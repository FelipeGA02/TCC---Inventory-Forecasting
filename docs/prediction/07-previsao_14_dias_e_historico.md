# 07 — Previsão (2 semanas a 3 meses) e histórico da previsão: como o sistema treina, guarda e mostra

A decisão está no [ADR-017](ADR-017-previsao-por-categoria-e-grama.md), com o d escolhido série a série do
[ADR-020](ADR-020-diferenciacao-por-serie.md) e a previsão de 91 dias com horizonte escolhido na
tela do [ADR-021](ADR-021-horizonte-de-previsao-selecionavel.md) (o nome do arquivo ficou do tempo
em que a previsão era de 14 dias). Este documento descreve o funcionamento: o caminho de uma planilha até a previsão na tela, o que cada
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
   último treino concluído, o disparo fica `skipped` e nada é treinado. A receita do modelo (d
   de cada família, horizontes, janela...) entra na impressão digital: depois de mudá-la, o
   próximo disparo treina mesmo sem venda nova.
3. **As telas passam a mostrar o treino novo** quando ele termina `done`: previsão (2 semanas
   por padrão; a loja escolhe até 3 meses), histórico, relatórios e notificações.

Não há treino agendado. Na API publicada no Render, que não treina
(`TRAINING_RUNNER=externo`), o passo 2 é o script
`python -m backend.scripts.treinar_previsoes`, rodado pela equipe de outra máquina sobre o
mesmo banco. É o mesmo código.

**Quando as regras de categoria mudam.** A planilha só classifica produto novo: o produto já
cadastrado mantém a categoria do cadastro. Depois de mudar
`training_scripts/preprocessing/taxonomy/categorias.py`, roda-se
`python -m backend.scripts.reclassificar_produtos` (sem `--aplicar`, só mostra o que muda;
com ele, atualiza `products` e registra em `processing_log`). O catálogo entra na impressão
digital, então o treino seguinte treina de novo. Produto que entra em `Servico e taxa` ou sai
dela muda o tamanho do pedido: em seguida, `reclassificar_encomendas` confere as encomendas
grandes. A revisão SKU a SKU de 04/11/2026 mudou 127 produtos de categoria; entre eles, grama
preta / pelo de urso e capim dos Texas passaram de Plantas diversas a Grama.

## 2. O treino

`backend/services/servico_previsao.py` monta as séries e chama
`backend/domain/models/trainer.py` para cada uma.

**Séries.** Em cada loja, as 4 categorias e cada produto de grama que vendeu nela. A série é
o fluxo diário: soma da quantidade por dia, sem as encomendas grandes (pedido acima de média +
4 desvios-padrão da quantidade dos pedidos da loja, ADR-018; antes, 2.000 unidades, ADR-013) e
sem `Servico e taxa`. Dia sem venda é zero, e todas as séries terminam no último dia com
venda da base (`data_until`).

**Quem treina.** Fica `insufficient_data`, sem previsão e com o motivo no log:
- a série com menos de 180 dias antes da 1ª origem do walk-forward;
- o produto que vendeu em menos de 28 dos últimos 365 dias.

**A partir de quando uma série tem previsão.** Os 180 dias contam antes da 1ª origem do
walk-forward, e não até a última venda. A 1ª origem fica 68 dias antes da última venda: são
56 origens andando 1 dia, e a última delas fica 13 dias antes da última venda, para ter 14
dias à frente. Então a série precisa de **249 dias de calendário** (180 + 69), contados da
primeira venda até a última, o que dá pouco mais de 8 meses. Os dias contados são de
calendário, inclusive os zeros (domingo, feriado, dia sem venda). A série de categoria
começa na primeira venda da loja, e a de produto, na primeira venda do produto naquela loja.
O produto de grama precisa ainda de venda em pelo menos 28 desses dias, dentro dos últimos
365 dias. Com os parâmetros padrão (`MIN_OBSERVATIONS_DAYS=180`,
`FORECAST_SERVICE_WF_ORIGINS=56`, `FORECAST_HORIZON_DAYS=14`), um produto que estreia hoje
ganha previsão no primeiro treino depois de 249 dias e 28 dias com venda. Com dados até
28/02/2026, isso vale para quem vendeu pela primeira vez até 25/06/2025.

