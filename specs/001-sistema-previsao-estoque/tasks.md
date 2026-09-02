# Tasks: Sistema de Previsão de Estoque para Floricultura

**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [ADR-009](../../docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md)

**Escopo**: recomendação de **reposição diária** (revisão de 2026-08-30). Camadas
L1 (SARIMAX diário por `unidade × categoria`) → L2 (desagregação para SKU) → L3 (política
de reposição perecível-consciente).

**Sprint map**: Sprint 0 = Modelagem/UML/EDA (Mai–Jun/2026) · Sprint 1 = Fases 1+2
(Jun/2026) · Sprint 2 = Fases 3+4 (Jul/2026) · Sprint 3 = Fases 5+6+7 (Ago/2026) ·
Sprint 4 = Fases 8+9 (Set/2026) · Sprint 5 = testes integrados (Out/2026) · Sprint 6 =
documentação final (Nov/2026).

---

## Fase 0: Modelagem, EDA e Documentação Acadêmica

- [ ] T000a Produzir diagramas UML em `docs/uml/`: casos de uso, atividades, classes,
      modelo de dados (ER) e arquitetura lógica (seção 6.4 do artigo)
- [x] **T000b EDA** — dois momentos (CRISP-DM): compreensão dos dados (base transacional)
      + série modelável (9 pares L1). Scripts em `training_scripts/eda/` (`_common.py`,
      `eda_source.py`, `eda_series.py`, `run_all.py`), métricas em `results/metrics/eda_*.json`,
      11 figuras em `results/plots/eda/`, consolidado em
      [`docs/eda_report.md`](../../docs/eda_report.md) + dicionário de dados da fonte em
      [`docs/database/dicionario_dados_fonte.md`](../../docs/database/dicionario_dados_fonte.md).
      **Achados que ajustam o plano** (ver §4 do relatório): "fim de semana vende mais" é
      **falso** (pico ter–qui / sex; sáb fraco; dom fechado); `log1p` para os 9 pares;
      exógena de data comemorativa tem de ser por par (sinal se inverte entre `Grama` e
      `Plantas de corte`); `Plantas de corte` é quase ruído branco na parte ARIMA;
      tendências divergentes por loja (Jardim Canadá −37%/−49%/ano, Itabirito +96%/+29%);
      share de SKU instável → *fallback* da L2 é caminho principal. **Pendências para a
      parceira** em §5 do relatório.
- [x] ~~T000c Levantamento de `shelf_life_dias`~~ — **cancelado por
      [ADR-011](../../docs/prediction/ADR-011-escopo-previsao-sem-reposicao.md)**: a camada
      de reposição (L3) saiu de escopo, não há mais uso para validade por categoria.
- [x] **T000d Taxonomia** (Etapa 3 — `training_scripts/preprocessing/map_taxonomy.py` +
      `taxonomy/{unidades,categorias}.py`, ver `docs/prediction/01-pre_processing.md` §5).
      **Fechado com a parceira (2026-08-30 / ADR-011):** `empresa → unidade` = 3 lojas
      separadas; `categoria` L1 = **3 categorias de demanda** (`Grama` · `Plantas de corte`
      · `Produtos de jardim`) + `Servico e taxa`. `map_taxonomy.py` emite `categoria` +
      `categoria_fina`, reporta volume e cobertura ≥ 180 d (9 pares L1, todos ≥ 221 dias).
      **Resíduo (baixa prioridade):** curadoria fina de SKUs de alto volume em `Outros`
      (1,3%) — interessa à EDA/L2, não muda o L1.

**Checkpoint**: `docs/uml/` e `docs/eda_report.md` existem; `contas_a_receber_taxonomia.csv`
gerado (12 colunas), 9 pares L1 com ≥ 180 dias, % de volume em "Outros" aceitável ✅

---

## Fase 1: Setup e Infraestrutura Base

- [ ] T001 Criar estrutura `backend/` conforme `plan.md` (api/, schemas/, services/,
      domain/{etl,features,models,disaggregation,replenishment}, infrastructure/)
