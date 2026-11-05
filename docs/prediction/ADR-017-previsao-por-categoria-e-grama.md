# ADR-017 — A previsão do sistema: SARIMAX direto em cada categoria e em cada produto de grama, por loja

**Status:** aceito · **Data:** 2026-10-26 · **Autores:** Daniel Nunes da Silva, Felipe Gurgel Araújo
**Aceita:** ADR-016 (categoria por modelo próprio) · **Revisa:** ADR-009 e ADR-011 (hierarquia
L1 por unidade + desagregação), ADR-006 (treino agendado), ADR-015 (script do treino fora da API)
**Pendente:** emenda dos Princípios II e V da constituição (`/speckit-constitution`)

---

## 1. Contexto

Até aqui a previsão das telas vinha de um treino em três níveis:

- **L1:** um SARIMAX por loja, na venda total;
- **L2:** a previsão da loja repartida entre as categorias pela participação de cada uma nas
  últimas 8 semanas;
- **produtos "regulares"** (ADI < 1,32): um SARIMAX por produto.

Esse treino rodava por agendador (segunda 02:00 e 10 minutos depois de cada planilha) e
levava ~40 minutos.

Dois achados mudaram o desenho:

1. **A desagregação perde para o modelo próprio da categoria** (ADR-016): o SARIMAX direto
   vence o erro em 7 dos 8 pares categoria-loja. A faixa de 95% da desagregação chega a
   cobrir só 60,3% dos dias (Flores de corte em Jardim Canadá), contra 96,2% no direto.
2. **O que a loja usa é a categoria e a grama.** As telas de previsão e de histórico já
   mostravam só as 4 categorias e os produtos de grama, por loja. A grama é a maior parte do
   volume, e a loja compra grama produto a produto.

Em paralelo, a branch `feat/servico-previsao` implementou e validou o treino direto: o
"serviço de previsão", disparado por um botão do admin.

## 2. Decisão

**O que é previsto.** Em cada loja, cada uma das 4 categorias (Grama, Plantas diversas,
Produtos de jardim, Flores de corte) e cada produto de grama, cada série com o seu SARIMAX.
O total da loja é a soma das 4 categorias, inclusive os limites da faixa: dá uma faixa
conservadora, mais larga que a exata. Não há mais modelo da loja, desagregação nem produto
"regular" de outras categorias.

**A receita** (`backend/domain/models/trainer.py`):

| Item | Valor |
| --- | --- |
| Série | fluxo diário: venda sem as notas acima de 2.000 un. (ADR-013; desde o ADR-018, acima de média + 4 desvios-padrão da quantidade dos pedidos da loja), sem `Servico e taxa` |
| Modelo | SARIMAX com m = 7, d = 0, D = 0 e constante; ordem (p, q)(P, Q) por AIC no grid p, q ∈ 0..2 e P, Q ∈ 0..1, só com a janela antes da 1ª origem |
| Exógenas | 6 dummies de dia da semana, `loja_fechada` e `abertura_excepcional` (calendário de cada loja) |
| Janela | deslizante, 365 dias (`FORECAST_SERVICE_WINDOW_DAYS`) |
| Validação | walk-forward com 56 origens andando 1 dia (8 semanas), cada uma prevendo 14 dias; métricas nos dias de loja aberta |
| Status | `trained` se MASE < 1 e cobertura da faixa de 95% em [90%, 98%]; senão `low_confidence` (a previsão sai e a tela a mostra igual; desde 2026-11-05, sem selo nem aviso de confiança) |
| Sem dados | `insufficient_data`, sem previsão: menos de 180 dias antes da 1ª origem; no produto, venda em menos de 28 dias da última janela (o critério e a origem do 28 estão no doc 07 §2) |
| Previsão | os 14 dias seguintes à última venda, com faixa de 95% |
| Diagnóstico | Ljung-Box (14 dias) e Shapiro-Wilk dos resíduos do ajuste final, gravados e citados no log quando p ≤ 0,05; não mudam o status |

Por que `d = 0`: as 12 séries de categoria e de produto de grama rejeitam raiz unitária no
ADF, e `d = 1` mostra sinal de sobrediferenciação (autocorrelação de lag 1 da diferença
entre −0,42 e −0,53). O custo medido fica registrado: na família Grama, `d = 1` ainda erra
1–7% menos.

**Quando treina.** Só quando o admin pede: botão "Treinar previsões" ou script
`python -m backend.scripts.treinar_previsoes`. Este é para a API que não treina, no Render
(`TRAINING_RUNNER=externo`). Não há agendador. A loja envia as planilhas da semana e treina
uma vez. Se as vendas, o calendário e o catálogo não mudaram desde o último treino
concluído (impressão digital SHA-256), o disparo fica `skipped`.

**O que as telas mostram.** Previsão de 14 dias, histórico, relatórios e notificações leem o
**último treino concluído** (`forecast_jobs` `done`).

