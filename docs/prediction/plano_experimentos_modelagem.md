# Plano de Ação — Experimentação Comparativa de Modelos de Previsão

**Objetivo**: produzir evidência empírica, conforme exige o Princípio II da constituição
("Estatística Antes de Machine Learning") e o ADR-001, comparando:

1. SARIMAX **sem enriquecimento** (baseline atual, só dados internos)
2. SARIMAX **enriquecido** com bases externas
3. Redes neurais e outros modelos de ML, usando as mesmas técnicas de validação do artigo

**Onde isso roda**: em `ia-predictor/training_scripts/`, não em `backend/domain/`. É uma
pasta de scripts Python (não notebooks — o `.gitignore` já exclui `*.ipynb`, ver
`docs/project/current_files_state.md` §2) dedicada a testar, treinar e validar
o SARIMAX antes de qualquer variante entrar no backend de produção. Os módulos
`backend/domain/` hoje estão vazios (stubs); não faz sentido implementá-los 3 vezes (uma
por variante). Prototipa-se tudo em `training_scripts/`, decide-se o vencedor com números,
e só então se implementa uma vez em `backend/domain/` (Fase 3 do `tasks.md`).

Subpastas, uma por etapa da comparação (evita misturar código de fases diferentes):

| Subpasta | Fase | Conteúdo |
| --- | --- | --- |
| `eda/` | 1.1 | Sazonalidade, tendência, CV por produto, seleção do Top-N |
| `baseline/` | 1 | Modelo A0 (SARIMA puro) e A1 (SARIMAX interno) |
| `enriched/` | 3 | Modelo B (SARIMAX interno + exógenas externas) |
| `alternative_models/` | 4 | ETS/Holt-Winters, XGBoost, Prophet, rede neural global |
| `validation/` | 1, 3, 4 | Walk-forward CV, testes de resíduos (Ljung-Box, Shapiro-Wilk) e de significância (Diebold-Mariano/Wilcoxon) — compartilhado entre fases, para garantir os mesmos splits/protocolo em todas as comparações |
| `results/` | todas | `metrics/*.csv` e `plots/` gerados pelos experimentos — staging; só o pipeline vencedor migra para `ia-predictor/results/` (produção) na Fase 5 |

---

## Fase 1 — Baseline sem enriquecimento

**Dados**: só `data/processed/contas_a_receber.csv` (transacional interno).

- [ ] 1.1 EDA (`tasks.md` T000b, em `training_scripts/eda/`): sazonalidade, tendência,
      CV por produto, seleção do Top-N produtos (ver `TOP_N_PRODUCTS=20` em `.env`) →
      `docs/eda_report.md`
- [ ] 1.2 `prepare_monthly_series()` (`training_scripts/baseline/`): série mensal por
      produto, freq='MS', ≥15 obs (spec: `SPECS.md` §5.1)
- [ ] 1.3 **Modelo A0 — SARIMA puro** (`training_scripts/baseline/`, sem nenhuma
      exógena): ablação de referência, mostra o piso de desempenho sem qualquer
      variável externa
- [ ] 1.4 **Modelo A1 — SARIMAX interno** (`training_scripts/baseline/`, spec
      `SPECS.md` §5.2): 15 variáveis já definidas (`mkt_*`, `prod_*`, `mes`,
      `trimestre`, `alta_temporada`), ponderadas por importância RF/MDI (`SPECS.md`
      §5.3, clip 0.1)
- [ ] 1.5 Seleção de ordem via grid AIC (36 combinações, D=0, m=12) — `SPECS.md` §6
- [ ] 1.6 Avaliação (`training_scripts/validation/`): hold-out 3 meses + walk-forward
      CV (≥4 folds); métricas MAE, RMSE, MAPE (filtrado), SMAPE, R²; diagnóstico de
      resíduos Ljung-Box + Shapiro-Wilk
- [ ] 1.7 Consolidar `training_scripts/results/metrics/baseline_A0_A1.csv` com
      métricas por produto

**Checkpoint**: scorecard A0 vs A1 por produto, prova que a exógena interna já ajuda
(ou não) antes de qualquer dado externo entrar.

---

## Fase 2 — Aquisição das bases de enriquecimento externas