**Como se decide se um produto de grama é regular e se vai ser previsto.** O sistema não
classifica o produto como "regular" ou "irregular". Ele confere duas contagens, nesta ordem,
em cada loja e a cada treino (`motivo_inelegivel` em `backend/domain/models/trainer.py`):

1. **Histórico:** 180 dias antes da 1ª origem do walk-forward, ou seja, 249 dias de
   calendário desde a primeira venda do produto na loja (`MIN_OBSERVATIONS_DAYS`).
2. **Frequência de venda:** venda em pelo menos 28 dos últimos 365 dias
   (`FORECAST_SERVICE_MIN_SALE_DAYS` e `FORECAST_SERVICE_MIN_SALE_WINDOW_DAYS`). Esse período é
   separado da janela de treino (545 dias, ADR-022): a janela maior não traz de volta produto
   que parou de vender. Conta dias com venda, não quantidade, e as encomendas
   grandes ficam de fora. Esta é a regra que separa o produto regular do irregular.

O produto que falha em qualquer uma vira `insufficient_data`: fica sem previsão, e o motivo
vai para o log e para o painel. O que passa nas duas é treinado e tem previsão (`trained`).
O walk-forward mede quanto a previsão acerta (erro médio por dia, erro em % da venda, MASE,
largura e cobertura da faixa de 95%); as métricas ficam no log e aparecem na tela de
histórico, sem classificar a série. Ou seja, as duas contagens dizem se o produto *pode* ser
previsto, e o walk-forward mede *quanto* a previsão acerta.

*De onde vem o 28.* O número foi herdado do corte do rateio por produto na desagregação
anterior: produto com menos de 28 dias de venda recebia rateio uniforme da categoria
(EDA, `00-eda_report.md` §2.5; gráfico em `03_esparsidade_dias_ativos_sku.png`). Com uns
300 dias de loja aberta por ano, 28 dias equivalem a vender cerca de uma vez a cada duas
semanas. Não foi testado se 28 é o melhor corte para o SARIMAX. Na base até 28/02/2026, a
separação é clara mesmo assim: os produtos que ficam de fora pela venda venderam em no máximo
23 dias no ano (capim dos Texas roxo, Itabirito), e o mais fraco que entra vendeu em 31
(Esmeralda, Itabirito). Qualquer corte entre 24 e 31 dias daria as mesmas listas.

*O que não é usado.* A EDA classifica a demanda pelo critério de Syntetos-Boylan
(`training_scripts/eda/eda_classificacao_sku.py`). Esse critério usa o intervalo médio entre
vendas (ADI) e a variação do tamanho delas (CV²) para separar demanda suave, errática,
intermitente e irregular. O sistema não usa essa classificação para decidir o treino. Ela
serve de comparação para a trilha Croston/TSB/SBA por SKU.

**Quantas séries.** As séries são as 4 categorias e todos os produtos de grama, separados
pelas 2 lojas. Desde a revisão SKU a SKU de 04/11/2026 (§1), Grama inclui também a grama preta
/ pelo de urso, o capim dos Texas, a semente de braquiária e o `GRAMADOS PREMIUM 20 KG
BIOPLANT`. A base tem 19 produtos de grama: 16 venderam nas 2 lojas, a Bermudas só em Jardim
Canadá e as 2 sementes de braquiária só em Itabirito. São 43 séries: 8 de categoria e 35 de
produto (17 em Jardim Canadá e 18 em Itabirito). Antes da revisão eram 9 produtos e 25
séries, 17 com previsão. As duas listas abaixo usam dados até 28/02/2026. "Dias de série" são
os dias de calendário da primeira venda até 28/02/2026, e o mínimo é 249. Os dias com venda
contam só o fluxo diário (sem encomendas grandes), e o mínimo é 28 nos últimos 365.

*Séries com previsão (23).*

