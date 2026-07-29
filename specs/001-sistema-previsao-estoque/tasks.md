# Tasks: Sistema de Previsão de Estoque para Floricultura

**Input**: [spec.md](spec.md) · [plan.md](plan.md)

**Sprint map**: Sprint 1 = Fase 1+2 (Jun/2026) · Sprint 2 = Fase 3+4 (Jul/2026) · Sprint 3 = Fase 5+6 (Ago/2026) · Sprint 4 = Fase 7+8 (Set/2026)

---

## Fase 1: Setup e Infraestrutura Base

**Objetivo**: Projeto inicializado, banco criado, FastAPI respondendo, sem lógica de negócio ainda.

- [ ] T001 Criar estrutura de diretórios `backend/` conforme `plan.md` (api/, schemas/, services/, domain/, infrastructure/)
- [ ] T002 [P] Criar `backend/config.py` com `Settings` via pydantic-settings lendo `.env`
- [ ] T003 [P] Criar `requirements.txt` com todas as dependências do backend (FastAPI, statsmodels, scikit-learn, SQLAlchemy, APScheduler, joblib, openpyxl, reportlab)
- [ ] T004 Criar `backend/infrastructure/database/engine.py` — engine SQLite + session factory
- [ ] T005 Criar `backend/infrastructure/database/models.py` — ORM: `products`, `model_artifacts`, `forecasts_cache`, `processing_log`, `retrain_history`, **`users`** (id, email, name, hashed_password, role, is_active)
- [ ] T006 Criar `backend/infrastructure/database/migrations.py` — `create_tables()` idempotente
- [ ] T007 Criar `backend/main.py` — app FastAPI com CORS, routers incluídos e `startup` chamando `create_tables()` + `start_scheduler()`
- [ ] T008 [P] Criar `backend/api/router_health.py` — `GET /health` retorna status + versão
- [ ] T009 [P] Criar `.env.example` com todas as variáveis de configuração documentadas
- [ ] T010 [P] Criar `tests/fixtures/sample.xlsx` e `tests/fixtures/sample_data.csv` com dados mínimos para testes

**Checkpoint**: `uvicorn backend.main:app --reload` → `GET /health` retorna `{"status": "ok"}` ✅

---

## Fase 2: Autenticação e Autorização (User Story 4 — Controle de Acesso)

**Objetivo**: JWT funcionando, perfis admin/viewer aplicados, login no React.
Esta fase DEVE ser concluída antes de qualquer outro endpoint `/api/v1/*`.

### Testes de Autenticação (escrever ANTES da implementação)

- [ ] T011 [P] [US4] `tests/unit/test_auth.py` — `hash_password` + `verify_password` corretos; senha errada retorna False
- [ ] T012 [P] [US4] `tests/unit/test_jwt.py` — `create_access_token` gera token válido; `decode_token` extrai role; token expirado levanta exceção
- [ ] T013 [US4] `tests/integration/test_auth_endpoints.py` — `POST /auth/login` com credenciais válidas retorna tokens; com senha errada retorna 401; endpoint `/api/v1/products` sem token retorna 401; com token viewer retorna 200; `POST /api/v1/upload` com token viewer retorna 403

### Implementação de Autenticação

- [ ] T014 [P] [US4] Criar `backend/auth/password_handler.py` — `hash_password(plain)` e `verify_password(plain, hashed)` usando passlib/bcrypt
- [ ] T015 [P] [US4] Criar `backend/auth/jwt_handler.py` — `create_access_token(data, expires_delta)`, `create_refresh_token(data)`, `decode_token(token)` usando python-jose
- [ ] T016 [US4] Criar `backend/auth/dependencies.py` — `get_current_user(token)` FastAPI dependency; `require_admin(user)` levanta 403 se `user.role != "admin"`
- [ ] T017 [US4] Adicionar tabela `users` ao `backend/infrastructure/database/models.py` (id, email, name, hashed_password, role, is_active)
- [ ] T018 [US4] Criar `backend/auth/seed_users.py` — script que lê `ADMIN_EMAIL/PASSWORD` e `VIEWER_EMAIL/PASSWORD` do `.env` e cria usuários iniciais com hash bcrypt (idempotente)
- [ ] T019 [US4] Criar `backend/schemas/auth.py` — `LoginRequest`, `TokenResponse(access_token, refresh_token, role, expires_in)`, `UserOut(id, email, name, role)`
- [ ] T020 [US4] Criar `backend/api/router_auth.py` — `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`; aplicar `get_current_user` dependency em todos os `/api/v1/*` routers
- [ ] T021 [US4] Aplicar `require_admin` nos endpoints protegidos: `POST /api/v1/upload`, `POST /api/v1/models/retrain`
- [ ] T022 [US4] Integrar `seed_users.py` no startup do `backend/main.py` (roda antes do scheduler)