- [ ] T002 [P] `backend/config.py` — `Settings` via pydantic-settings: `TOP_N_PRODUCTS`,
      `FORECAST_HORIZON_DAYS=14`, `TEST_DAYS=28`, `MIN_OBSERVATIONS_DAYS=180`,
      `SEASONAL_PERIOD=7`, `SAFETY_STOCK_DAYS=2`, `SHELF_LIFE_DEFAULT_DAYS=7`,
      `LOG_CV_THRESHOLD=0.7`, `RETRAIN_DAY_OF_WEEK=mon`, `RETRAIN_HOUR=2`, `DAILY_FORECAST_HOUR=3`
- [ ] T003 [P] `requirements.txt` (FastAPI, statsmodels, scikit-learn, SQLAlchemy,
      APScheduler, joblib, openpyxl, reportlab, python-jose, passlib) e
      `requirements-dev.txt` (jupyter, matplotlib, seaborn, plotly, statsforecast)
- [ ] T004 `backend/infrastructure/database/engine.py` — engine SQLite + session factory
- [ ] T005 `backend/infrastructure/database/models.py` — ORM: `products` (+`categoria`,
      `unidade`), `categories` (`shelf_life_dias`, status, métricas L1), `model_artifacts`,
      `forecasts_cache`, `replenishment_cache`, `processing_log`, `retrain_history`, `users`
- [ ] T006 `backend/infrastructure/database/migrations.py` — `create_tables()` idempotente
- [ ] T007 `backend/main.py` — app FastAPI com CORS, routers, `startup` chamando
      `create_tables()` + `start_weekly_retrain()` + `start_daily_generation()`
- [ ] T008 [P] `backend/api/router_health.py` — `GET /health`
- [ ] T009 [P] `.env.example` com todas as variáveis documentadas
- [ ] T010 [P] `tests/fixtures/sample.xlsx` e `sample_data.csv` (dados mínimos, várias
      datas e categorias para exercitar a série diária)

**Checkpoint**: `uvicorn backend.main:app --reload` → `GET /health` retorna `{"status": "ok"}` ✅

---

## Fase 2: Autenticação e Autorização (US4)

Concluir antes de qualquer outro endpoint `/api/v1/*`.

- [ ] T011 [P] [US4] `tests/unit/test_auth.py` — `hash_password`/`verify_password`
- [ ] T012 [P] [US4] `tests/unit/test_jwt.py` — `create_access_token`/`decode_token`; expiração
- [ ] T013 [US4] `tests/integration/test_auth_endpoints.py` — login ok/401; `/api/v1/*` sem
      token → 401; token viewer em `/api/v1/upload` → 403
- [ ] T014 [P] [US4] `backend/auth/password_handler.py` — passlib/bcrypt
- [ ] T015 [P] [US4] `backend/auth/jwt_handler.py` — python-jose
- [ ] T016 [US4] `backend/auth/dependencies.py` — `get_current_user()`, `require_admin()`
- [ ] T017 [US4] `backend/auth/seed_users.py` — cria admin/viewer do `.env` (idempotente)
- [ ] T018 [US4] `backend/schemas/auth.py` — `LoginRequest`, `TokenResponse`, `UserOut`
- [ ] T019 [US4] `backend/api/router_auth.py` — `/auth/login`, `/auth/refresh`, `/auth/me`;
      aplicar `get_current_user` em todos os routers `/api/v1/*`
- [ ] T020 [US4] Aplicar `require_admin` em `POST /api/v1/upload` e `POST /api/v1/models/retrain`
- [ ] T021 [US4] Integrar `seed_users.py` no startup do `main.py`
- [ ] T022 [P] [US4] `app-react/src/app/auth/AuthContext.tsx` — token/user/role em localStorage
- [ ] T023 [P] [US4] `app-react/src/app/auth/LoginPage.tsx` — form email+senha
- [ ] T024 [US4] `app-react/src/app/auth/PrivateRoute.tsx` — redireciona; prop `requiredRole`
- [ ] T025 [US4] Interceptor fetch — injeta `Authorization: Bearer`; 401 → `/login`

