# 10 — Estacionariedade e a escolha de d série a série

**Data:** 2026-11-09 (refeito no mesmo dia: a 1ª versão testava uma série e uma janela diferentes das
do modelo, §3.1) ·
**Status:** concluído; adotado pelo [ADR-020](ADR-020-diferenciacao-por-serie.md)
**Scripts:** `ia-predictor/training_scripts/validation/estacionariedade_fiel_ao_modelo.py` (testes),
`variantes_nivel_sazonal.py` (walk-forward de d = 0 × d = 1, 52 treinos semanais)
**Resultados:** `ia-predictor/training_scripts/results/metrics/estacionariedade_fiel_ao_modelo/janelas.csv`,
`variantes_nivel_sazonal/` e `variantes_nivel_sazonal_produtos/`

---

## 1. A pergunta

O treino usava d = 0 em todas as séries (ADR-017), com base no ADF do histórico inteiro. No
walk-forward, d = 1 errou menos em várias séries: −9,5% na Grama de Jardim Canadá, −2,6% na soma
dos produtos de grama. Três perguntas:

1. Os testes de estacionariedade, aplicados ao que o modelo de fato diferencia, pedem d = 1?
2. Qual teste — KPSS ou ADF — concorda com o walk-forward?
3. O d deve ser escolhido série a série, e por qual critério?

Resposta curta:

- **O KPSS concorda com o walk-forward; o ADF não.** Nenhuma série em que o KPSS rejeita a
  estacionariedade do nível fica melhor com d = 0 (8 de 8 ficam melhor com d = 1), e a correlação
  entre "% das janelas em que ele rejeita" e o ganho de d = 1 é −0,48 (p = 0,02). O ADF diz
  "estacionária" em quase tudo, inclusive onde d = 1 erra 9,5% menos — a distorção que a
  literatura prevê para estas séries (§2.3).
- **Nem toda série que ganha com d = 1 é não estacionária pelo KPSS:** 8 de 15. As outras 7 são
  séries esparsas (3 a 22 un./dia), em que o KPSS não tem poder para detectar o nível que anda —
  o teste é inconclusivo, não negativo.
- **O d sai do walk-forward de cada série.** Usar o KPSS como critério erra 2,5% menos que d = 0;
  escolher pelo erro do walk-forward, 3,6–3,8% menos — praticamente o limite de quem escolhesse
  olhando o ano inteiro (3,9%). O KPSS fica como fundamento nas séries em que rejeita.

## 2. O que a teoria diz

### 2.1 Como se escolhe d

No ARIMA, d é o número de diferenças que tornam a série estacionária. O AIC **não** compara modelos
com d diferente (a verossimilhança de y e a de Δy não são comparáveis), então d é escolhido antes,
por teste, ou pelo erro fora da amostra (Hyndman & Athanasopoulos, *FPP3*, cap. 9 e §5.10). O
procedimento do `auto.arima` (Hyndman & Khandakar, 2008) usa o **KPSS**: d = 0 se ele não rejeita a
estacionariedade a 5%. Com regressores, o teste é feito **nos resíduos da regressão** — o SARIMAX do
sistema é uma regressão com erros ARIMA, yₜ = c + xₜ'β + uₜ, e o d se aplica a uₜ.

| Teste | H0 | Rejeitar quer dizer |
| --- | --- | --- |
| ADF (Said & Dickey, 1984), DF-GLS (Elliott, Rothenberg & Stock, 1996), Phillips-Perron | tem raiz unitária | estacionária → d = 0 |
| KPSS (Kwiatkowski, Phillips, Schmidt & Shin, 1992) | nível estacionário | nível não estacionário → d = 1 |

### 2.2 Nível local: por que d = 1 sem passeio aleatório puro

No modelo de nível local (Muth, 1960; Harvey, 1989), yₜ = μₜ + xₜ'β + uₜ, μₜ = μₜ₋₁ + ηₜ. Com
σ²_η > 0, a forma reduzida é integrada de ordem 1 — o nível local puro é exatamente um
**ARIMA(0,1,1)**, com o MA tanto mais perto de −1 quanto menor o sinal-ruído σ²_η/σ²_u — e a
previsão é a suavização exponencial: parte do nível recente. Com σ²_η = 0, d = 0 basta.