### Frontend — Login e Rotas Protegidas

- [ ] T023 [P] [US4] Criar `app-react/src/app/auth/AuthContext.tsx` — React Context com `token`, `user`, `role`; persiste token em `localStorage`; expõe `login()` e `logout()`
- [ ] T024 [P] [US4] Criar `app-react/src/app/auth/LoginPage.tsx` — formulário email + senha com react-hook-form; chama `AuthApi.login()`; redireciona para Dashboard após sucesso
- [ ] T025 [US4] Criar `app-react/src/app/auth/PrivateRoute.tsx` — wrapper que redireciona para `/login` se não autenticado; aceita prop `requiredRole` para restringir por perfil
- [ ] T026 [US4] Configurar axios/fetch com interceptor que injeta `Authorization: Bearer <token>` em todas as requisições e redireciona para `/login` em respostas 401

**Checkpoint**: `POST /auth/login` retorna JWT; `POST /api/v1/upload` com token viewer retorna 403; tela de login funcional no React ✅

---

## Fase 4: ETL Pipeline (User Story 1 — Upload de Planilha)

**Objetivo**: Upload de XLSX funcional com deduplicação e log de processamento.

### Testes ETL (escrever ANTES da implementação)

- [ ] T027 [P] [US1] Teste unitário `tests/unit/test_parser.py` — `parse_xlsx(fixture)` retorna records com 19 campos; linhas corrompidas vão para `skipped`
- [ ] T028 [P] [US1] Teste unitário `tests/unit/test_normalizer.py` — qtdade ≤ 0 removida; emissao nula removida; vírgula decimal convertida
- [ ] T029 [P] [US1] Teste unitário `tests/unit/test_deduplicator.py` — registro com mesma `(doc_numero, produto_cod)` não duplica no CSV
- [ ] T030 [US1] Teste de integração `tests/integration/test_etl_pipeline.py` — `upload_service.process_upload(fixture.xlsx)` atualiza CSV e grava `processing_log`

### Implementação ETL

- [ ] T031 [P] [US1] Criar `backend/domain/etl/parser.py` — migrar e refatorar `parse_xlsx()` do código existente; retorna `(records, skipped)`
- [ ] T032 [P] [US1] Criar `backend/domain/etl/normalizer.py` — `normalize_records(records)` → DataFrame com dtypes corretos
- [ ] T033 [P] [US1] Criar `backend/domain/etl/deduplicator.py` — `deduplicate(df_new, csv_path, key_fields)` → DataFrame só com registros novos
- [ ] T034 [US1] Criar `backend/infrastructure/storage/file_manager.py` — `append_to_csv()`, `load_csv()`, `log_processing()`
- [ ] T035 [US1] Criar `backend/services/upload_service.py` — orquestra parse → normalize → dedup → append → log → agenda retrain
- [ ] T036 [US1] Criar `backend/schemas/upload.py` — `UploadResponse` Pydantic
- [ ] T037 [US1] Criar `backend/api/router_upload.py` — `POST /api/v1/upload` com `require_admin`; multipart/form-data; valida extensão e tamanho; retorna `UploadResponse`

**Checkpoint**: Upload de XLSX com token admin via `/api/v1/upload` → CSV atualizado + `processing_log` gravado no banco ✅

---

## Fase 3: Feature Engineering + SARIMAX (User Story 2 — Previsão por Produto)

**Objetivo**: Modelos treinados e persistidos; endpoint de previsão funcional.

### Testes (escrever ANTES da implementação)