| # | Loja | Série | 1ª venda | Dias de série | Dias com venda (365) |
| --- | --- | --- | --- | --- | --- |
| 1 | Jardim Canadá | Categoria Grama | 02/01/2024 | 789 | 299 |
| 2 | Jardim Canadá | Categoria Plantas diversas | 02/01/2024 | 789 | 299 |
| 3 | Jardim Canadá | Categoria Produtos de jardim | 02/01/2024 | 789 | 299 |
| 4 | Jardim Canadá | Categoria Flores de corte | 02/01/2024 | 789 | 299 |
| 5 | Jardim Canadá | 3 GRAMA ESMERALDA | 02/01/2024 | 789 | 297 |
| 6 | Jardim Canadá | 147 GRAMA AMENDOIM UNID. BDJA | 02/01/2024 | 789 | 262 |
| 7 | Jardim Canadá | 710 GRAMA SAO CARLOS | 02/01/2024 | 789 | 255 |
| 8 | Jardim Canadá | 1293 CAPIM DOS TEXAS ROXO | 03/01/2024 | 788 | 59 |
| 9 | Jardim Canadá | 00020227 CAPIM DOS TEXAS ROXO | 18/01/2024 | 773 | 51 |
| 10 | Jardim Canadá | 1294 CAPIM DOS TEXAS VERDE | 10/01/2024 | 781 | 39 |
| 11 | Jardim Canadá | 166 GRAMA PRETA PELO DE URSO BDJA (UNID) | 02/01/2024 | 789 | 39 |
| 12 | Jardim Canadá | 00150005 GRAMA PRETA PELO URSO SAQ | 29/01/2024 | 762 | 37 |
| 13 | Jardim Canadá | 1739 GRAMA ZEON | 01/02/2024 | 759 | 35 |
| 14 | Jardim Canadá | 167 GRAMA PRETA ANA | 16/01/2024 | 775 | 34 |
| 15 | Jardim Canadá | 00013475 GRAMA ESMERALDA ( ITO) | 07/02/2024 | 753 | 33 |
| 16 | Itabirito | Categoria Grama | 02/01/2024 | 789 | 295 |
| 17 | Itabirito | Categoria Plantas diversas | 02/01/2024 | 789 | 301 |
| 18 | Itabirito | Categoria Produtos de jardim | 02/01/2024 | 789 | 301 |
| 19 | Itabirito | Categoria Flores de corte | 02/01/2024 | 789 | 301 |
| 20 | Itabirito | 00013475 GRAMA ESMERALDA ( ITO) | 02/01/2024 | 789 | 291 |
| 21 | Itabirito | 147 GRAMA AMENDOIM UNID. BDJA | 03/01/2024 | 788 | 79 |
| 22 | Itabirito | 710 GRAMA SAO CARLOS | 03/01/2024 | 788 | 64 |
| 23 | Itabirito | 3 GRAMA ESMERALDA | 03/01/2024 | 788 | 31 |

Esmeralda em Itabirito (31), Esmeralda ITO em Jardim Canadá (33), grama preta Ana (34) e Zeon
(35) em Jardim Canadá estão perto do mínimo de 28.

*Resultado do treino (treino 10, 05/11/2026).* 23 séries com previsão; antes da revisão
(treino 6, 02/11/2026) eram 17. Nas categorias, a mudança de composição mexe pouco no MASE
(Jardim Canadá: Grama 0,924 → 0,945, Plantas diversas 0,937 → 0,971, Produtos de jardim 0,906
→ 0,876; Itabirito: até 0,02). As 6 séries novas:

| Loja | Série | MASE | Faixa de 95% acertou |
| --- | --- | --- | --- |
| Jardim Canadá | 1293 CAPIM DOS TEXAS ROXO | 2,285 | 91,1% |
| Jardim Canadá | 00020227 CAPIM DOS TEXAS ROXO | 0,764 | 100,0% |
| Jardim Canadá | 1294 CAPIM DOS TEXAS VERDE | 0,739 | 99,1% |
| Jardim Canadá | 166 GRAMA PRETA PELO DE URSO BDJA (UNID) | 0,676 | 100,0% |
| Jardim Canadá | 00150005 GRAMA PRETA PELO URSO SAQ | 1,080 | 97,8% |
| Jardim Canadá | 167 GRAMA PRETA ANA | 1,007 | 97,8% |

São produtos de venda esporádica (34 a 59 dias com venda no ano): a faixa cobre os muitos dias
de venda zero e fica larga, ou o modelo não bate a repetição da semana anterior (MASE ≥ 1).

