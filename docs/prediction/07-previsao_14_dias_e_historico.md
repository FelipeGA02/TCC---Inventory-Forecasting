# 07 — Previsão de 14 dias e histórico da previsão: como o sistema treina, guarda e mostra

A decisão está no [ADR-017](ADR-017-previsao-por-categoria-e-grama.md). Este documento
descreve o funcionamento: o caminho de uma planilha até a previsão na tela, o que cada
tabela guarda e as regras do histórico congelado.

---

## 1. O ciclo da loja

```
planilha da semana ──► conferência (sem gravar) ──► gravação ──► "Treinar previsões" ──► telas
                         dias faltando? aviso          sales        forecast_jobs done     último treino
```

1. **A gestora envia a planilha** "Contas a Receber" (da semana ou do mês). A tela confere
   antes de gravar (§5) e mostra:
   - o período de cada loja;
   - as vendas novas e as que já estavam carregadas;
   - os dias de loja aberta que ficariam sem venda.

   Ela confirma, e as vendas novas vão para `sales`.
2. **A gestora treina as previsões** (botão no alto da tela, só admin). O treino roda em
   segundo plano, e o sino de notificações mostra o andamento. Sem dados novos desde o
   último treino concluído, o disparo fica `skipped` e nada é treinado.
3. **As telas passam a mostrar o treino novo** quando ele termina `done`: previsão de 14
   dias, histórico, relatórios e notificações.

Não há treino agendado. Na API publicada no Render, que não treina
(`TRAINING_RUNNER=externo`), o passo 2 é o script
`python -m backend.scripts.treinar_previsoes`, rodado pela equipe de outra máquina sobre o
mesmo banco. É o mesmo código.

## 2. O treino

`backend/services/servico_previsao.py` monta as séries e chama
`backend/domain/models/trainer.py` para cada uma.

**Séries.** Em cada loja, as 4 categorias e cada produto de grama que vendeu nela. A série é
o fluxo diário: soma da quantidade por dia, sem as notas acima de 2.000 unidades (ADR-013) e
sem `Servico e taxa`. Dia sem venda é zero, e todas as séries terminam no último dia com
venda da base (`data_until`).

**Quem treina.** Fica `insufficient_data`, sem previsão e com o motivo no log:
- a série com menos de 180 dias antes da 1ª origem do walk-forward;
- o produto que vendeu em menos de 28 dias da última janela de 365.

**Para cada série treinável:**

1. **Ordem por AIC.** O grid é p, q ∈ 0..2 e P, Q ∈ 0..1, com m = 7, d = 0, D = 0,
   constante e as 8 exógenas de calendário. Ajusta só na janela de 365 dias que termina na
   véspera da 1ª origem, então a escolha não vê o período avaliado.
2. **Walk-forward.** São 56 origens andando 1 dia. Em cada uma, o modelo é reajustado nos 365
   dias antes dela e prevê os 14 dias seguintes. As janelas se sobrepõem: cada dia avaliado
   aparece em até 14 origens, uma por horizonte. As métricas são dos dias de loja aberta:
   - MASE;
   - erro relativo à naïve sazonal;
   - origens que vencem a naïve;
   - cobertura e largura da faixa de 95%;
   - previsto ÷ vendido;
   - erro no total de cada janela.
3. **Complemento.** A última origem completa fica 13 dias antes da última venda. As 13
   origens seguintes preveem só o próprio dia (h = 1), fora das métricas, para o histórico
   (§4).
4. **Ajuste final.** Ajusta nos últimos 365 dias e prevê os 14 dias seguintes à última
   venda. Desse ajuste saem:
   - os coeficientes (`series_models.params.coeficientes`);
   - o diagnóstico dos resíduos: Ljung-Box até 14 dias e Shapiro-Wilk, em
     `series_models.metrics`. O log cita o problema quando p ≤ 0,05; o diagnóstico não muda
     o status.
5. **Status.** `trained` se MASE < 1 e cobertura da faixa em [90%, 98%]. Senão
   `low_confidence`: a previsão sai com aviso. Ajuste que falha vira `error`, e o treino
   segue com as outras séries.

**Paralelismo.** Com `TRAINING_WORKERS > 1` cada série vai para um processo. Se o pool
quebrar (acontece no proot/Termux), as séries que faltam seguem uma a uma.