**Checkpoint**: login retorna JWT; upload com token viewer → 403; tela de login no React ✅

---

## Fase 3: ETL Pipeline (US1 — Upload de Planilha)

- [ ] T026 [P] [US1] `tests/unit/test_parser.py` — `parse_xlsx(fixture)`; linhas corrompidas em `skipped`
- [ ] T027 [P] [US1] `tests/unit/test_normalizer.py` — qtdade ≤ 0 removida; emissao nula; vírgula decimal
- [ ] T028 [P] [US1] `tests/unit/test_deduplicator.py` — dedup por
      `(doc_numero, produto_cod, emissao, qtdade, vl_total)` só entre arquivos
- [ ] T029 [US1] `tests/integration/test_etl_pipeline.py` — `process_upload(fixture.xlsx)`
      atualiza CSV e grava `processing_log`
- [ ] T030 [P] [US1] `backend/domain/etl/parser.py` — `parse_xlsx()` → `(records, skipped)`
- [ ] T031 [P] [US1] `backend/domain/etl/normalizer.py` — `normalize_records()` → DataFrame
      tipado; deriva `categoria` e `unidade` do produto/empresa
- [ ] T032 [P] [US1] `backend/domain/etl/deduplicator.py` — `deduplicate(df_new, csv, key_fields)`
- [ ] T033 [US1] `backend/infrastructure/storage/file_manager.py` — `append_to_csv()`,
      `load_csv()`, `log_processing()`
- [ ] T034 [US1] `backend/services/upload_service.py` — parse → normalize → dedup → append →
      log → agenda reajuste
- [ ] T035 [US1] `backend/schemas/upload.py` — `UploadResponse`
- [ ] T036 [US1] `backend/api/router_upload.py` — `POST /api/v1/upload` [admin]; valida
      extensão e tamanho

**Checkpoint**: upload com token admin → CSV atualizado + `processing_log` gravado ✅

---

## Fase 4: L1 — SARIMAX Diário por `unidade × categoria` (US2)

### Testes (escrever ANTES)

- [ ] T037 [P] [US2] `tests/unit/test_daily_series.py` — `prepare_daily_series(df, unidade,
      categoria)`: reindex diário completo, dias sem venda = 0; `ValueError` com < 180 dias
- [ ] T038 [P] [US2] `tests/unit/test_calendar_exogenous.py` — dummies de dia-da-semana;
      flag de feriado; "dias até Dia das Mães" correto; alinhamento de índice
- [ ] T039 [P] [US2] `tests/unit/test_importance.py` — importâncias somam 1; `weight_features` clip(0.1)
- [ ] T040 [P] [US2] `tests/unit/test_stationarity.py` — `suggest_d` retorna 0 para série estacionária
- [ ] T041 [P] [US2] `tests/unit/test_order_selection.py` — grid m=7; tupla válida; tolera falhas
- [ ] T042 [P] [US2] `tests/unit/test_evaluator.py` — `mase()`, `rmsse()`, cobertura do IC
      com arrays conhecidos; `walk_forward_cv(n_splits=2, horizon=14)` retorna DataFrame
- [ ] T043 [P] [US2] `tests/unit/test_forecaster.py` — `generate_daily_forecast` retorna 14
      pontos com datas corretas; back-transform `expm1` se `use_log`
- [ ] T044 [US2] `tests/integration/test_l1_pipeline.py` — `run_category_pipeline(df, unidade,
      categoria)` retorna `CategoryPipelineResult` com todas as chaves

### Implementação — Features

- [ ] T045 [P] [US2] `backend/domain/features/daily_series.py` — `prepare_daily_series()` → `pd.Series` freq='D'
- [ ] T046 [P] [US2] `backend/domain/features/calendar_exogenous.py` — dia-da-semana
      (dummies/Fourier), feriado nacional (BrasilAPI/curadoria), véspera, "dias até data
      comemorativa" (Mães, Namorados, Finados, Natal)
- [ ] T047 [P] [US2] `backend/domain/features/importance.py` — `compute_rf_importance()`, `weight_features()`

### Implementação — Modelagem L1