*Com o d escolhido série a série (ADR-020, treino de 09/11/2026, mesma base).* Ver ADR-020 §6.

*Séries sem previsão (20).* Em 17 o motivo é a venda em menos de 28 dias: produtos de venda
esporádica, com poucos dias no ano e às vezes uma única compra grande. Com tantos zeros, a
série não sustenta um SARIMAX. Nas outras 3, o produto estreou há pouco e não tem os 249 dias
de série: o `GRAMADOS PREMIUM` nas 2 lojas, desde o fim de outubro de 2025, e a semente de
braquiária de 10 kg em Itabirito. O `GRAMADOS PREMIUM` em Jardim Canadá já vende em 36 dias e
deve ganhar previsão quando completar o histórico, por volta de julho de 2026. Todas ficam no
log e no painel como `insufficient_data`, com o motivo, sem previsão.

| # | Loja | Produto | 1ª venda | Última venda | Dias com venda (365) | Dias com venda (histórico) | Quantidade total (fluxo) | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Jardim Canadá | 00030458 GRAMADOS PREMIUM 20 KG BIOPLANT | 28/10/2025 | 26/02/2026 | 36 | 36 | 257 (257) | histórico (124 dias) |
| 2 | Jardim Canadá | 00150149 CAPIM DOS TEXAS VERDE | 26/01/2024 | 10/02/2026 | 8 | 25 | 742 (542) | venda |
| 3 | Jardim Canadá | 134 GRAMA AZUL SAQ | 08/03/2024 | 15/01/2026 | 3 | 6 | 1.436 (36) | venda |
| 4 | Jardim Canadá | 00013479 GRAMA AMENDOIM | 10/01/2024 | 08/10/2025 | 2 | 5 | 1.255 (1.255) | venda |
| 5 | Jardim Canadá | 1832 GRAMA BERMUDAS | 20/03/2024 | 30/09/2025 | 2 | 6 | 428 (428) | venda |
| 6 | Jardim Canadá | 2372 GRAMA ESMERALDA MAXI ROLO | 06/03/2024 | 31/05/2024 | 0 | 6 | 64 (64) | venda |
| 7 | Itabirito | 1293 CAPIM DOS TEXAS ROXO | 16/02/2024 | 06/02/2026 | 23 | 55 | 11.332 (3.947) | venda |
| 8 | Itabirito | 00020227 CAPIM DOS TEXAS ROXO | 01/04/2024 | 17/11/2025 | 10 | 13 | 318 (318) | venda |
| 9 | Itabirito | 00150149 CAPIM DOS TEXAS VERDE | 08/02/2025 | 07/01/2026 | 10 | 11 | 188 (188) | venda |
| 10 | Itabirito | 00030458 GRAMADOS PREMIUM 20 KG BIOPLANT | 02/11/2025 | 10/02/2026 | 8 | 8 | 25 (25) | histórico (119 dias) |
| 11 | Itabirito | 1294 CAPIM DOS TEXAS VERDE | 15/04/2024 | 15/01/2026 | 8 | 21 | 733 (633) | venda |
| 12 | Itabirito | 167 GRAMA PRETA ANA | 22/01/2024 | 18/02/2026 | 8 | 22 | 9.826 (442) | venda |
| 13 | Itabirito | 1739 GRAMA ZEON | 20/02/2024 | 27/02/2026 | 7 | 13 | 905 (455) | venda |
| 14 | Itabirito | 166 GRAMA PRETA PELO DE URSO BDJA (UNID) | 29/02/2024 | 03/12/2025 | 5 | 14 | 2.675 (1.375) | venda |
| 15 | Itabirito | 2372 GRAMA ESMERALDA MAXI ROLO | 23/10/2024 | 13/11/2025 | 4 | 12 | 1.080 (160) | venda |
| 16 | Itabirito | 00013479 GRAMA AMENDOIM | 26/03/2024 | 18/11/2025 | 1 | 12 | 2.221 (908) | venda |
| 17 | Itabirito | 00021675 SEMENTE BRACHIARA 10KG | 24/11/2025 | 24/11/2025 | 1 | 1 | 1 (1) | histórico (97 dias) |
| 18 | Itabirito | 00150005 GRAMA PRETA PELO URSO SAQ | 08/02/2024 | 17/10/2025 | 1 | 19 | 337 (337) | venda |
| 19 | Itabirito | 00021306 SEMENTE BRACHIARIA 1KG | 23/02/2024 | 29/10/2024 | 0 | 2 | 150 (150) | venda |
| 20 | Itabirito | 134 GRAMA AZUL SAQ | 30/03/2024 | 30/01/2025 | 0 | 3 | 34 (34) | venda |