**Ao concluir**, numa transação só, que marca o treino `done`:
- grava o histórico da previsão (§4);
- liga a este treino as planilhas que entraram nele pela primeira vez
  (`processing_log.forecast_job_id`);
- apaga o walk-forward (`series_backtest_points`) dos treinos mais antigos que os últimos
  `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` (padrão 4).

Treino que falha ou cai no meio não muda nada do que as telas mostram.

## 3. A previsão de 14 dias

Cada série com modelo grava os 14 dias seguintes à última venda, com faixa de 95%
(`series_forecasts`).

O painel (`GET /api/v1/painel`) lê o último treino concluído:
- a previsão de cada categoria por dia, com o modelo dela (`categorias_modelo`) e o teste de
  acerto dia a dia (`backtest_categorias`, o 1º dia de cada janela);
- o total da loja, que é a soma das 4 categorias, inclusive os limites da faixa (uma faixa
  conservadora);
- os produtos de grama, cada um com o seu modelo, ou só o status e o motivo se ficou sem
  previsão.

Loja fechada e evento do dia vêm do calendário.

A previsão não é recalculada todo dia: com o mesmo modelo e os mesmos dados ela daria os
mesmos números. Ela muda quando a loja treina de novo com vendas novas.

## 4. O histórico da previsão

**Regra:** o previsto de um dia é o da última previsão feita antes dele — o número que a loja
viu na tela —, e não muda depois que o dia passa. A regra pura está em
`backend/domain/historico_previsao.py`; a gravação, em `servico_previsao.gravar_historico`.

Cada treino concluído tem um `início` = dia seguinte à última venda. Em cada loja do treino:

1. **apaga os dias ≥ início**, de todas as séries. Inclui a série que desta vez ficou sem
   modelo: o número dela sai da tela, então não pode congelar depois;
2. **grava os 14 dias da previsão nova** (`source = forecast`, `origin_date` = início);
3. **preenche com o walk-forward só os dias < início ainda vazios** (`source = walk_forward`).
   Entra só o 1º dia de cada janela (h = 1), das origens completas e do complemento. Como as
   origens andam 1 dia, cada dia tem um previsto só, feito com as vendas até a véspera.

Dia < início nunca é apagado: é isso que congela. Os casos saem dessa regra, sendo G os dias
entre o início de um treino e o do seguinte:

| Intervalo | Fica congelado da previsão anterior | O walk-forward preenche |
| --- | --- | --- |
| G ≤ 14 (ex.: 9) | os G primeiros dias (horizontes 1 a G) | nada |
| G > 14 (ex.: 20) | os 14 dias | os G − 14 dias que sobram |
| 1º treino | — | os 69 dias antes do início |

**Exemplo:**
- **Treino 1**, vendas até 03/10: grava a previsão de 04/10 a 17/10; o walk-forward preenche
  de 27/07 a 03/10.
- **Treino 2**, 9 dias depois, vendas até 12/10: apaga de 13 a 17/10 e grava de 13/10 a
  26/10. Ficam congelados de 04 a 12/10 do treino 1 (9 dias).
- **Treino 3**, 20 dias depois, vendas até 01/11: nenhum dia do treino 2 é ≥ 02/11, então os
  14 (13 a 26/10) ficam. De 27/10 a 01/11 está vazio, e o walk-forward do treino 3 preenche.
  Grava de 02/11 a 15/11.

**O complemento** existe por causa do treino 3. O buraco sempre termina na véspera do início
novo, e sem as 13 origens parciais o h = 1 não chegaria a esses dias. Um buraco maior que 69
dias (a loja dez semanas sem treinar) fica vazio no começo.

**O que cada ponto guarda** (`forecast_history`):
- previsto e faixa;
- `source`;
- `origin_date` (o horizonte é `day − origin_date + 1`);
- `job_id`;
- `store_closed`: se o calendário dava a loja fechada quando o dia foi previsto. Se o
  calendário for corrigido depois, a tela ainda explica um previsto zero.

**A tela** (`GET /api/v1/painel/historico/{loja}/{categoria|produto}/{item}`) mostra o
vendido de cada dia (sem encomendas grandes, de `sales`) contra o previsto congelado, em
duas linhas:
- **o que a tela mostrava** (`forecast`);
- **o teste do treino** (`walk_forward`). Essa é otimista perto da outra: prevê só 1 dia à
  frente, enquanto a previsão congelada tem horizontes de até 7 a 14 dias.