O KPSS é o teste LM **dessa hipótese**, σ²_η = 0 (Kwiatkowski et al., 1992, §2; Nyblom &
Mäkeläinen, 1983). E o seu poder cai com o sinal-ruído: quando o ruído do dia é grande perto da
variação do nível, ele raramente rejeita, mesmo com o nível andando (Kwiatkowski et al., 1992,
simulações de poder). Não rejeitar, numa série esparsa, é falta de evidência, não evidência de
estacionariedade.

### 2.3 Por que o ADF erra nestas séries

Quando a diferença da série tem raiz MA perto de −1 (o nível local com sinal-ruído baixo), o ADF
rejeita a raiz unitária muito acima dos 5% nominais (Schwert, 1989; Agiakloglou & Newbold, 1992). A
correção é usar mais lags na regressão aumentada (Schwert, 1989; Ng & Perron, 1995, 2001); o
Phillips-Perron, que corrige sem lags, é o mais distorcido (Schwert, 1989). Nas 23 séries, a
autocorrelação de lag 1 da diferença fica entre −0,43 e −0,54: é esse caso.

## 3. Como foi testado

### 3.1 O que estava errado na 1ª versão

A 1ª versão deste documento (`estacionariedade_janela_aic.py`, `estacionariedade_grama.py`) não
testava o que o modelo diferencia:

1. **Série:** testava o resíduo de uma regressão só nos **dias de loja aberta, emendados**, sem a
   exógena `loja_fechada`. A semana passava a ter 6 dias (o lag 7 deixava de ser o mesmo dia da
   semana anterior), e cada feriado deslocava o resto. O SARIMAX usa **todos os dias do calendário**,
   com `loja_fechada` entre as exógenas.
2. **Janela:** testava a janela do AIC (365 dias antes da 1ª origem do walk-forward, que termina 68
   dias antes do corte), mas a previsão de cada corte é ajustada nos 365 dias **até o corte**.

Os números abaixo são do teste corrigido. A 1ª versão chegava à mesma direção, mais fraca (KPSS em
46–60% das janelas das famílias grandes, contra 62–77% agora; correlação −0,41, p = 0,055).

### 3.2 Desenho

- **Séries:** as 8 categorias (4 × 2 lojas) e os 15 produtos de grama com previsão, no fluxo diário
  sem encomendas grandes (a série do treino, `servico_previsao._montar_series`).
- **Série testada:** uₜ, o resíduo de MQO de y nas **mesmas exógenas do SARIMAX** (constante, 6
  dummies de dia da semana, `loja_fechada`, `abertura_excepcional`), em **todos os dias** da janela.
- **Janelas:** a de ajuste (365 dias até o corte) em cada um dos 52 treinos semanais de 01/03/2025 a
  21/02/2026; a do AIC, como comparação.
- **Testes, a 5%:** KPSS de nível (lags automáticos, Hobijn, Franses & Ooms, 2004; e a regra curta
  do `auto.arima`, ⌊4(n/100)^¼⌋ = 5); ADF com constante e 4 regras de lags — AIC, BIC, t-stat e o
  lag fixo de Schwert, ⌊12(n/100)^¼⌋ = 16 (máximo das outras 3); DF-GLS (`arch`, lags por AIC);
  Phillips-Perron (`arch`).
- **Ligação com a prática:** o ganho de d = 1 é o do walk-forward de `variantes_nivel_sazonal.py`
  (52 treinos semanais, ordem por AIC a cada 4 treinos para cada d, erro diário dos 7 dias
  seguintes a cada treino, dias de loja aberta), com Diebold-Mariano (erro-padrão HAC, lag 7).
  "Não estacionária" = o teste aponta não estacionariedade em pelo menos metade das 52 janelas.

## 4. Resultados

### 4.1 Série a série

% das janelas de ajuste em que cada teste aponta nível **não** estacionário (KPSS: rejeita; ADF e
DF-GLS: não rejeitam a raiz unitária). "Erro com d = 1": erro do walk-forward com d = 1 sobre o de
d = 0; em negrito, diferença significativa a 5%.