A última venda conta todas as notas, inclusive as encomendas grandes. Os dias com venda e o
fluxo (entre parênteses) não contam as encomendas. A Esmeralda Maxi Rolo de Jardim Canadá não
vende desde 31/05/2024, e a Azul em saco de Itabirito, desde 30/01/2025. A Bermudas não tem
série em Itabirito, porque nunca vendeu lá.

| | Jardim Canadá | Itabirito | Total |
| --- | --- | --- | --- |
| Categorias | 4 | 4 | 8 |
| Produtos de grama | 9 | 8 | 17 |
| **Séries montadas** | **13** | **12** | **25** |
| Com previsão (categorias + grama treinável) | 4 + 5 | 4 + 4 | **17** |
| `insufficient_data` (grama com < 28 dias de venda) | 4 | 4 | 8 |

Todas cumprem os 180 dias antes da 1ª origem (22/12/2025): o produto mais novo começou em
23/10/2024. Na Amendoim em bandeja de Itabirito, 91% do volume é encomenda grande (482 mil
un. no total, 42 mil no fluxo), e por isso ela tem só 79 dias com venda. A contagem é refeita
a cada treino: com planilhas novas, um produto pode passar dos 28 dias ou cair abaixo deles.

**Para cada série treinável:**

1. **Ordem por AIC.** O grid é p, q ∈ 0..2 e P, Q ∈ 0..1, com m = 7, D = 0 e as 8 exógenas de
   calendário. Ajusta só na janela de treino (545 dias, `FORECAST_SERVICE_WINDOW_DAYS`, ADR-022; até
   10/11/2026, 365) que termina na véspera da 1ª origem, então a
   escolha não vê o período avaliado. Isso é feito duas vezes, com d = 0 (com constante) e d = 1
   (sem), e os passos 1 e 2 rodam para cada um (ADR-020).
2. **Walk-forward.** São 56 origens andando 1 dia. Em cada uma, o modelo é reajustado nos 545
   dias antes dela e prevê os 14 dias seguintes. As janelas se sobrepõem: cada dia avaliado
   aparece em até 14 origens, uma por horizonte. As métricas são dos dias de loja aberta:
   - MASE;
   - erro relativo à naïve sazonal;
   - origens que vencem a naïve;
   - cobertura e largura da faixa de 95%;
   - previsto ÷ vendido;
   - erro no total de cada janela.
   Com os dois d avaliados, fica o d cujo walk-forward errou menos (erro médio por dia); o erro
   de cada um vai para `series_models.metrics.selecao_d` e para o log da série.
3. **Cobertura até a última venda.** A última origem fica 13 dias antes da última venda, então
   as janelas cobrem todos os dias até ela; o histórico guarda de cada dia a janela mais antiga
   (§4). Até 10/11/2026 havia um complemento (13 origens parciais com h = 1, fora das métricas)
   só para o histórico, que guardava o 1º dia de cada janela; saiu com o ADR-023.
4. **Ajuste final.** Ajusta nos últimos 545 dias e prevê os 91 dias seguintes à última venda
   (`FORECAST_MAX_HORIZON_DAYS`, ADR-021; o walk-forward continua com 14). Desse ajuste saem:
   - os coeficientes (`series_models.params.coeficientes`);
   - o diagnóstico dos resíduos: Ljung-Box até 14 dias e Shapiro-Wilk, em
     `series_models.metrics`. O log cita o problema quando p ≤ 0,05.
5. **Status.** `trained`: a série ajustou e tem previsão; as métricas do walk-forward ficam
   registradas, sem classificar a série. Ajuste que falha vira `error`, e o treino segue com
   as outras séries.