- [ ] T048 [P] [US2] `backend/domain/models/stationarity.py` — ADF+KPSS; `suggest_d(max_d=1)`
- [ ] T049 [P] [US2] `backend/domain/models/order_selection.py` — grid p,q∈0..2; P,Q∈0..1;
      D=0; m=7; critério AIC
- [ ] T050 [US2] `backend/domain/models/sarimax_trainer.py` — `fit_sarimax()`,
      `run_category_pipeline()` → `CategoryPipelineResult` dataclass
- [ ] T051 [US2] `backend/domain/models/evaluator.py` — `mase()`, `rmsse()`, `ic_coverage()`,
      `walk_forward_cv(n_splits=4, horizon=14, origem móvel)`, `residual_tests()` (Ljung-Box + Shapiro-Wilk)
- [ ] T052 [US2] `backend/domain/models/forecaster.py` — `generate_daily_forecast()`
      extrapolando exógenas de calendário (determinísticas); IC 95%; back-transform log

### Model Registry + Reajuste semanal

- [ ] T053 [US2] `backend/infrastructure/storage/model_registry.py` — `save_artifact()`,
      `load_artifact()`, `get_status()`, `list_trained_categories()`
- [ ] T054 [US2] `backend/services/retrain_service.py` — `run_full_retrain(trigger)`: itera
      `unidade × categoria`, `run_category_pipeline()`, persiste, grava `retrain_history`
- [ ] T055 [US2] `backend/infrastructure/scheduler/weekly_retrain.py` — APScheduler
      `CronTrigger(day_of_week="mon", hour=2)`

**Checkpoint**: reajuste gera artefatos L1 por `unidade × categoria` com MASE/RMSSE/cobertura no banco ✅

---

## Fase 5: L2 + L3 — Desagregação e Política de Reposição (US2 + US3)

### Testes

- [ ] T056 [P] [US2] `tests/unit/test_sku_split.py` — share móvel soma 1 na categoria;
      perfil de dia-da-semana aplicado; SKU de baixo giro cai no rateio uniforme
- [ ] T057 [P] [US3] `tests/unit/test_replenishment_policy.py` — `qty_to_order` = 0 quando
      estoque cobre a demanda; cobertura limitada por `shelf_life_dias`; `expected_waste`
      cresce quando validade < horizonte
- [ ] T058 [P] [US3] `tests/unit/test_replenishment_simulation.py` — simulação de perda +
      ruptura sobre série sintética; política bate a regra ingênua de 7 dias
- [ ] T059 [US3] `tests/integration/test_replenishment_pipeline.py` — categoria treinada →
      previsão por SKU → recomendação por SKU/dia com todos os campos

### Implementação

- [ ] T060 [US2] `backend/domain/disaggregation/sku_split.py` — `disaggregate(previsao_cat,
      df_hist, produto_cod)`: share móvel (4–8 semanas) × perfil de dia-da-semana; fallback uniforme
- [ ] T061 [US3] `backend/domain/replenishment/policy.py` — `recommend(previsao_sku,
      shelf_life_dias, safety_stock_days, estoque_atual=0)` → qty, cover_until,
      reorder_in_days, expected_waste, stockout_risk
- [ ] T062 [US3] `backend/domain/replenishment/simulation.py` — `simulate_policy(hold_out,
      policy)` vs. `naive_7d` → perda + ruptura; usado como quality gate no `evaluator`
- [ ] T063 [US2] `backend/services/forecast_service.py` — `get_forecast(produto_cod)`:
      carrega modelo L1 da categoria, `generate_daily_forecast()`, aplica L2, popula `forecasts_cache`
- [ ] T064 [US3] `backend/services/replenishment_service.py` — `get_replenishment(produto_cod)`:
      consome previsão L2, aplica L3, popula `replenishment_cache`
- [ ] T065 [US2/US3] `backend/infrastructure/scheduler/daily_generation.py` — APScheduler
      `CronTrigger(hour=3)`: para cada SKU do Top-N roda L2+L3 a partir do modelo L1 em cache;
      registra data e contagem de SKUs