**Histórico da previsão.** O previsto de cada dia fica congelado depois que o dia passa
(`forecast_history`). Cada treino concluído faz três coisas, na mesma transação que marca o
treino como `done`:

1. troca os dias a partir do início da previsão nova (o dia seguinte à última venda);
2. grava os 14 dias novos;
3. preenche com o 1º dia de cada janela do walk-forward (h = 1) só os dias que nenhuma
   previsão cobriu.

Com treino a cada 9 dias, ficam congelados os 9 primeiros dias de cada previsão. Com mais de
14 dias entre treinos, ficam os 14, e o walk-forward do treino seguinte preenche o resto.
Detalhes em `07-previsao_14_dias_e_historico.md`.

**Envio de planilha.** A carga confere a planilha antes de gravar
(`POST /api/v1/upload/verificacao`): período de cada loja, vendas novas e já carregadas, e
os dias de loja aberta que ficariam sem venda na base. A gestora vê o aviso e confirma. A
carga não agenda treino: responde `needs_training` quando há venda nova.

## 3. Alternativas

| Opção | Por que não |
| --- | --- |
| Manter L1 + desagregação e só trocar a categoria pelo direto (ADR-016, §3) | dois treinos para manter, e a loja não usa o total previsto por um modelo próprio: a soma das categorias responde à mesma pergunta |
| Produto de grama por desagregação da categoria | a grama é comprada produto a produto e os produtos principais vendem quase todo dia: série densa o bastante para um SARIMAX próprio, com a mesma validação da categoria |
| Treino agendado após o upload | com planilhas semanais, o treino logo depois de cada arquivo treina com a semana pela metade; a gestora sabe quando terminou de enviar |

## 4. Consequências

- **Saiu do sistema:** o treino anterior (`treino_service`, `/api/v1/models/*`, o agendador
  APScheduler e o script `gravar_previsao`). Saíram também as tabelas dele do ORM
  (`retrain_history`, `model_artifacts`, `backtest_points`, `forecast_runs`,
  `forecasts_cache`) e as rotas nunca implementadas (products, forecast, alerts, simulation,
  reports). Num banco antigo, essas tabelas continuam lá, sem uso.
- **Treino mais longo por série, menos séries.** Cada série tem 36 ajustes na grade, 56 no
  walk-forward, 13 no complemento e 1 no ajuste final. A ~2,3 s por ajuste (medida do
  ADR-016), cada série leva uns 4 minutos. Com dados até 28/02/2026, a base tinha 9
  produtos de grama, e o treino montava 25 séries: 8 de categoria (4 por loja) e 17 de
  produto de grama (9 em Jardim Canadá e 8 em Itabirito). Dessas, 17 tinham previsão: as 8 de
  categoria e 9 de grama (5 em Jardim Canadá e 4 em Itabirito). As outras 8 de grama ficavam
  `insufficient_data` (venda em menos de 28 dias). Com a classificação SKU a SKU de
  04/11/2026, que pôs a grama preta, o capim dos Texas e a semente de braquiária em Grama,
  são 19 produtos e 43 séries (8 de categoria e 35 de produto), 23 com previsão (8 de
  categoria e 15 de grama: 11 em Jardim Canadá e 4 em Itabirito). No treino de 05/11/2026,
  9 ficaram `trained` e 14 `low_confidence` (antes, 9 e 8); as 6 séries novas, de capim dos
  Texas e grama preta, ficaram todas `low_confidence`. A lista e o resultado estão no doc 07 §2. Com `TRAINING_WORKERS`
  processos, o treino cai na mesma proporção.
- **Rastreabilidade:**
  - `forecast_jobs` guarda o disparo, a configuração e a versão do código;
  - `forecast_job_logs`, uma linha por série;
  - `series_models`, a ordem, as métricas, o diagnóstico e os coeficientes;
  - `processing_log.forecast_job_id`, as planilhas que entraram em cada treino.

  O walk-forward completo (`series_backtest_points`) fica só nos últimos
  `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` treinos (padrão 4), porque cresce ~13 mil linhas
  por treino.
- **Constituição desatualizada.** O Princípio II ainda manda obter a categoria por
  desagregação. O Princípio V cita `retrain_history` e `forecast_runs` como registro
  obrigatório. As duas emendas ficam para `/speckit-constitution`.
- **Experimentos preservados:** `training_scripts/frontend_mock/gerar_dados_frontend.py`
  guarda a receita anterior, para o artigo e para comparação.

## 5. Referências

- `ia-predictor/backend/services/servico_previsao.py` — o treino, a gravação e o histórico
- `ia-predictor/backend/domain/models/trainer.py` — a receita e o walk-forward
- `ia-predictor/backend/domain/historico_previsao.py` — a regra do histórico congelado
- `ia-predictor/backend/domain/etl/cobertura.py` — os dias faltando na conferência da planilha
- `docs/prediction/ADR-016-categoria-direta-vs-desagregacao.md` — a evidência da categoria direta
- `docs/prediction/07-previsao_14_dias_e_historico.md` — como o sistema treina, guarda e mostra
