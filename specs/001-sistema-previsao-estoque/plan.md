# Implementation Plan: Sistema de Previsão de Estoque para Floricultura

**Branch**: `001-sistema-previsao-estoque` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)

---

## Summary

Sistema web completo de previsão de demanda para rede de floricultura com 3 unidades.
Recebe planilhas XLSX mensais, processa 324k+ transações históricas, treina modelos
SARIMAX por produto com ponderação de variáveis exógenas via Random Forest, e expõe
os resultados via API REST consumida por um dashboard React interativo.
O retrain é automatizado semanalmente via scheduler interno.

---

## Technical Context

**Language/Version**: Python 3.11 (backend) · TypeScript/Node 20 (frontend build)

**Primary Dependencies**:
- Backend: FastAPI 0.111, statsmodels 0.14, scikit-learn 1.4, pandas 2.2, SQLAlchemy 2.0, APScheduler 3.10, joblib 1.4, openpyxl 3.1, reportlab 4.2, **python-jose[cryptography] 3.3** (JWT), **passlib[bcrypt] 1.7** (hash de senha)
- Frontend: React 18, Recharts, Material UI, react-router, react-hook-form (já em app-react/), **openapi-typescript-codegen** (cliente HTTP gerado de openapi.yaml)

**Storage**: SQLite via SQLAlchemy (modelo de dados relacional); CSV para base transacional; joblib para artefatos de modelo

**Testing**: pytest + pytest-asyncio (backend) · Vitest (frontend)

**Target Platform**: Servidor local Windows / Linux; acesso via navegador web

**Project Type**: Web service (API REST) + SPA frontend

**Performance Goals**:
- Upload 50 MB XLSX → processado em < 30s
- Endpoint de previsão → resposta em < 2s
- Retrain de 20 produtos → concluído em < 2h

**Constraints**:
- Série histórica máxima disponível: 26 meses mensais
- Mínimo de 15 observações para treinar modelo
- Retrain não pode bloquear o dashboard (deve rodar em background)
- Modelos sem dados suficientes DEVEM ter status explícito, nunca silencioso

**Scale/Scope**: 20 produtos modelados; 324k transações; 3 unidades operacionais; 1–5 usuários simultâneos

---

## Constitution Check

| Princípio | Status | Observação |
| --- | --- | --- |
| I. Domínio Puro | ✅ PASS | `backend/domain/` não importará FastAPI/SQLAlchemy |
| VI. Segurança por Padrão | ✅ PASS | JWT obrigatório em todos os `/api/v1/*`; bcrypt para senhas; sem dados pessoais na API |
| II. Estatística antes de ML | ✅ PASS | SARIMAX é o modelo central; RF apenas como pré-processamento de importância |
| III. Validação obrigatória | ✅ PASS | Walk-forward CV (4 folds) obrigatório antes de `status = "trained"` |
| IV. Interface para não-técnico | ✅ PASS | Mensagens de status em PT-BR sem jargão; SC-006 |
| V. Rastreabilidade total | ✅ PASS | `processing_log` e `retrain_history` obrigatórios |

**Resultado**: APROVADO — sem violações.

---

## Project Structure

### Documentation (this feature)

```
specs/001-sistema-previsao-estoque/
├── plan.md              ← este arquivo
├── spec.md              ← especificação funcional
├── checklists/
│   └── requirements.md  ← checklist de qualidade (aprovado)
└── tasks.md             ← gerado por /speckit-tasks
```

### Source Code