| Série | Venda/dia | KPSS | ADF (AIC) | ADF (lag de Schwert) | DF-GLS | Erro com d = 1 | p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| JC · Grama | 1.337 | **77%** | 17% | 75% | 10% | **−9,5%** | < 0,001 |
| JC · Plantas diversas | 1.220 | **73%** | 15% | 46% | 17% | −2,7% | 0,24 |
| ITA · Grama | 310 | **65%** | 6% | 48% | 6% | −1,3% | 0,48 |
| JC · Produtos de jardim | 455 | **62%** | 0% | 13% | 2% | −2,2% | 0,22 |
| ITA · Produtos de jardim | 200 | 48% | 0% | 8% | 2% | −1,0% | 0,65 |
| ITA · Plantas diversas | 537 | 29% | 0% | 15% | 10% | +1,8% | 0,39 |
| JC · Flores de corte | 57 | 8% | 0% | 0% | 0% | **+3,0%** | 0,001 |
| ITA · Flores de corte | 60 | 4% | 0% | 0% | 2% | **+2,9%** | 0,042 |
| JC · Grama preta Ana (167) | 7 | **100%** | 0% | 0% | 5% | −1,1% | 0,90 |
| JC · Grama Esmeralda (3) | 603 | **69%** | 0% | 63% | 13% | −3,3% | 0,10 |
| JC · Grama Amendoim (147) | 564 | **69%** | 2% | 33% | 4% | −2,7% | 0,10 |
| ITA · Grama Esmeralda (00013475) | 219 | **67%** | 6% | 23% | 4% | **−3,3%** | 0,043 |
| ITA · Grama Esmeralda (3) | 1 | 44% | 19% | 19% | 0% | +0,6% | 0,93 |
| JC · Grama Esmeralda ITO (00013475) | 3 | 39% | 0% | 0% | 0% | **−23,5%** | < 0,001 |
| JC · Grama preta pelo de urso (166) | 22 | 17% | 0% | 0% | 4% | **−6,5%** | < 0,001 |
| JC · Capim dos Texas roxo (1293) | 11 | 12% | 2% | 2% | 0% | +8,5% | 0,07 |
| ITA · Grama Amendoim (147) | 61 | 10% | 0% | 0% | 2% | −3,1% | 0,06 |
| JC · Grama São Carlos (710) | 79 | 10% | 0% | 0% | 0% | +2,5% | 0,12 |
| JC · Capim dos Texas roxo (00020227) | 5 | 4% | 13% | 21% | 12% | **+10,5%** | 0,029 |
| JC · Capim dos Texas verde (1294) | 3 | 0% | 0% | 0% | 6% | **−5,0%** | 0,009 |
| JC · Grama preta pelo de urso saq. (00150005) | 13 | 0% | 0% | 0% | 0% | −0,7% | 0,29 |
| ITA · Grama São Carlos (710) | 15 | 0% | 4% | 4% | 2% | −0,5% | 0,83 |
| JC · Grama Zeon (1739) | 6 | 0% | 0% | 0% | 0% | **+6,1%** | 0,001 |

- **KPSS ≥ 50% (8 séries): todas ficam melhor com d = 1.** São as categorias grandes (Grama das 2
  lojas, Plantas e Produtos de Jardim Canadá) e os produtos de grama que mais vendem.
- **d = 1 melhor com o KPSS abaixo de 50% (7 séries):** Esmeralda ITO de Jardim Canadá, grama preta
  pelo de urso, capim verde (as 3 significativas), Produtos de jardim de Itabirito (48%, no limite),
  Amendoim de Itabirito, grama preta de saco e São Carlos de Itabirito. Todas, menos Produtos de
  jardim, vendem de 3 a 61 un./dia: o KPSS não tem poder para ver o nível nelas (§2.2).
- **d = 0 melhor (8 séries):** nenhuma com o KPSS acima de 50%. Significativas: Flores de corte nas 2
  lojas, Zeon e capim dos Texas roxo (00020227).

### 4.2 KPSS × ADF