- [ ] T022 [P] [US2] Teste unitário `tests/unit/test_time_series.py` — meses ausentes preenchidos com 0; `ValueError` com < 15 obs
- [ ] T023 [P] [US2] Teste unitário `tests/unit/test_exogenous.py` — DataFrame com exatamente 15 colunas; `alta_temporada=1` em maio; alinhamento de índices
- [ ] T024 [P] [US2] Teste unitário `tests/unit/test_importance.py` — importâncias somam 1.0; `weight_features` respeita `clip(lower=0.1)`
- [ ] T025 [P] [US2] Teste unitário `tests/unit/test_stationarity.py` — `suggest_d` retorna 0 para série já estacionária
- [ ] T026 [P] [US2] Teste unitário `tests/unit/test_order_selection.py` — retorna tupla válida; não lança exceção quando combinações individuais falham
- [ ] T027 [P] [US2] Teste unitário `tests/unit/test_evaluator.py` — métricas corretas com arrays conhecidos; `walk_forward_cv` com 2 folds retorna DataFrame
- [ ] T028 [P] [US2] Teste unitário `tests/unit/test_forecaster.py` — `ForecastResult` tem N=horizon datas corretas; back-transform `expm1` aplicado quando `use_log=True`
- [ ] T029 [US2] Teste de integração `tests/integration/test_sarimax_pipeline.py` — `run_product_pipeline(df, produto_cod)` com fixture retorna `ProductPipelineResult` com todas as chaves

### Implementação — Feature Engineering

- [ ] T030 [P] [US2] Criar `backend/domain/features/time_series.py` — `prepare_monthly_series(df, produto_cod)` → `pd.Series` com freq='MS'; preenche meses ausentes com 0
- [ ] T031 [P] [US2] Criar `backend/domain/features/exogenous.py` — `build_exogenous_features(df, produto_cod)` → DataFrame com 15 variáveis (mercado + produto + calendário)
- [ ] T032 [P] [US2] Criar `backend/domain/features/importance.py` — `compute_rf_importance(X, y, n_estimators=200)` e `weight_features(X, importances, clip=0.1)`

### Implementação — Modelagem SARIMAX

- [ ] T033 [P] [US2] Criar `backend/domain/models/stationarity.py` — `check_stationarity(ts)` com ADF+KPSS; `suggest_d(ts, max_d=1)`
- [ ] T034 [P] [US2] Criar `backend/domain/models/order_selection.py` — `select_sarimax_order()` grid 36 combinações; D=0; m=12; critério AIC
- [ ] T035 [US2] Criar `backend/domain/models/sarimax_trainer.py` — `fit_sarimax()` e `run_product_pipeline()` retornando `ProductPipelineResult` dataclass
- [ ] T036 [US2] Criar `backend/domain/models/evaluator.py` — `evaluate_model()`, `walk_forward_cv(n_splits=4)`, `residual_tests()` (Ljung-Box + Shapiro-Wilk)
- [ ] T037 [US2] Criar `backend/domain/models/forecaster.py` — `generate_forecast()` extrapolando exógenas futuras; back-transform log; retorna `ForecastResult`

### Implementação — Model Registry + Retrain

- [ ] T038 [US2] Criar `backend/infrastructure/storage/model_registry.py` — `save_artifact()`, `load_artifact()`, `get_status()`, `list_trained_products()`
- [ ] T039 [US2] Criar `backend/services/retrain_service.py` — `run_full_retrain(trigger)`: carrega CSV, seleciona top_N, itera `run_product_pipeline()`, persiste, grava `retrain_history`
- [ ] T040 [US2] Criar `backend/infrastructure/scheduler/weekly_retrain.py` — APScheduler com `CronTrigger(day_of_week="mon", hour=2)`; integrar em `main.py startup`

### Implementação — Endpoints de Produto e Previsão

- [ ] T041 [US2] Criar `backend/services/forecast_service.py` — `get_forecast(produto_cod, horizon)`: carrega artefato, chama `generate_forecast()`, popula cache
- [ ] T042 [US2] Criar `backend/schemas/product.py` e `backend/schemas/forecast.py` — Pydantic models completos com todos os campos de resposta
- [ ] T043 [US2] Criar `backend/api/router_products.py` — `GET /api/v1/products` (paginado, filtro, sort) e `GET /api/v1/products/{id}` (histórico + métricas)
- [ ] T044 [US2] Criar `backend/api/router_forecast.py` — `GET /api/v1/forecast/{produto_cod}?horizon_months=3` e `GET /api/v1/forecast/batch?top_n=10`

**Checkpoint**: `GET /api/v1/forecast/147?horizon_months=3` retorna JSON com datas, previsões e IC 95% ✅

---

