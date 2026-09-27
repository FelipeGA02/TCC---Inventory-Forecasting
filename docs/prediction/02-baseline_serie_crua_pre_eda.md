# 02 — Linha de base: SARIMA sobre 1 série crua (dados pré-EDA)

**Experimento:** `A0_sarima_serie_crua_pre_eda` · **Data:** 2026-09-27  
**Script:** `ia-predictor/training_scripts/baseline/sarimax_serie_crua.py`  
**Resultados:** `training_scripts/results/metrics/baseline_A0_sarima_serie_crua_pre_eda.json`
(+ `_holdout.csv`) · gráficos em `training_scripts/results/plots/baseline/`

## Objetivo

Estabelecer o **ponto zero** da modelagem para medir o ganho de cada etapa seguinte:

1. **este experimento:** série crua, sem EDA e sem exógenas;
2. aplicação dos achados do EDA (L1 por unidade, 2 lojas, encomendas fora, teto p99);
3. exógenas de calendário (A1);
4. bases de enriquecimento (clima, feriados municipais; Modelo B).

## O que entrou

| Item | Valor |
| --- | --- |
| Base | `data/processed/contas_a_receber_taxonomia.csv`: Etapa 3 do pré-processamento de 2026-08-30 (commit `8e5aa6e`), com as colunas removidas e a taxonomia, **antes do EDA** |
| Série | **1 série**: soma diária de `qtdade` de todas as lojas (Jardim Canadá, Itabirito, Garden Center) e categorias |
| Regras aplicadas | só a regra que já existia antes do EDA: `Servico e taxa` fica fora (5.342 linhas); dias sem venda = 0 |
| Não aplicado | separação de encomendas grandes, teto p99, junção Garden Center→Jardim Canadá, exógenas |
| Período | 2024-01-02 → 2026-02-28 · 789 dias (135 zerados, quase todos domingos) |
| Perfil | média 4.995/dia · mediana 3.931 · máximo 66.377 · CV 1,10 |
| Modelo | SARIMA(1,0,1)(1,0,1)₇ + constante, com log1p (CV > 0,7) e d = 0 (ADF p < 0,001); ordem escolhida por AIC num grid de 36 combinações |

## Resultados

| Métrica | Hold-out 28d | Walk-forward (4 folds × 14d) |
| --- | --- | --- |
| MAE (unidades/dia) | 1.415 | 1.394 |
| MASE | 0,404 | 0,396 |
| RMSSE | 0,319 | 0,289 |
| **MAE relativo à naïve sazonal na mesma janela** | **0,82** | **0,83** (vence a naïve em 2 de 4 folds) |
| Cobertura IC 95% | 92,9% | 96,4% |
| **Largura média do IC 95%** | **79 mil** | **81 mil** (≈ 16× a média diária) |
| MAPE (dias com venda) | 38,4% | — |
| Ljung-Box p (lag 7 / 14) | 0,79 / 0,91 | — |
| Shapiro-Wilk p | ≈ 0 | — |

Walk-forward por fold (MAE do modelo ÷ MAE da naïve): 04/jan 0,35 · 18/jan 1,33 ·
01/fev 1,10 · 15/fev 0,52.

Pelos limiares do CLAUDE.md, o status formal é **`trained`** (MASE < 1, cobertura no intervalo [90%, 98%]).

## Leitura: por que o MASE de 0,40 engana

- **Denominador inflado.** O MASE divide o erro pelo erro da naïve sazonal *dentro do
  treino*. Esse treino contém os picos de encomenda (até 66 mil unidades num dia), o que
  infla a escala e faz qualquer erro parecer pequeno. Comparando com a naïve **na mesma
  janela de teste**, o ganho é modesto (MAE relativo de 0,82) e inconsistente: a naïve
  vence em 2 dos 4 folds.
- **Intervalo inútil na prática.** A cobertura passa porque o IC 95% é enorme (≈ 80 mil
  para uma média de 5 mil/dia). Os picos de encomenda na série forçam o modelo a admitir
  qualquer valor. Um intervalo desse tamanho não serve para decidir reposição.
- **Previsão ≈ perfil semanal médio.** A previsão pontual praticamente repete o padrão
  semanal (domingo = 0), sem prever os picos. Os resíduos não têm autocorrelação
  (Ljung-Box ok), mas estão longe da normal (caudas pesadas por causa das encomendas).
- **Hold-out calmo.** Fevereiro/2026 não teve picos grandes. O teste mais exigente
  (dezembro, com picos de 41 a 66 mil) ficou no treino.

## Como comparar com os próximos experimentos

Os experimentos seguintes mudam o **alvo** (2 séries por unidade, sem encomendas). Por isso,
MASE contra MASE, cada um com seu próprio denominador, **não é comparação justa**. Para
cada experimento novo, usar:

1. **MAE relativo à naïve na mesma janela** e número de folds em que vence a naïve;
2. **largura média do IC 95%** junto com a cobertura (um intervalo mais estreito com a
   mesma cobertura é ganho real);
3. MAE em unidades somando as previsões das unidades de volta ao total, na mesma janela e
   nos mesmos folds (origens 2026-01-04, 01-18, 02-01, 02-15).