**Paralelismo.** Com `TRAINING_WORKERS > 1` cada série vai para um processo. Se o pool
quebrar (acontece no proot/Termux), as séries que faltam seguem uma a uma.

**Ao concluir**, numa transação só, que marca o treino `done`:
- grava o histórico da previsão (§4);
- liga a este treino as planilhas que entraram nele pela primeira vez
  (`processing_log.forecast_job_id`);
- apaga o walk-forward (`series_backtest_points`) dos treinos mais antigos que os últimos
  `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` (padrão 4).

Treino que falha ou cai no meio não muda nada do que as telas mostram.

## 3. A previsão (2 semanas a 3 meses)

Cada série com modelo grava os 91 dias seguintes à última venda, com faixa de 95%
(`series_forecasts`; até 08/11/2026 eram 14). A tela de Previsão e os relatórios mostram os
primeiros 14, 21, 28, 42, 56 ou 91 dias, à escolha da loja (caixa de opções "Horizonte",
padrão **2 semanas**). O teste de acerto (walk-forward, indicadores do histórico) é o das
2 primeiras semanas; o acerto além delas está no ADR-021 §3.1, sem aviso na tela. Acima do
gráfico, o quadro "Feriados e datas comemorativas no período" mostra cada data do horizonte num
cartão, com o dia da semana e se as lojas abrem (fechadas, abertas ou aberta só numa delas).

O calendário (`calendar_days`) precisa cobrir os 91 dias seguintes à última venda; dia que
faltar usa o padrão da loja (fechada só no domingo), e o treino registra o aviso.

Nos dias em que o calendário dá a loja fechada, previsto e faixa são zero
(`forecaster.prever`, desde 2026-11-09), na previsão e no walk-forward. A exógena
`loja_fechada` só desconta um valor fixo, e os termos MA levam a surpresa dos dias anteriores
para o domingo. No treino de 06/11/2026, Flores de corte de Jardim Canadá previa 7,2 em
01/03/2026 (domingo) depois de vender 227 na sexta e 124 no sábado, com faixa de 0 a 118. As
métricas não mudam: o walk-forward já é avaliado só nos dias de loja aberta.

O painel (`GET /api/v1/painel`) lê o último treino concluído:
- a previsão de cada categoria por dia, com o modelo dela (`categorias_modelo`) e o teste de
  acerto dia a dia (`backtest_categorias`, o 1º dia de cada janela);
- o total da loja, que é a soma das 4 categorias, inclusive os limites da faixa (uma faixa
  conservadora);
- os produtos de grama, cada um com o seu modelo, ou só o status e o motivo se ficou sem
  previsão.

Loja fechada e evento do dia vêm do calendário.

**Datas comemorativas (ADR-019).** Em Flores de corte, a previsão dos dias da semana do Dia
da Mulher, do Dia das Mães, do Dia dos Namorados, do Natal e do Ano Novo é multiplicada pelo
fator da data. Nas outras séries, a de 26 a 31/12 e a da semana do Dia do Trabalho, pela queda.
- **Quais dias:** de 6 dias antes até a data, com a loja aberta e sem abertura excepcional (no
  Ano Novo, de 26 a 31/12).
- **De onde vem o fator:** é recalculado a cada treino. É quanto a semana da data vendeu a
  mais ou a menos nas últimas 3 ocorrências.
  - **Alta (Flores de corte):** metade do aumento, entre 1 e 3.
  - **Queda (as outras):** a queda inteira, com piso de 0,2, só se cada ocorrência (pelo
    menos 2) ficou em até 0,8 de uma semana comum.
- **O que muda junto:** a faixa de 95% é multiplicada pelo mesmo número, e o total da loja
  herda o ajuste.
- **Onde fica:** o multiplicador fica em `series_forecasts.event_factor` e
  `forecast_history.event_factor`, e a frase do ajuste, no log da série.
- **Na tela:** nada. O fator é interno: a tela mostra o previsto e a faixa já ajustados, sem
  aviso, e a API não o entrega (`openapi.yaml` 6.0.0; até a 5.1.0 havia aviso na Previsão,
  no histórico e no relatório gerencial).