O tooltip mostra o horizonte e se a previsão contava com a loja fechada.

**Pontos de atenção:**
- **A fronteira é o dia seguinte à última venda, não o dia do clique.** Se a loja treina no
  dia 20 com vendas só até o dia 10, a previsão nova cobre de 11 a 24 e substitui a antiga
  nesses dias. Continua honesta, porque só usou dados até o dia 10.
- **Uma venda apagada que faz a última venda voltar** puxa o início para trás e "descongela"
  dias. É coerente, porque esses dias voltaram a não ter venda.
- **Banco com treino anterior à gravação do histórico:**
  `python -m backend.scripts.semear_historico [--recriar]` preenche o histórico a partir do
  último treino. `--recriar` apaga antes o que o treino antigo do painel gravou.

## 5. Conferência da planilha antes de gravar

`POST /api/v1/upload/verificacao` passa a planilha pelas mesmas etapas da carga (Etapas 1–3,
loja, categoria, encomenda, duplicatas) sem gravar nada. Para cada loja, confere do dia
seguinte à última venda já carregada (quando ele vem antes do 1º dia da planilha) até o
último dia da planilha. A regra está em `backend/domain/etl/cobertura.py`.

**Falta** o dia em que a loja estava aberta e não tem venda nem na planilha nem na base.
"Aberta" segue o calendário da loja; fora dele, a loja só fecha no domingo. Domingo e
feriado no meio não contam como falta.

O aviso cobre três casos:
- **antes da planilha:** o buraco entre a base e a planilha;
- **dentro da planilha:** dia aberto sem venda no período que ela cobre;
- **loja ausente:** a planilha não traz uma das lojas.

A tela mostra o aviso e a consequência: esses dias contam como venda zero na previsão até a
planilha deles chegar. A gestora escolhe **Gravar mesmo assim** ou **Cancelar**.

A confirmação envia o arquivo de novo para `POST /api/v1/upload`, que confere outra vez (a
base pode ter mudado no meio) e grava em `processing_log.quality`:
- o período da planilha;
- os dias faltando;
- os avisos.

Reproduzindo a carga das 26 planilhas mensais reais (jan/2024 a fev/2026), em ordem e com o
calendário real, o aviso não dispara nenhuma vez.

## 6. Onde está cada coisa

| Tabela | Guarda | Fica |
| --- | --- | --- |
| `forecast_jobs` | cada disparo: status, andamento, impressão digital, `data_until`, configuração (com `versao_codigo`) | sempre |
| `forecast_job_logs` | uma linha por série e as do treino (planilhas novas, histórico, limpeza) | sempre |
| `series_models` | cada série: status, ordem, AIC, métricas, diagnóstico, coeficientes, motivo | sempre |
| `series_forecasts` | os 14 dias de cada série | sempre (é a origem dos valores que o histórico trocou) |
| `series_backtest_points` | todas as origens e horizontes do walk-forward | só nos últimos 4 treinos concluídos |
| `forecast_history` | o previsto congelado de cada dia | sempre |
| `processing_log` | cada planilha: contagens, período, dias faltando, `forecast_job_id` | sempre |

| Comando (a partir de `ia-predictor/`) | Para quê |
| --- | --- |
| `python -m backend.scripts.treinar_previsoes [--workers N]` | treinar fora da API (Render) |
| `python -m backend.scripts.semear_historico [--recriar]` | preencher o histórico de um banco antigo |

| Teste | O que garante |
| --- | --- |
| `tests/unit/test_historico_previsao.py` | a regra do histórico: congelamento, 9 e 20 dias, 1º dia das janelas, loja fechada |
| `tests/unit/test_treino_serie.py` | walk-forward, complemento até a última venda, métricas, diagnóstico e coeficientes |
| `tests/unit/test_cobertura_planilha.py` | os dias faltando: entre a base e a planilha, domingo e feriado, loja ausente, dentro da planilha |
| `tests/integration/test_servico_previsao.py` | treino de ponta a ponta, histórico gravado, planilhas ligadas, limpeza do walk-forward, script |
| `tests/integration/test_upload.py` | conferência sem gravar, aviso de dias faltando, gravação com o aviso no `processing_log` |