- [ ] T066 [US2] `backend/schemas/forecast.py` — `DailyPoint`, `ForecastResponse`
- [ ] T067 [US3] `backend/schemas/replenishment.py` — `ReplenishmentDay`,
      `ReplenishmentRecommendation`, `ReplenishmentBatchResponse`
- [ ] T068 [US2] `backend/api/router_products.py` — `GET /api/v1/products[/{id}]` (histórico diário)
- [ ] T069 [US2] `backend/api/router_forecast.py` — `GET /api/v1/forecast/{id}?horizon_days=14`
      e `GET /api/v1/forecast/batch`
- [ ] T070 [US3] `backend/api/router_replenishment.py` — `GET /api/v1/replenishment/{id}`
      e `GET /api/v1/replenishment/batch`

**Checkpoint**: `GET /api/v1/replenishment/147` retorna qty por dia, cobre-até, cadência e
selo de risco ✅

### Comparação acadêmica (ii)

- [ ] T070a Trilha de comparação em `training_scripts/alternative_models/`: Croston/TSB/SBA
      por SKU **×** SARIMAX hierárquico (L1+L2), **mesmos splits** de walk-forward
      (origem móvel, h=14); MASE/RMSSE lado a lado; relatório em
      `docs/prediction/comparacao_hierarquico_vs_intermitente.md`

---

## Fase 6: Alertas (US3 — complemento)

- [ ] T071 [P] [US3] `tests/unit/test_alert_service.py` — severity=high se previsão 7d > 30%
      acima da média 4 semanas; medium se 20–30%; flag de risco de sobra para validade curta
- [ ] T072 [US3] `tests/integration` — `GET /api/v1/alerts` retorna lista ordenada após geração diária
- [ ] T073 [US3] `backend/services/alert_service.py` — variação previsão 7d vs. média 4
      semanas; classifica severity; marca `risco_sobra` quando `shelf_life_dias` curto e
      previsão em queda; justificativa PT-BR
- [ ] T074 [US3] `backend/schemas/alert.py` — `AlertItem`, `AlertListResponse`
- [ ] T075 [US3] `backend/api/router_alerts.py` — `GET /api/v1/alerts?limit=50&severity=all`

**Checkpoint**: após geração diária, `GET /api/v1/alerts` retorna ≥ 1 alerta para a fixture ✅

---

## Fase 7: Models Status + Retrain Manual + Exportação

- [ ] T076 [US3] `backend/schemas/model_status.py` — `ModelStatusResponse` (contagem por
      status de `unidade × categoria`, último reajuste, última geração diária)
- [ ] T077 [US3] `backend/api/router_models.py` — `GET /api/v1/models/status` e
      `POST /api/v1/models/retrain` [admin] (409 se já rodando)
- [ ] T078 [US5] `tests/integration` — export `?format=excel` com abas "Reposição",
      "Previsão diária", "Métricas", "Alertas"; `?format=pdf` válido
- [ ] T079 [US5] `backend/services/report_service.py` — `generate_excel()` (openpyxl, 4
      abas), `generate_pdf()` (reportlab)
- [ ] T080 [US5] `backend/schemas/report.py` + `backend/api/router_reports.py` —
      `GET /api/v1/reports/export?format=excel|pdf&top_n=10&horizon_days=14`

**Checkpoint**: `GET /api/v1/models/status` mostra data do último reajuste e da última
geração diária; download de PDF com reposição preenchida ✅

---

## Fase 8: Simulação (US5)

- [ ] T081 [P] [US5] `tests/unit/test_simulation_service.py` — sem cenário → previsão base;
      desconto 0% → delta 0; desconto 15% → delta > 0; reposição recalculada
- [ ] T082 [US5] `backend/services/simulation_service.py` — multiplicador sobre a previsão
      diária base (desconto via coeficiente de preço/desconto do modelo L1; bundle via
      `expected_uplift_pct`); repassa para L3
- [ ] T083 [US5] `backend/schemas/simulation.py` + `backend/api/router_simulation.py` —
      `POST /api/v1/simulation`

**Checkpoint**: `POST /api/v1/simulation` com desconto 15% → previsão simulada > base e
reposição ajustada ✅