| Teste (janela de ajuste) | Lags (média) | Acerta o lado do walk-forward (de 23) | Spearman com o ganho de d = 1 | Erro, usando o teste para escolher d a cada treino |
| --- | --- | --- | --- | --- |
| **KPSS** | automático | **16** | **−0,48 (p = 0,02)** | **−2,5%** |
| KPSS, lags curtos | 5 | 15 | −0,48 (p = 0,02) | −2,5% |
| ADF, lag de Schwert | 16 | 10 | −0,20 (n.s.) | −2,2% |
| ADF, t-stat | 8,1 | 9 | −0,08 (n.s.) | −1,2% |
| ADF, AIC | 3,2 | 8 | +0,02 (n.s.) | −0,4% |
| ADF, BIC | 0,2 | 8 | +0,13 (n.s.) | 0 (d = 0 em tudo) |
| DF-GLS | AIC | 8 | −0,36 (n.s.) | 0 |
| Phillips-Perron | — | 8 | — | 0 (rejeita a raiz unitária em todas as janelas) |

"Acerta o lado": a série fica melhor com d = 1 e o teste a chama de não estacionária (≥ 50% das
janelas), ou o contrário.

- **O ADF depende do número de lags, como a teoria prevê.** Com poucos lags (BIC, AIC) ele rejeita
  a raiz unitária em quase todas as janelas e daria d = 0 em tudo — inclusive na Grama de Jardim
  Canadá, onde d = 1 erra 9,5% menos. Com o lag de Schwert (16), passa a apontar justamente as
  séries que o KPSS aponta (Grama de Jardim Canadá em 75% das janelas, Esmeralda em 63%). Quanto mais
  corrigido, mais perto do KPSS.
- **O Phillips-Perron**, o mais sensível à raiz MA perto de −1 (Schwert, 1989), rejeita em 100%.
- **O ADF não serve para escolher d nestas séries; o KPSS serve como evidência**, e é o teste que o
  procedimento padrão usa.

### 4.3 Critério para escolher d série a série

Combinando, treino a treino, as previsões de d = 0 e d = 1 já calculadas (23 séries, treino semanal,
7 dias seguintes, ano de 03/2025 a 02/2026; erro sobre d = 0 em tudo):

| Critério | Erro | p | Trocas de d no ano (23 séries) |
| --- | --- | --- | --- |
| d = 0 em tudo (ADR-017) | 0 | — | 0 |
| KPSS na janela de ajuste de cada treino | −2,5% | 0,002 | 70 |
| KPSS, maioria das últimas 4 janelas | −2,3% | 0,006 | 38 |
| KPSS na janela do AIC (a 1ª versão) | −1,8% | 0,007 | 69 |
| d = 1 em tudo, exceto Flores de corte (1ª versão do ADR-020) | −3,6% | < 0,001 | 0 |
| **Erro do walk-forward da série nas últimas 8 semanas (o que o treino faz)** | **−3,6%** | < 0,001 | 109 |
| Erro nas últimas 13 / 26 semanas | −3,8% / −3,7% | < 0,001 | 74 / 49 |
| Limite: o melhor d de cada série, escolhido olhando o ano inteiro | −3,9% | < 0,001 | 0 |

- O KPSS como critério perde para o walk-forward pelas 7 séries esparsas em que d = 1 ajuda sem ele
  rejeitar.
- Escolher pelo erro recente da própria série chega perto do limite de quem visse o futuro, sem
  olhar o futuro. É o que o treino passa a fazer (ADR-020): o walk-forward de 56 origens (8 semanas)
  roda com d = 0 e com d = 1, e fica o d que errou menos.

## 5. Conclusão

- **O d de cada série sai do walk-forward**, entre 0 e 1. O critério é o erro fora da amostra, o
  que a literatura recomenda quando o AIC não serve (modelos com d diferente).
- **Fundamento teórico, onde o teste decide:** nas séries grandes de Grama, Plantas e Produtos de
  jardim o KPSS — o teste LM da variância do nível — rejeita a estacionariedade na maioria das
  janelas, e nenhuma série em que ele rejeita fica melhor com d = 0. O nível delas anda dentro da
  janela de 365 dias; a forma reduzida de um nível local é integrada de ordem 1, e d = 1 com termo
  MA acompanha esse nível.