```
ia-predictor/
│
├── backend/                          # Pacote principal Python
│   ├── main.py                       # Entrypoint FastAPI
│   ├── config.py                     # Settings (pydantic-settings + .env)
│   ├── dependencies.py               # Injeção de dependências
│   │
│   ├── api/                          # Routers HTTP (apresentação)
│   │   ├── router_auth.py            # POST /auth/login, /auth/refresh, GET /auth/me
│   │   ├── router_upload.py          # POST /api/v1/upload  [admin]
│   │   ├── router_products.py        # GET /api/v1/products[/{id}]  [viewer]
│   │   ├── router_forecast.py        # GET /api/v1/forecast/{id}, /batch  [viewer]
│   │   ├── router_alerts.py          # GET /api/v1/alerts  [viewer]
│   │   ├── router_simulation.py      # POST /api/v1/simulation  [viewer]
│   │   ├── router_reports.py         # GET /api/v1/reports/export  [viewer]
│   │   ├── router_models.py          # GET|POST /api/v1/models/*  [admin para POST]
│   │   └── router_health.py          # GET /health  [público]
│   │
│   ├── schemas/                      # Pydantic (contratos de API)
│   │   ├── auth.py                   # LoginRequest, TokenResponse, UserOut
│   │   ├── upload.py
│   │   ├── product.py
│   │   ├── forecast.py
│   │   ├── alert.py
│   │   ├── simulation.py
│   │   ├── report.py
│   │   └── model_status.py
│   │
│   ├── services/                     # Casos de uso (aplicação)
│   │   ├── upload_service.py
│   │   ├── forecast_service.py
│   │   ├── alert_service.py
│   │   ├── simulation_service.py
│   │   ├── report_service.py
│   │   └── retrain_service.py
│   │
│   ├── domain/                       # Lógica pura (sem I/O)
│   │   ├── etl/
│   │   │   ├── parser.py             # XLSX → records
│   │   │   ├── normalizer.py         # tipos, limpeza, datas
│   │   │   └── deduplicator.py       # dedup por (doc_numero, produto_cod)
│   │   ├── features/
│   │   │   ├── time_series.py        # prepare_monthly_series()
│   │   │   ├── exogenous.py          # build_exogenous_features() — 15 variáveis
│   │   │   └── importance.py         # compute_rf_importance(), weight_features()
│   │   └── models/
│   │       ├── stationarity.py       # check_stationarity(), suggest_d()
│   │       ├── order_selection.py    # grid AIC/BIC — 36 combinações
│   │       ├── sarimax_trainer.py    # fit_sarimax(), run_product_pipeline()
│   │       ├── evaluator.py          # walk_forward_cv(), residual_tests()
│   │       └── forecaster.py         # generate_forecast() → ForecastResult
│   │
│   ├── auth/                         # Módulo de autenticação e autorização
│   │   ├── jwt_handler.py            # create_access_token(), decode_token()
│   │   ├── password_handler.py       # hash_password(), verify_password() — bcrypt
│   │   ├── dependencies.py           # get_current_user(), require_admin()
│   │   └── seed_users.py             # script de criação de usuários iniciais
│   │
│   └── infrastructure/               # I/O externo
│       ├── database/
│       │   ├── engine.py
│       │   ├── models.py             # ORM: products, model_artifacts, forecasts_cache,
│       │   │                         #      processing_log, retrain_history, users
│       │   └── migrations.py
│       ├── storage/
│       │   ├── file_manager.py       # leitura/escrita CSV, pickle
│       │   └── model_registry.py     # save/load artefatos + metadados
│       └── scheduler/
│           └── weekly_retrain.py     # APScheduler — segunda-feira 02:00
│
├── data/
│   ├── raw/                          # XLSX recebidos (upload)
│   └── processed/
│       ├── contas_a_receber.csv      # base consolidada (sep=";")
│       └── processamento_log.json
│
├── models/                           # Artefatos treinados
│   └── {produto_cod}/
│       ├── sarimax_result.pkl
│       ├── importances.pkl
│       └── metadata.json
│
├── tests/
│   ├── unit/                         # Testes de domínio isolado
│   │   ├── test_parser.py
│   │   ├── test_normalizer.py
│   │   ├── test_deduplicator.py
│   │   ├── test_time_series.py
│   │   ├── test_exogenous.py
│   │   ├── test_importance.py
│   │   ├── test_stationarity.py
│   │   ├── test_order_selection.py
│   │   ├── test_evaluator.py
│   │   ├── test_forecaster.py
│   │   ├── test_alert_service.py
│   │   └── test_simulation_service.py
│   ├── integration/
│   │   ├── test_etl_pipeline.py
│   │   ├── test_sarimax_pipeline.py
│   │   └── test_api_endpoints.py
│   └── fixtures/
│       ├── sample_data.csv
│       └── sample.xlsx
│
├── .env.example
├── requirements.txt
└── openapi.yaml                      # Spec OpenAPI 3.0 (fonte da verdade dos contratos)
│
app-react/                            # Frontend React (existente — integrar via API)
└── src/
    ├── services/
    │   └── api/                      # gerado automaticamente por openapi-typescript-codegen
    │       ├── apis/                 # ForecastApi, AlertsApi, AuthApi, ...
    │       ├── models/               # tipos TypeScript de todos os schemas
    │       └── index.ts
    └── app/
        ├── auth/
        │   ├── AuthContext.tsx        # React context com token + user + role
        │   ├── LoginPage.tsx          # formulário de login
        │   └── PrivateRoute.tsx       # redireciona para /login se não autenticado
        ├── pages/
        │   ├── Dashboard.tsx          # visão geral + alertas + upload (admin)
        │   ├── ProductDetail.tsx      # histórico + ForecastChart + métricas
        │   ├── Alerts.tsx             # lista priorizada de alertas
        │   └── Simulation.tsx         # cenários de promoção
        └── components/
            ├── ForecastChart.tsx      # Recharts — histórico + previsão + IC 95%
            ├── AlertList.tsx
            ├── UploadPanel.tsx        # visível apenas para role=admin
            └── ExportButton.tsx
```