- **No walk-forward:** o fator de cada origem usa só a venda anterior a ela.
- **Por quê:** sem o ajuste, o modelo prevê uma semana comum, menos da metade do que essas
  semanas vendem (doc 08).

A previsão não é recalculada todo dia: com o mesmo modelo e os mesmos dados ela daria os
mesmos números. Ela muda quando a loja treina de novo com vendas novas.

## 4. O histórico da previsão

**Regra (ADR-023, desde 10/11/2026):** o previsto de um dia é o **registro mais antigo** dele,
e nenhum treino seguinte o troca. A regra pura está em `backend/domain/historico_previsao.py`;
a gravação, em `servico_previsao.gravar_historico`.

Cada treino concluído tem um `início` = dia seguinte à última venda. Em cada loja do treino,
grava só os dias de cada série que **ainda não têm registro**:

1. **da previsão nova, os 14 primeiros dias** (`FORECAST_HORIZON_DAYS`; `source = forecast`,
   `origin_date` = início). Os 91 dias previstos continuam em `series_forecasts` para a tela de
   Previsão; o histórico guarda só as 2 semanas que o teste de acerto avalia;
2. **do walk-forward, de cada dia a janela mais antiga que o previu** (`source = walk_forward`,
   `origin_date` = a origem dessa janela): a de maior horizonte, até 14 dias antes, feita com
   as vendas até a véspera da origem. Os 13 primeiros dias do período testado só aparecem nas
   primeiras janelas, com horizonte 1 a 13; os outros ficam com h = 14.

Os casos, sendo G os dias entre o início de um treino e o do seguinte:

| Intervalo | Fica da previsão anterior | O walk-forward do treino novo preenche |
| --- | --- | --- |
| G ≤ 14 (ex.: 7 ou 9) | os 14 dias inteiros (horizontes 1 a 14) | nada |
| G > 14 (ex.: 20) | os 14 dias | os G − 14 dias que sobram, até a véspera do início novo |
| 1º treino | — | os 69 dias antes do início (56 origens + 13) |

**Exemplo:**
- **Treino 1**, vendas até 03/10: grava a previsão de 04/10 a 17/10; o walk-forward preenche
  de 27/07 a 03/10 (27/07 com h = 1, ..., de 09/08 em diante com h = 14).
- **Treino 2**, 9 dias depois, vendas até 12/10: os dias de 04 a 17/10 já têm registro e
  ficam com o treino 1; grava de 18/10 a 26/10 (horizontes 6 a 14 da previsão nova).
- **Treino 3**, 20 dias depois, vendas até 01/11: de 27/10 a 01/11 ninguém previu; o
  walk-forward do treino 3 preenche, com a janela de 14 dias antes. Grava de 02/11 a 15/11.

**Antes (até 10/11/2026)** valia a última previsão feita antes do dia: cada treino apagava os
dias ≥ início e gravava a previsão inteira (91 dias), e do walk-forward entrava só o 1º dia de
cada janela (h = 1), com um complemento de 13 origens parciais para chegar até a última venda.
O histórico mostrava o previsto da véspera nos dias do walk-forward, otimista perto da
previsão que a loja via. `semear_historico --recriar` refaz um histórico gravado assim.

**O que cada ponto guarda** (`forecast_history`):
- previsto e faixa;
- `source`;
- `origin_date` (o horizonte é `day − origin_date + 1`);
- `job_id`;
- `store_closed`: se o calendário dava a loja fechada quando o dia foi previsto. Se o
  calendário for corrigido depois, a tela ainda explica um previsto zero.

**A tela** (`GET /api/v1/painel/historico/{loja}/{categoria|produto}/{item}`) mostra o
vendido de cada dia (sem encomendas grandes, de `sales`) contra o previsto gravado, numa linha
só: **o que a previsão mostrava** (`forecast`) ou **o teste do treino** (`walk_forward`), os
dois com até 14 dias de antecedência.