- **Onde o teste não decide** — séries esparsas, sinal-ruído baixo —, o walk-forward decide; em
  várias delas d = 1 ajuda, porque a previsão de um ARIMA(0,1,1) é a suavização exponencial do
  nível, mais estável que a média do ano.
- **O ADF não sustenta d = 0:** ele rejeita a raiz unitária por distorção (raiz MA perto de −1), e
  passa a concordar com o KPSS quando recebe os lags que a correção pede.
- Com d = 1 o modelo fica sem constante (`forecaster.ajustar`).

## 6. Limitações

- **Um ano de avaliação** (52 treinos) e janelas sobrepostas: as porcentagens não são testes
  independentes.
- **Viés de seleção nas métricas:** os indicadores da tela vêm do walk-forward do d
  escolhido — o menor de 2 erros —, então ficam um pouco otimistas.
- **O d pode trocar entre treinos** (≈ 2 vezes por série por ano na simulação de 26 semanas, ≈ 5 na
  de 8): a forma da previsão muda junto. O histórico congelado mostra o que a loja viu em cada
  semana.
- **Custo:** o treino roda a escolha da ordem e o walk-forward 2 vezes por série: no treino local, 40 min contra 13,5 min com um d só (14 processos).
- **d = 1 perde nas viradas de temporada:** no walk-forward do treino de produção (dez/2025–fev/2026,
  a queda depois das festas), Grama erra mais com d = 1. A escolha pelo walk-forward da própria
  série leva isso em conta naquele treino.
- **Horizonte longo:** a previsão com d = 1 é melhor até a 6ª semana e pior da 7ª em diante
  (ADR-021 §3.1).
- **KPSS com p-valor interpolado** e limitado a [0,01; 0,10] no `statsmodels`.

## Referências

- Agiakloglou, C.; Newbold, P. (1992). Empirical evidence on Dickey-Fuller-type tests. *Journal of
  Time Series Analysis*, 13(6), 471–483.
- Elliott, G.; Rothenberg, T. J.; Stock, J. H. (1996). Efficient tests for an autoregressive unit
  root. *Econometrica*, 64(4), 813–836.
- Harvey, A. C. (1989). *Forecasting, Structural Time Series Models and the Kalman Filter*.
  Cambridge University Press.
- Hobijn, B.; Franses, P. H.; Ooms, M. (2004). Generalizations of the KPSS-test for stationarity.
  *Statistica Neerlandica*, 58(4), 483–502.
- Hyndman, R. J.; Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*, 3ª ed. OTexts,
  §5.10 (validação cruzada de séries temporais), cap. 9 (ARIMA) e cap. 10 (regressão com erros
  ARIMA).
- Hyndman, R. J.; Khandakar, Y. (2008). Automatic time series forecasting: the forecast package for
  R. *Journal of Statistical Software*, 27(3).
- Kwiatkowski, D.; Phillips, P. C. B.; Schmidt, P.; Shin, Y. (1992). Testing the null hypothesis of
  stationarity against the alternative of a unit root. *Journal of Econometrics*, 54, 159–178.
- Muth, J. F. (1960). Optimal properties of exponentially weighted forecasts. *Journal of the
  American Statistical Association*, 55(290), 299–306.
- Ng, S.; Perron, P. (1995). Unit root tests in ARMA models with data-dependent methods for the
  selection of the truncation lag. *Journal of the American Statistical Association*, 90(429),
  268–281.
- Ng, S.; Perron, P. (2001). Lag length selection and the construction of unit root tests with good
  size and power. *Econometrica*, 69(6), 1519–1554.
- Nyblom, J.; Mäkeläinen, T. (1983). Comparisons of tests for the presence of random walk
  coefficients in a simple linear model. *Journal of the American Statistical Association*,
  78(384), 856–864.
- Said, S. E.; Dickey, D. A. (1984). Testing for unit roots in autoregressive-moving average models
  of unknown order. *Biometrika*, 71(3), 599–607.
- Schwert, G. W. (1989). Tests for unit roots: a Monte Carlo investigation. *Journal of Business &
  Economic Statistics*, 7(2), 147–159.