**Structure Decision**: Opção "web application" adaptada — backend Python separado de frontend React existente. Backend em `ia-predictor/backend/`, frontend em `app-react/`. Comunicação via API REST definida em `openapi.yaml`.

---

## Phase 0 — Research (Concluído)

Código existente em `ia-predictor/src/` foi analisado e servirá de referência, não de ponto de partida. As seguintes decisões técnicas foram validadas contra o artigo TCC:

| Decisão | Evidência | Risco |
| --- | --- | --- |
| D=0 no SARIMAX sazonal | 26 meses < 3 ciclos completos (36) | Baixo — P/Q capturam sazonalidade |
| log1p para CV > 0.7 | Série com alta variância — evita heterocedasticidade | Baixo |
| RF MDI para ponderação | Breiman 2001 — evita multicolinearidade | Baixo |
| Grid 36 combinações AIC | Balanceia tempo e qualidade | Médio — ~3min/produto |
| APScheduler in-process | Volume não justifica Celery | Baixo para ≤ 20 produtos |

---

## Phase 1 — Design

### Contratos de API (13 endpoints)

| Método | Endpoint | Auth | Perfil mínimo |
| --- | --- | --- | --- |
| GET | `/health` | ❌ público | — |
| POST | `/auth/login` | ❌ público | — |
| POST | `/auth/refresh` | ✅ JWT | qualquer |
| GET | `/auth/me` | ✅ JWT | qualquer |
| POST | `/api/v1/upload` | ✅ JWT | admin |
| GET | `/api/v1/products` | ✅ JWT | viewer |
| GET | `/api/v1/products/{id}` | ✅ JWT | viewer |
| GET | `/api/v1/forecast/{id}` | ✅ JWT | viewer |
| GET | `/api/v1/forecast/batch` | ✅ JWT | viewer |
| GET | `/api/v1/alerts` | ✅ JWT | viewer |
| POST | `/api/v1/simulation` | ✅ JWT | viewer |
| GET | `/api/v1/reports/export` | ✅ JWT | viewer |
| GET | `/api/v1/models/status` | ✅ JWT | viewer |
| POST | `/api/v1/models/retrain` | ✅ JWT | admin |

### Infraestrutura de Autenticação

**Fluxo JWT**:

