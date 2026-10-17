# Implementation Plan: Sistema de Previsão de Vendas para Floricultura

**Branch**: `001-sistema-previsao-vendas` | **Date**: 2026-07-28 (revisado 2026-08-30) | **Spec**: [spec.md](spec.md)

---

## Summary

Sistema web de **recomendação de reposição diária** para rede de floricultura com 3
unidades. Recebe planilhas XLSX de vendas, processa 324k+ transações históricas, treina
um modelo SARIMAX por `unidade × categoria` sobre a série **diária agregada** (camada L1),
desagrega a previsão para cada SKU do Top-N (camada L2) e aplica uma política de reposição
perecível-consciente (camada L3). Os resultados são expostos via API REST consumida por um
dashboard React. Os modelos L1 são reajustados semanalmente (o treino é pulado sem venda
nova); cada treino gera uma vez a previsão de 60 dias e o dashboard mostra os 14 dias a
partir de hoje. A previsão só é gerada de novo se o calendário mudar depois do treino.

Revisão de escopo (2026-08-30): antes o entregável era previsão **mensal** por produto.
Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`.

---

## Technical Context

**Language/Version**: Python 3.11 (backend) · TypeScript/Node 20 (frontend build)

**Primary Dependencies**:
- Backend: FastAPI 0.111, statsmodels 0.14 (SARIMAX L1), scikit-learn 1.4 (RF MDI),
  pandas 2.2, SQLAlchemy 2.0, APScheduler 3.10, joblib 1.4, openpyxl 3.1, reportlab 4.2,
  **python-jose[cryptography] 3.3** (JWT), **passlib[bcrypt] 1.7** (hash de senha).
  Demanda intermitente por SKU (Croston/TSB/SBA): implementação própria ou `statsforecast`
  — só na trilha de comparação em `training_scripts/`, não no runtime.
- Frontend: React 18, Recharts, Material UI, react-router, react-hook-form (já em
  app-react/), **openapi-typescript-codegen**.
- Dev/EDA (fora do runtime): Jupyter Notebooks, matplotlib, seaborn, plotly.

**Storage**: SQLite via SQLAlchemy; CSV para base transacional; joblib para artefatos de
modelo L1 (um por `unidade × categoria`).

**Testing**: pytest + pytest-asyncio (backend) · Vitest (frontend)

**Target Platform**: Servidor local Windows / Linux; acesso via navegador web

**Project Type**: Web service (API REST) + SPA frontend

**Performance Goals**:
- Upload 50 MB XLSX → processado em < 30s
- Endpoint de previsão / reposição → resposta em < 2s
- Reajuste semanal dos modelos L1 → concluído em < 2h
- Geração da previsão → concluída em < 15min

**Constraints**:
- Série histórica: ~26 meses → ~790 dias por `unidade × categoria`
- Mínimo de 180 dias para treinar um modelo L1
- Série diária por SKU é >90% zeros → SKU nunca é modelado isoladamente (camada L2)
- Reajuste e geração da previsão não podem bloquear o dashboard (rodam em background)
- `shelf_life_dias` por categoria é dado externo — default parametrizado até a parceira confirmar
- Categorias sem dados suficientes DEVEM ter status explícito, nunca silencioso

**Scale/Scope**: 6 pares `unidade × categoria` modelados em L1 (2 unidades × 3 categorias);
20 SKUs com desagregação/reposição detalhadas; 324k transações; 2 unidades; 1–5 usuários
simultâneos.

---

## Constitution Check

| Princípio | Status | Observação |
| --- | --- | --- |
| I. Domínio Puro | ✅ PASS | `backend/domain/` (etl, features, models, disaggregation, replenishment) não importa FastAPI/SQLAlchemy |
| II. Estatística antes de ML | ✅ PASS | L1 é SARIMAX; Croston/TSB só na trilha de comparação por SKU (série esparsa, SARIMAX inaplicável); NN/boosting exigem evidência empírica |
| III. Validação obrigatória | ✅ PASS | Walk-forward CV (≥4 folds, origem móvel, h=14d) + MASE < 1.0 + simulação de perda/ruptura antes de `status = "trained"` |
| IV. Interface para não-técnico | ✅ PASS | Recomendação e alertas em PT-BR sem jargão; SC-006 |
| V. Rastreabilidade total | ✅ PASS | `processing_log`, `retrain_history` (inclusive treinos `skipped`) e `forecast_runs` (cada geração da previsão) |
| VI. Segurança por Padrão | ✅ PASS | JWT em todos os `/api/v1/*`; bcrypt; sem dados pessoais na API |

**Resultado**: APROVADO — sem violações. Constituição v2.0.0.

---

## Project Structure

### Documentation (this feature)

```
specs/001-sistema-previsao-vendas/
├── plan.md              ← este arquivo
├── spec.md              ← especificação funcional
├── checklists/
│   └── requirements.md  ← checklist de qualidade
└── tasks.md             ← gerado por /speckit-tasks
```

### Source Code

```
ia-predictor/
│
├── backend/
│   ├── main.py                       # Entrypoint FastAPI
│   ├── config.py                     # Settings (pydantic-settings + .env)
│   ├── dependencies.py
│   │
│   ├── api/
│   │   ├── router_auth.py
│   │   ├── router_upload.py          # POST /api/v1/upload  [admin]
│   │   ├── router_products.py        # GET /api/v1/products[/{id}]  [viewer]
│   │   ├── router_forecast.py        # GET /api/v1/forecast/{id}, /batch  [viewer] — diário
│   │   ├── router_replenishment.py   # GET /api/v1/replenishment/{id}, /batch  [viewer]
│   │   ├── router_alerts.py          # GET /api/v1/alerts  [viewer]
│   │   ├── router_simulation.py      # POST /api/v1/simulation  [viewer]
│   │   ├── router_reports.py         # GET /api/v1/reports/export  [viewer]
│   │   ├── router_models.py          # GET|POST /api/v1/models/*  [admin para POST]
│   │   └── router_health.py          # GET /health  [público]
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── upload.py
│   │   ├── product.py
│   │   ├── forecast.py               # DailyPoint, ForecastResponse
│   │   ├── replenishment.py          # ReplenishmentRecommendation, ReplenishmentBatch
│   │   ├── alert.py
│   │   ├── simulation.py
│   │   ├── report.py
│   │   └── model_status.py
│   │
│   ├── services/
│   │   ├── upload_service.py
│   │   ├── forecast_service.py       # L1 forecast + L2 desagregação
│   │   ├── replenishment_service.py  # L3 política de reposição
│   │   ├── alert_service.py
│   │   ├── simulation_service.py
│   │   ├── report_service.py
│   │   └── retrain_service.py        # ajuste semanal dos modelos L1
│   │
│   ├── domain/
│   │   ├── etl/
│   │   │   ├── parser.py
│   │   │   ├── normalizer.py
│   │   │   └── deduplicator.py
│   │   ├── features/
│   │   │   ├── daily_series.py        # prepare_daily_series(df, unidade, categoria)
│   │   │   ├── calendar_exogenous.py  # dia-da-semana, feriados, dias-até-data-comemorativa
│   │   │   └── importance.py          # compute_rf_importance(), weight_features()
│   │   ├── models/                    # L1
│   │   │   ├── stationarity.py
│   │   │   ├── order_selection.py     # grid p,q∈0..2; P,Q∈0..1; m=7
│   │   │   ├── sarimax_trainer.py     # fit_sarimax(), run_category_pipeline()
│   │   │   ├── evaluator.py           # walk_forward_cv(h=14), mase(), rmsse(), residual_tests()
│   │   │   └── forecaster.py          # generate_daily_forecast() → ForecastResult
│   │   ├── disaggregation/            # L2
│   │   │   └── sku_split.py           # share móvel × perfil dia-da-semana; fallback uniforme
│   │   └── replenishment/             # L3
│   │       ├── policy.py              # qtd_repor(), cobertura, cadência
│   │       └── simulation.py          # perda (murcha) + ruptura sobre hold-out
│   │
│   ├── auth/
│   │   ├── jwt_handler.py
│   │   ├── password_handler.py
│   │   ├── dependencies.py
│   │   └── seed_users.py
│   │
│   └── infrastructure/
│       ├── database/
│       │   ├── engine.py
│       │   ├── models.py             # ORM: products, categories, model_artifacts,
│       │   │                         #      forecasts_cache, replenishment_cache,
│       │   │                         #      processing_log, retrain_history, users
│       │   └── migrations.py
│       ├── storage/
│       │   ├── file_manager.py
│       │   └── model_registry.py
│       └── scheduler/
│           ├── weekly_retrain.py     # APScheduler — segunda 02:00 (fit L1; pula sem venda nova)
│           └── calendar_check.py     # APScheduler — todo dia 03:00 (gera a previsão de novo só se o calendário mudou)
│
├── data/
│   ├── raw/
│   └── processed/
│       ├── contas_a_receber.csv
│       └── processamento_log.json
│
├── models/
│   └── {unidade}__{categoria}/
│       ├── sarimax_result.pkl
│       ├── importances.pkl
│       └── metadata.json
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_normalizer.py
│   │   ├── test_deduplicator.py
│   │   ├── test_daily_series.py
│   │   ├── test_calendar_exogenous.py
│   │   ├── test_importance.py
│   │   ├── test_stationarity.py
│   │   ├── test_order_selection.py
│   │   ├── test_evaluator.py          # mase, rmsse, cobertura, walk_forward h=14
│   │   ├── test_forecaster.py
│   │   ├── test_sku_split.py          # L2
│   │   ├── test_replenishment_policy.py  # L3
│   │   ├── test_alert_service.py
│   │   └── test_simulation_service.py
│   ├── integration/
│   │   ├── test_etl_pipeline.py
│   │   ├── test_l1_pipeline.py
│   │   ├── test_replenishment_pipeline.py
│   │   └── test_api_endpoints.py
│   └── fixtures/
│       ├── sample_data.csv
│       └── sample.xlsx
│
├── .env.example
├── requirements.txt
└── openapi.yaml
│
app-react/
└── src/
    ├── services/api/                 # gerado por openapi-typescript-codegen
    └── app/
        ├── auth/
        ├── pages/
        │   ├── Dashboard.tsx          # visão geral + reposição de hoje + upload (admin)
        │   ├── ProductDetail.tsx      # histórico diário + ForecastChart + métricas
        │   ├── Replenishment.tsx      # lista de reposição do dia por produto
        │   ├── Alerts.tsx
        │   └── Simulation.tsx
        └── components/
            ├── ForecastChart.tsx      # Recharts — histórico + previsão diária + IC 95%
            ├── ReplenishmentTable.tsx  # qtd, cobre-até, cadência, selo de risco
            ├── AlertList.tsx
            ├── UploadPanel.tsx        # role=admin
            └── ExportButton.tsx
```

**Structure Decision**: "web application" — backend Python em `ia-predictor/backend/`,
frontend React em `app-react/`. Comunicação via API REST definida em `openapi.yaml`.

---

## Phase 0 — Research

Código existente em `ia-predictor/` serve de referência. Decisões validadas contra o
artigo TCC e a revisão de escopo (ADR-009):

| Decisão | Evidência | Risco |
| --- | --- | --- |
| L1 = SARIMAX diário por `unidade × categoria`, m=7 | série agregada é densa; sazonalidade semanal é o efeito dominante em varejo perecível | Baixo |
| D=0 no termo sazonal | histórico < 3 ciclos anuais; P/Q semanais capturam o padrão | Baixo |
| L2 desagregação proporcional (não modelo por SKU) | série diária por SKU é >90% zeros; M5 mostra que rateio + intermitente supera SARIMAX por item | Baixo |
| L3 política determinística com shelf-life | perecibilidade exige limitar compra ao que vende dentro da validade | Médio — depende de `shelf_life_dias` real |
| MASE como métrica primária | M5 (varejo intermitente); MAPE/SMAPE instáveis com contagem baixa | Baixo |
| Croston/TSB só como comparação | Princípio II: SARIMAX central; intermitente é benchmark, não produção | Baixo |
| APScheduler in-process (2 jobs) | volume não justifica Celery | Baixo |
| React em vez de Streamlit/Dash | app-react/ já existente cobre RNF-01 | Baixo |

**Entregáveis acadêmicos desta fase** (seções 6.4 e 4.2 do artigo): diagramas UML em
`docs/uml/` e relatório de EDA em `docs/prediction/00-eda_report.md` — ver Fase 0 em `tasks.md`.
Item de levantamento adicional: **confirmar `shelf_life_dias` por categoria com a parceira**.

---

## Phase 1 — Design

### Contratos de API (15 endpoints)

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
| GET | `/api/v1/replenishment/{id}` | ✅ JWT | viewer |
| GET | `/api/v1/replenishment/batch` | ✅ JWT | viewer |
| GET | `/api/v1/alerts` | ✅ JWT | viewer |
| POST | `/api/v1/simulation` | ✅ JWT | viewer |
| GET | `/api/v1/reports/export` | ✅ JWT | viewer |
| GET | `/api/v1/models/status` | ✅ JWT | viewer |
| POST | `/api/v1/models/retrain` | ✅ JWT | admin |

### Infraestrutura de Autenticação

Fluxo JWT e tabela `users` inalterados pela revisão de escopo:

```
POST /auth/login { email, password }
  → bcrypt.verify(password, stored_hash)
  → access_token (JWT, 8h) + refresh_token (7d)

GET /api/v1/* Authorization: Bearer <access_token>
  → verifica assinatura + expiração → injeta current_user → checa role
```

```sql
users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  hashed_password TEXT NOT NULL, role TEXT NOT NULL, is_active BOOLEAN DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

Variáveis `.env` de auth: `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`,
`ACCESS_TOKEN_EXPIRE_HOURS=8`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `ADMIN_EMAIL/PASSWORD`,
`VIEWER_EMAIL/PASSWORD`.

### Cliente TypeScript Gerado (openapi-codegen)

```bash
npx openapi-generator-cli generate \
  -i ia-predictor/openapi.yaml -g typescript-fetch \
  -o app-react/src/services/api \
  --additional-properties=supportsES6=true,typescriptThreePlus=true
```

### Banco de Dados (SQLite)

```sql
products            (produto_cod PK, produto_nome, categoria, unidade, total_sold, updated_at)
categories          (id PK, unidade, categoria, shelf_life_dias, model_status,
                     mase, rmsse, ic_coverage_pct, observations_days, trained_at)
model_artifacts     (id PK, category_id FK, status, order, seasonal_order, use_log,
                     artifact_path, mase, rmsse, ic_coverage_pct, aic, bic,
                     trained_at, observations_days, error_message)
forecasts_cache     (id PK, produto_cod FK, forecast_date, predicted, lower_95, upper_95,
                     generated_at, model_id FK)
replenishment_cache (id PK, produto_cod FK, ref_date, qty_to_order, cover_until,
                     reorder_in_days, expected_waste, stockout_risk_pct, risk_label,
                     generated_at)
processing_log      (id PK, filename, file_hash, rows_added, rows_skipped,
                     rows_duplicate, processed_at)
retrain_history     (id PK, started_at, finished_at, trigger, categories_trained,
                     categories_failed, status)
```

### Pipeline Hierárquico (L1 → L2 → L3)

```
# L1 — por (unidade, categoria)
prepare_daily_series(df, unidade, categoria)      # soma diária; reindex completo
    └─ ≥ 180 dias?  → continua
    └─ < 180 dias?  → status = "insufficient_data", EXIT

build_calendar_exogenous(idx)                     # dow dummies/Fourier, feriados,
                                                 # dias-até-data-comemorativa
compute_rf_importance(X_train, y_train) → weight_features(clip=0.1)
check_stationarity(ts) → suggest_d(ts)            # d ∈ {0, 1}
select_sarimax_order(ts, exog, d, D=0, m=7,
    p,q ∈ 0..2 ; P,Q ∈ 0..1 ; criterion="aic")   # grid
fit_sarimax(ts_train, exog_train_w, order, seasonal_order)
walk_forward_cv(n_splits=4, horizon=14)           # MASE, RMSSE, cobertura IC
residual_tests()                                  # Ljung-Box + Shapiro-Wilk (log)

MASE < 1.0  E  cobertura ∈ [90,98]  E  simulação melhor que ingênua?
    → status = "trained"   ; salva artefato joblib + metadados
else
    → status = "low_confidence" ; salva com aviso

generate_daily_forecast(model, exog_future, horizon=14) → ForecastResult (por categoria)

# L2 — por SKU do Top-N
share_sku = média móvel 4–8 semanas da participação do SKU na categoria
perfil_dow_sku = perfil de dia-da-semana do SKU
previsao_sku[d] = previsao_categoria[d] * share_sku * ajuste_dow
    └─ SKU com < 28 dias c/ venda ou < 8 vendas → rateio uniforme da categoria

# L3 — por SKU do Top-N
cobertura_alvo = min(shelf_life_dias, FORECAST_HORIZON_DAYS)
qty_to_order(t) = max(0, Σ previsao_sku[t..t+cobertura_alvo-1]
                        + safety_stock - estoque_atual)
expected_waste, stockout_risk, reorder_in_days, cover_until → replenishment_cache
```

### Agendamento

- **`weekly_retrain.py`** — `CronTrigger(day_of_week="mon", hour=2)` → se não há venda nova
  desde o último treino `done` e a config é a mesma, grava `retrain_history` como `skipped`
  e para; senão reajusta (fit) todos os modelos L1, grava `retrain_history` e gera a
  previsão (`forecast_runs` com `trigger = retrain`): `FORECAST_STORED_DAYS` (60) dias a
  partir do último dia com venda, com L2, em `forecasts_cache`.
- **`calendar_check.py`** — `CronTrigger(hour=3)` → se algum `calendar_days.updated_at` é
  posterior à última geração, carrega os modelos do último treino (`artifact_path`) e gera
  a previsão de novo (`trigger = calendar`). Senão não faz nada: com o mesmo modelo e os
  mesmos dados, a previsão seria a mesma.
- A API entrega os `FORECAST_HORIZON_DAYS` (14) dias a partir de hoje da última geração
  `done`; a janela anda com a data sem recalcular.

---

## Complexity Tracking

Nenhuma violação constitucional identificada.

---

## Suggested Commit Message

```
docs: revisão de escopo mensal→diário (reposição perecível) — constituição v2.0.0, ADR-009
```