## Fase 4: Alertas (User Story 3 — Alerta Automático de Reposição)

**Objetivo**: Lista de alertas gerada automaticamente após cada retrain.

### Testes

- [ ] T045 [P] [US3] Teste unitário `tests/unit/test_alert_service.py` — severity=high se variação > 30%; medium se 20–30%; nenhum alerta se < 20%
- [ ] T046 [US3] Teste de integração — `GET /api/v1/alerts` retorna lista ordenada por variação após retrain com dados da fixture

### Implementação

- [ ] T047 [US3] Criar `backend/services/alert_service.py` — calcula variação da previsão próximo mês vs. média 3m; classifica severity; retorna `AlertItem`
- [ ] T048 [US3] Criar `backend/schemas/alert.py` — `AlertItem` e `AlertListResponse` Pydantic
- [ ] T049 [US3] Criar `backend/api/router_alerts.py` — `GET /api/v1/alerts?limit=50&severity=all`

**Checkpoint**: Após retrain, `GET /api/v1/alerts` retorna lista com pelo menos 1 alerta para dados de teste ✅

---

## Fase 5: Models Status + Retrain Manual (User Story 3 — complemento)

**Objetivo**: Gestora pode ver status do retrain e disparar manualmente se necessário.

- [ ] T050 [US3] Criar `backend/schemas/model_status.py` — `ModelStatusResponse` Pydantic
- [ ] T051 [US3] Criar `backend/api/router_models.py` — `GET /api/v1/models/status` (último retrain, próximo, progresso) e `POST /api/v1/models/retrain` (disparo manual assíncrono; 409 se já rodando)

**Checkpoint**: `GET /api/v1/models/status` mostra data do último retrain e status `is_training` correto ✅

---

## Fase 6: Simulação (User Story 4 — Simulação de Promoção)

**Objetivo**: Endpoint de simulação de cenários de desconto e venda casada.

### Testes

- [ ] T052 [P] [US4] Teste unitário `tests/unit/test_simulation_service.py` — sem cenário retorna previsão base; desconto 0% retorna delta=0; desconto 15% retorna delta > 0

### Implementação

- [ ] T053 [US4] Criar `backend/services/simulation_service.py` — aplica multiplicador sobre previsão base: desconto usa coeficiente `prod_taxa_desconto` do modelo; bundle usa `expected_uplift_pct` diretamente
- [ ] T054 [US4] Criar `backend/schemas/simulation.py` — `SimulationRequest` e `SimulationResponse` Pydantic
- [ ] T055 [US4] Criar `backend/api/router_simulation.py` — `POST /api/v1/simulation`

**Checkpoint**: `POST /api/v1/simulation` com desconto 15% retorna previsão simulada > previsão base ✅

---

## Fase 7: Exportação (User Story 5 — Relatório PDF e Excel)

**Objetivo**: Exportação de relatórios para reuniões de planejamento.

### Testes

- [ ] T056 [US5] Teste de integração — `GET /api/v1/reports/export?format=excel` retorna arquivo .xlsx com abas "Previsões", "Métricas", "Alertas"
- [ ] T057 [US5] Teste de integração — `GET /api/v1/reports/export?format=pdf` retorna arquivo .pdf com conteúdo válido

### Implementação

- [ ] T058 [US5] Criar `backend/services/report_service.py` — `generate_excel(top_n, horizon)` com openpyxl (3 abas); `generate_pdf(top_n, horizon)` com reportlab
- [ ] T059 [US5] Criar `backend/schemas/report.py` — parâmetros de query validados
- [ ] T060 [US5] Criar `backend/api/router_reports.py` — `GET /api/v1/reports/export?format=excel|pdf&top_n=10&horizon_months=3`; response com `Content-Disposition: attachment`

**Checkpoint**: Download de PDF via browser com previsões e alertas preenchidos ✅

---

## Fase 8: Frontend React + Integração (User Stories 1–5)

**Objetivo**: Dashboard React consumindo a API; todos os fluxos funcionais no navegador.