```
POST /auth/login { email, password }
  → bcrypt.verify(password, stored_hash)
  → gera access_token (JWT, expira 8h) + refresh_token (expira 7d)
  → retorna { access_token, refresh_token, role, expires_in }

GET /api/v1/* Authorization: Bearer <access_token>
  → middleware verifica assinatura JWT + expiração
  → injeta current_user no request
  → verifica role se endpoint é admin-only → 403 se insuficiente

POST /auth/refresh { refresh_token }
  → valida refresh_token → emite novo access_token
```

**Tabela `users` (SQLite)**:

```sql
users (
  id          INTEGER PRIMARY KEY,
  email       TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  hashed_password TEXT NOT NULL,   -- bcrypt
  role        TEXT NOT NULL,       -- "admin" | "viewer"
  is_active   BOOLEAN DEFAULT 1,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Usuários iniciais** (criados via script `seed_users.py` ou variáveis `.env`):

```
ADMIN_EMAIL=gestora@floricultura.com
ADMIN_PASSWORD=<gerado no primeiro boot>
VIEWER_EMAIL=gerente@floricultura.com
VIEWER_PASSWORD=<gerado no primeiro boot>
JWT_SECRET_KEY=<string aleatória 32+ chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=8
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Cliente TypeScript Gerado (openapi-codegen)

```bash
# Instalar gerador (uma vez)
npm install -g @openapitools/openapi-generator-cli

# Regenerar sempre que openapi.yaml mudar
npx openapi-generator-cli generate \
  -i ia-predictor/openapi.yaml \
  -g typescript-fetch \
  -o app-react/src/services/api \
  --additional-properties=supportsES6=true,typescriptThreePlus=true
```

O cliente gerado expõe classes como `ForecastApi`, `AlertsApi`, `AuthApi`
com métodos tipados e injeção automática do header `Authorization: Bearer`
via `Configuration.accessToken`.

Contratos completos com request/response JSON definidos em `SPECS.md` e formalizados em `openapi.yaml`.

### Banco de Dados (SQLite)

```sql
products            (produto_cod PK, produto_nome, total_sold, updated_at)
model_artifacts     (id PK, produto_cod FK, status, order, seasonal_order,
                     use_log, artifact_path, mae, rmse, mape, smape, r2,
                     aic, bic, trained_at, observations, error_message)
forecasts_cache     (id PK, produto_cod FK, forecast_date, predicted,
                     lower_95, upper_95, generated_at, model_id FK)
processing_log      (id PK, filename, file_hash, rows_added, rows_skipped,
                     rows_duplicate, processed_at)
retrain_history     (id PK, started_at, finished_at, trigger, products_trained,
                     products_failed, status)
```

### Pipeline SARIMAX por Produto

```
prepare_monthly_series(df, produto_cod)
    └─ 15+ obs?  → continua
    └─ < 15 obs? → status = "insufficient_data", EXIT

build_exogenous_features(df, produto_cod)         # 15 variáveis
compute_rf_importance(X_train, y_train)           # 200 árvores
weight_features(X, importances)                   # clip(lower=0.1)

check_stationarity(ts_train)
suggest_d(ts_train)                               # d ∈ {0, 1}

select_sarimax_order(ts_train, exog_train_w,
    p_range=0..2, q_range=0..2,
    P_range=0..1, Q_range=0..1,
    D=0, m=12, criterion="aic")                   # 36 combinações

fit_sarimax(ts_train, exog_train_w, order, seasonal_order)
walk_forward_cv(df, produto_cod, n_splits=4)      # validação obrigatória

MAPE < 20% e SMAPE < 30%?
    → status = "trained"
    → salva artefato joblib + metadados
else
    → status = "low_confidence"
    → salva com aviso

generate_forecast(model, importances, last_exog, horizon=3)
    → ForecastResult{dates, predicted, lower_95, upper_95}
```

---

## Complexity Tracking

Nenhuma violação constitucional identificada — seção omitida conforme instrução do template.

---

## Suggested Commit Message

```
docs: add spec-kit constitution, feature spec and implementation plan (v1.0.0)
```