Esta é a parte **nova**, fora do que `SPECS.md`/artigo já documentam — precisa de ADR
próprio (`docs/prediction/ADR-008-variaveis-exogenas-externas.md`) justificando cada fonte.
Nenhuma delas envolve dado pessoal de cliente → sem conflito com Princípio VI/LGPD.

| Fonte | Dado | API/acesso | Observação |
| --- | --- | --- | --- |
| Feriados nacionais | Datas exatas (Natal, Tiradentes, etc.) | [BrasilAPI](https://brasilapi.com.br/api/feriados/v1/{ano}) — gratuita, sem chave | Cobre só nível nacional |
| Feriados municipais | Nova Lima e Itabirito/MG (aniversário da cidade, padroeiro) | Decretos municipais — **curadoria manual**, não tem API pública confiável | Baixo volume, tabela fixa versionada no repo |
| Datas comemorativas móveis | Dia das Mães (2º domingo de maio), Dia dos Namorados (12/jun fixo no Brasil), Dia das Mulheres (8/mar fixo) | cálculo determinístico (sem API) | Refina o `alta_temporada` binário atual para "dias até a data" |
| Clima | Temperatura e precipitação diária/mensal em Nova Lima/Itabirito | [Open-Meteo Historical Weather API](https://open-meteo.com) — gratuita, sem chave, por lat/long | Chuva pode afetar entrega/venda de flores de corte |
| Indicadores econômicos | IPCA, Selic, confiança do consumidor | [Banco Central SGS](https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados) — gratuita, sem chave | Séries mensais, já na granularidade certa |
| Interesse de busca | Volume de busca "flores", "buquê", "dia das mães presente" | `pytrends` (não oficial, Google Trends) | Instável/rate-limited; tratar como opcional, não crítico |

- [ ] 2.1 Criar `backend/infrastructure/external_data/` (camada de I/O — clientes HTTP,
      cache local em `data/external/`) — **não é domínio**, por isso fica em
      `infrastructure/`, nunca em `domain/features/` (Princípio I)
- [ ] 2.2 Cliente para cada fonte da tabela acima, com cache em disco (evita rate-limit
      e permite rodar offline depois da primeira coleta)
- [ ] 2.3 Curadoria manual da tabela de feriados municipais (Nova Lima + Itabirito),
      versionada como CSV/JSON no repo
- [ ] 2.4 `docs/prediction/ADR-008-variaveis-exogenas-externas.md`: por que cada fonte foi
      escolhida, o que foi descartado e por quê
- [ ] 2.5 Atualizar `SPECS.md` §5.2 com a tabela de variáveis externas (mesmo formato
      da tabela de exógenas internas)

**Checkpoint**: `data/external/` populado com séries mensais alinhadas ao período
Jan/2024–Fev/2026, prontas para merge com a série de cada produto.

---

## Fase 3 — SARIMAX enriquecido vs. baseline

- [ ] 3.1 `domain/features/external_exogenous.py` (lógica **pura**, sem I/O): recebe os
      DataFrames já coletados na Fase 2 e faz o merge mensal com o índice do produto
- [ ] 3.2 **Modelo B — SARIMAX interno + externo** (`training_scripts/enriched/`):
      mesmas 15 variáveis de A1 + as novas (clima, feriados precisos, indicadores
      econômicos, tendência de busca)
- [ ] 3.3 Reaplicar RF/MDI para ponderar o conjunto ampliado (mitiga multicolinearidade
      entre `mkt_taxa_desconto` e IPCA, por exemplo)
- [ ] 3.4 Mesmo protocolo de avaliação da Fase 1 (`training_scripts/validation/`:
      hold-out 3m + walk-forward CV ≥4 folds + Ljung-Box + Shapiro-Wilk) — **mesmos
      produtos, mesmos splits** que A0/A1, para comparação justa
- [ ] 3.5 Teste estatístico de significância da diferença (ex.: Diebold-Mariano ou
      Wilcoxon pareado nos erros de A1 vs B) — não basta "SMAPE caiu 2%", precisa
      mostrar que a diferença não é ruído
- [ ] 3.6 Relatório `docs/prediction/comparacao_enriquecimento.md`: tabela A0 vs A1 vs B por
      produto, com veredito (enriquecimento externo compensa a complexidade adicional
      ou não)

**Checkpoint**: decisão documentada — variáveis externas entram ou não na versão de
produção do SARIMAX.

---

## Fase 4 — Redes neurais e outros modelos

Constituição Princípio II exige evidência quantitativa de superioridade antes de
introduzir ML/redes neurais — esta fase produz exatamente essa evidência.

**Cuidado central**: o próprio artigo (M4, Makridakis et al. 2020) argumenta que
modelos de ML overfitam com <50 observações **por série**. Testar um LSTM produto-a-
produto (26 obs) repetiria esse erro. A forma correta de dar a esses modelos uma chance
justa é treinar um **modelo global** (uma rede só, entrada com todas as séries do
Top-N produtos empilhadas, produto como variável categórica/embedding) — é assim que
os métodos de ML venceram a M4/M5 (ex. N-BEATS, DeepAR, ES-RNN), porque compartilham
dados entre séries em vez de ajustar 20 modelos com 26 pontos cada.

| Modelo | Papel na comparação |
| --- | --- |
| Naive sazonal / Holt-Winters (ETS) | Baseline clássico adicional (Hyndman & Athanasopoulos, já citado no artigo) |
| XGBoost/LightGBM | Árvore de decisão com lags + exógenas como features tabulares, por produto ou global |
| Prophet | Já era candidato descartado no ADR-001 — vale re-testar com o conjunto de exógenas ampliado |
| Rede neural global (ex. LSTM/GRU multi-série ou N-BEATS simplificado) | Único modelo de ML testado no formato correto para séries curtas |

- [ ] 4.1 Preparar dataset "long format" (produto × mês × exógenas) para os modelos
      globais (`training_scripts/alternative_models/`)
- [ ] 4.2 Treinar cada candidato (`training_scripts/alternative_models/`) com **os
      mesmos splits** de walk-forward CV das Fases 1 e 3 (`training_scripts/validation/`
      — crítico para comparação válida)
- [ ] 4.3 Mesmas métricas (MAE, RMSE, MAPE, SMAPE, R²) + tempo de treino/inferência
      (relevante para o requisito de retrain semanal < 2h, RNF-03)
- [ ] 4.4 Teste de significância pareado (mesmo método da Fase 3) contra o melhor
      SARIMAX (A1 ou B, o que vencer a Fase 3)
- [ ] 4.5 Relatório final `docs/prediction/comparacao_modelos_final.md`: tabela consolidada
      A0/A1/B/ETS/XGBoost/Prophet/NN-global, por produto e agregado
- [ ] 4.6 Atualizar `docs/prediction/ADR-001-sarimax_central_model.md` com uma seção
      "Revisão empírica" — mantém SARIMAX se ele ainda vencer, ou abre ADR-009
      propondo o modelo vencedor caso a evidência mude a decisão (a própria ADR-001 já
      previa essa porta: "Modelos de ML podem ser introduzidos no futuro mediante
      evidência de superioridade")

**Checkpoint**: decisão final e documentada sobre qual família de modelo vai para
produção — com números, não opinião.

---

## Fase 5 — Consolidação e integração ao produto

- [ ] 5.1 Só agora implementar `backend/domain/models/` e `backend/domain/features/`
      "para valer" (hoje são stubs vazios) — usando o pipeline vencedor da Fase 4,
      seguindo `tasks.md` Fase 3 (T030–T044)
- [ ] 5.2 Se o vencedor envolver dados externos, adicionar o job de atualização dessas
      bases ao `retrain_service.py`/scheduler semanal (Fase 3/T038-T040 do `tasks.md`)
- [ ] 5.3 Registrar os relatórios comparativos como artefato de suporte à seção 6.5 do
      artigo (dimensão "validação estatística") e à contribuição acadêmica — isso vira
      basicamente uma contribuição acadêmica (iii), além das duas já previstas em
      `SPECS.md` §12 (ponderação RF/MDI e granularidade mensal×diária)
- [ ] 5.4 Atualizar `SPECS.md` e a constituição (se o modelo vencedor não for SARIMAX
      puro) — mudança de princípio exige emenda MAJOR/MINOR conforme seção Governance

---

## Ordem de execução recomendada

Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5. Fases 1–4 rodam em `training_scripts/`
(rápido, descartável); só a Fase 5 mexe em código de produção — assim nenhuma variante
perdedora vira dívida técnica em `backend/`.