O tooltip mostra com quantos dias de antecedência o dia foi previsto ("previsto 14 dias antes
(teste do treino)") e se a previsão contava com a loja fechada.

Acima do gráfico, 2 medidas do teste (walk-forward) da série no último treino concluído que a
avaliou (`avaliacao` da resposta; se o último treino a recusou, vale o anterior), em linguagem
simples e com o nome técnico embaixo:
- **Erro por dia, em unidades (MAE):** quanto a previsão de um dia erra, em média, para mais ou
  para menos;
- **Margem de incerteza (IC 95%):** metade da distância média entre o mínimo e o máximo
  previstos para um dia.

O erro em % da venda (WAPE) saiu da tela em 10/11/2026: no dia a dia ele passa de 90% em séries
em que poucos pedidos grandes fazem a maior parte da venda (Grama de Itabirito, 91% contra 117%
de repetir a semana anterior), e assustava mais do que informava. A API ainda o entrega em
`avaliacao.wape_pct`.

No gráfico, o teste do treino (`walk_forward`) é a linha tracejada, com a marca "início do teste
do treino", e a previsão gravada (`forecast`) é a linha cheia, com a marca "início da previsão".

Todas nos dias de loja aberta do walk-forward. Até a versão 6 da API a tela mostrava acerto no
total de 14 dias, cobertura da faixa, origens que venciam a naïve e previsto ÷ vendido, lidos do
painel.

**Pontos de atenção:**
- **A fronteira é o dia seguinte à última venda, não o dia do clique.** Se a loja treina no
  dia 20 com vendas só até o dia 10, a previsão nova cobre de 11 a 24, mas os dias que a
  previsão anterior já tinha gravado ficam com ela.
- **Uma venda apagada que faz a última venda voltar** não muda o histórico: os dias gravados
  ficam com o registro mais antigo.
- **Banco com histórico de outra regra:**
  `python -m backend.scripts.semear_historico [--recriar]` preenche o histórico a partir do
  último treino (walk-forward guardado em `series_backtest_points` + os 14 primeiros dias da
  previsão). `--recriar` apaga antes tudo o que estava gravado. O walk-forward guardado não tem
  o fator das datas comemorativas: `event_factor` fica nulo nesses dias (o previsto já vem
  com ele).

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
| `series_forecasts` | os 91 dias de cada série (14 até 08/11/2026), com o multiplicador da data comemorativa (`event_factor`, ADR-019) | sempre (é a origem dos valores que o histórico trocou) |
| `series_backtest_points` | todas as origens e horizontes do walk-forward | só nos últimos 4 treinos concluídos |
| `forecast_history` | o previsto mais antigo de cada dia (14 dias de cada previsão + a janela mais antiga do walk-forward), com o `event_factor` que entrou nele | sempre |
| `processing_log` | cada planilha: contagens, período, dias faltando, `forecast_job_id` | sempre |

| Comando (a partir de `ia-predictor/`) | Para quê |
| --- | --- |
| `python -m backend.scripts.treinar_previsoes [--workers N]` | treinar fora da API (Render) |
| `python -m backend.scripts.semear_historico [--recriar]` | preencher o histórico de um banco antigo |
| `python -m backend.scripts.reclassificar_produtos [--aplicar]` | aplicar ao catálogo do banco as regras de categoria de hoje |

| Teste | O que garante |
| --- | --- |
| `tests/unit/test_historico_previsao.py` | a regra do histórico: registro mais antigo, janela mais antiga do walk-forward, 14 dias da previsão, loja fechada |
| `tests/unit/test_treino_serie.py` | walk-forward até a última venda, métricas, diagnóstico e coeficientes; o fator das datas só na semana da data; a previsão final além do horizonte do walk-forward (ADR-021); d = 1 sem constante (ADR-020) |
| `tests/unit/test_datas_comemorativas.py` | o fator das datas: regra de cada ano, metade do aumento, sem olhar o futuro, piso e teto, abertura excepcional, últimas ocorrências |
| `tests/unit/test_cobertura_planilha.py` | os dias faltando: entre a base e a planilha, domingo e feriado, loja ausente, dentro da planilha |
| `tests/integration/test_servico_previsao.py` | treino de ponta a ponta, histórico gravado, planilhas ligadas, limpeza do walk-forward, script; d escolhido pelo walk-forward e receita na impressão digital |
| `tests/integration/test_upload.py` | conferência sem gravar, aviso de dias faltando, gravação com o aviso no `processing_log` |