- [ ] T061 Gerar `ia-predictor/openapi.yaml` completo com todos os endpoints (OpenAPI 3.0)
- [ ] T062 [P] Criar `app-react/src/app/services/api.ts` — cliente HTTP tipado consumindo a API (baseURL configurável via env)
- [ ] T063 [P] [US1] Criar `app-react/src/app/components/UploadPanel.tsx` — formulário de upload com feedback de progresso e resultado
- [ ] T064 [P] [US2] Criar `app-react/src/app/components/ForecastChart.tsx` — gráfico Recharts com histórico + previsão + faixa IC 95% + marcação de alta temporada
- [ ] T065 [P] [US2] Criar `app-react/src/app/pages/ProductDetail.tsx` — busca produto, exibe histórico + `ForecastChart` + métricas em linguagem simples
- [ ] T066 [P] [US3] Criar `app-react/src/app/pages/Alerts.tsx` — lista de alertas com severidade visual (vermelho/amarelo) e justificativa
- [ ] T067 [P] [US3] Criar `app-react/src/app/components/ModelStatusBadge.tsx` — indicador de status e data do último retrain
- [ ] T068 [P] [US4] Criar `app-react/src/app/pages/Simulation.tsx` — formulário de cenário + gráfico comparativo base vs. simulado
- [ ] T069 [P] [US5] Criar `app-react/src/app/components/ExportButton.tsx` — botão de exportação com seleção de formato (PDF/Excel)
- [ ] T070 Integrar todos os componentes no `Dashboard.tsx` principal com navegação via react-router
- [ ] T071 Teste de integração manual — percorrer fluxo completo: upload → retrain → ver previsão → ver alerta → exportar PDF

**Checkpoint**: Fluxo completo funcional no navegador sem erros de console ✅

---

## Fase 9: Polimento e Qualidade

**Objetivo**: Garantir qualidade, documentação e entregabilidade.

- [ ] T072 [P] Criar `CLAUDE.md` — guia do projeto para sessões futuras de desenvolvimento com IA
- [ ] T073 [P] Gerar `ia-predictor/openapi.yaml` final atualizado com todos os schemas reais
- [ ] T074 [P] Executar todos os testes unitários e corrigir falhas: `pytest tests/unit/ -v`
- [ ] T075 [P] Executar testes de integração: `pytest tests/integration/ -v`
- [ ] T076 Validação estatística formal: MAPE < 20% e SMAPE < 30% nos 2 produtos de maior volume
- [ ] T077 Executar Ljung-Box nos resíduos de todos os modelos treinados; logar resultados
- [ ] T078 Validação com usuários da entidade parceira — percurso guiado dos 5 User Stories
- [ ] T079 [P] Criar `docs/quickstart.md` — guia de instalação e uso para a entidade parceira
- [ ] T080 Commit final com toda a documentação e código: `git commit -m "feat: sistema de previsão de estoque v1.0.0"`

---

## Dependências e Ordem de Execução

### Dependências entre Fases

- **Fase 1** (Setup): sem dependências — começa imediatamente
- **Fase 2** (ETL): depende de Fase 1 — bloqueia Fases 3–8
- **Fase 3** (SARIMAX): depende de Fase 2 — bloqueia Fases 4–7
- **Fase 4** (Alertas): depende de Fase 3
- **Fase 5** (Model Status): depende de Fase 3 — paralela com Fase 4
- **Fase 6** (Simulação): depende de Fase 3 — paralela com Fases 4+5
- **Fase 7** (Exportação): depende de Fases 4+5
- **Fase 8** (Frontend): depende de Fases 2–7
- **Fase 9** (Polimento): depende de Fase 8

### Tarefas Paralelas por Fase

- Fase 1: T001–T010 podem rodar em paralelo (arquivos independentes)
- Fase 3: T022–T028 (testes) podem rodar em paralelo; T030–T033 (features) podem rodar em paralelo
- Fase 8: T062–T069 (componentes React) podem rodar em paralelo

### Estratégia MVP

1. Completar Fase 1 → Fase 2 → Fase 3 (T001–T044)
2. **MVP**: `POST /upload` + `GET /forecast/{id}` funcionando = core do sistema
3. Adicionar Fase 4 (alertas) → Fase 5 (status)
4. Adicionar Fase 6 (simulação) → Fase 7 (exportação)
5. Fase 8 (frontend) sobre API já estável

---

## Notas

- `[P]` = tarefa independente, pode ser executada em paralelo com outras `[P]` da mesma fase
- `[US#]` = rastreabilidade para User Story da spec
- Testes DEVEM falhar antes de implementação (TDD)
- Commit após cada Checkpoint validado
- Não avançar para próxima fase se Checkpoint atual falhou