---

## Fase 9: Frontend React + Integração (US1–US5)

- [ ] T084 Gerar `ia-predictor/openapi.yaml` completo (15 endpoints, schemas `DailyPoint`,
      `ReplenishmentRecommendation`)
- [ ] T085 [P] `app-react/src/services/api/` — regenerar cliente (`npm run generate:api`)
- [ ] T086 [P] [US1] `components/UploadPanel.tsx` — upload com feedback (role=admin)
- [ ] T087 [P] [US2] `components/ForecastChart.tsx` — Recharts: histórico + previsão **diária**
      + IC 95% + marcação de fim de semana / feriado / data comemorativa
- [ ] T088 [P] [US3] `components/ReplenishmentTable.tsx` — por produto: qty sugerida,
      "cobre até", cadência, selo de risco (perda / ruptura / ok)
- [ ] T089 [P] [US2] `pages/ProductDetail.tsx` — histórico diário + `ForecastChart` + métricas simples
- [ ] T090 [P] [US3] `pages/Replenishment.tsx` — "Reposição de Hoje": lista dos top N com `ReplenishmentTable`
- [ ] T091 [P] [US3] `pages/Alerts.tsx` — alertas com severidade visual e justificativa
- [ ] T092 [P] [US5] `pages/Simulation.tsx` — cenário + gráfico base vs. simulado + reposição
- [ ] T093 [P] [US5] `components/ExportButton.tsx` — seleção PDF/Excel
- [ ] T094 Integrar tudo no `Dashboard.tsx` com react-router
- [ ] T095 Teste manual — upload → reajuste → previsão diária → reposição do dia → alerta → exportar PDF

**Checkpoint**: fluxo completo funcional no navegador sem erros de console ✅

---

## Fase 10: Polimento e Qualidade

- [ ] T096 [P] Atualizar `CLAUDE.md` e `docs/quickstart.md` (a criar)
- [ ] T097 [P] `pytest tests/unit/ -v` e `pytest tests/integration/ -v` — corrigir falhas
- [ ] T098 Validação estatística formal: **MASE < 1.0** nas `unidade × categoria` de maior
      volume; cobertura do IC ∈ [90%, 98%]
- [ ] T099 Simulação de reposição vs. regra ingênua de 7 dias para os top 10 produtos —
      registrar redução de perda + ruptura (SC-003)
- [ ] T100 Ljung-Box + Shapiro-Wilk nos resíduos de todos os modelos L1 — logar
- [ ] T101 Validação com usuários da entidade parceira — percurso guiado dos User Stories
- [ ] T102 Commit final: `feat: sistema de reposição diária v1.0.0`

---

## Dependências e Ordem de Execução

- **Fase 0**: sem dependência de código — paralela à Fase 1
- **Fase 1**: começa imediatamente
- **Fase 2**: depende da Fase 1 — bloqueia Fases 3–9
- **Fase 3** (ETL): depende da Fase 2 — bloqueia Fases 4+
- **Fase 4** (L1): depende da Fase 3 — bloqueia Fase 5
- **Fase 5** (L2+L3): depende da Fase 4 — bloqueia Fases 6–8
- **Fase 6** (Alertas), **Fase 7** (Status/Export), **Fase 8** (Simulação): dependem da Fase 5, paralelas entre si
- **Fase 9** (Frontend): depende das Fases 3–8
- **Fase 10** (Polimento): depende da Fase 9

### Estratégia MVP

1. Fases 1 → 2 → 3 → 4 → 5 (T001–T070)
2. **MVP**: `POST /upload` + `GET /replenishment/{id}` funcionando = core do sistema
3. Fase 6 (alertas) → Fase 7 (status/export) → Fase 8 (simulação)
4. Fase 9 (frontend) sobre API estável

---

## Notas

- `[P]` = tarefa independente, paralelizável com outras `[P]` da mesma fase
- `[US#]` = rastreabilidade para User Story
- Testes DEVEM falhar antes da implementação (TDD)
- Commit após cada Checkpoint validado
- Não avançar de fase com Checkpoint falho
