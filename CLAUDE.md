# CLAUDE.md — Sistema de Previsão de Estoque · Floricultura

Guia para sessões de desenvolvimento com Claude Code.
Leia este arquivo antes de qualquer implementação.

---

## O que é este projeto

TCC de Ciência da Computação (Centro Universitário Dom Helder, 2026), em parceria com a
Floricultura Verde Perto (unidades em Nova Lima — Jardim Canadá — e Itabirito/MG).
Sistema de previsão de demanda para rede de floricultura com 3 unidades operacionais,
baseado em modelos SARIMAX com atualização semanal automática e dashboard React.

**Domínio**: floricultura · alta perecibilidade · sazonalidade por datas comemorativas  
**Dados**: 324k+ transações · Jan/2024–Fev/2026 · 5.100+ SKUs · 3 unidades  
**Horizonte de previsão**: 2–3 semanas (operacional), mapeado para granularidade mensal
com previsão de 1–3 meses à frente  
**Metodologia**: ágil/iterativa para o software; CRISP-DM (compreensão do negócio →
compreensão dos dados → preparação → modelagem → avaliação → implantação) para o
pipeline de dados e modelagem preditiva

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Backend API | FastAPI 0.111 + Python 3.11 |
| Modelagem | statsmodels 0.14 (SARIMAX) + scikit-learn 1.4 (RF) |
| Análise exploratória (EDA) | Jupyter Notebooks + matplotlib, seaborn, plotly (não entram no runtime de produção) |
| Auth | python-jose (JWT HS256) + passlib (bcrypt) |
| Banco | SQLite via SQLAlchemy 2.0 |
| Scheduler | APScheduler 3.10 (segunda-feira 02:00) |
| Serialização | joblib (modelos), openpyxl (XLSX), reportlab (PDF) |
| Frontend | React 18 + Recharts + MUI (em `app-react/`) — decisão pós-prototipagem; o projeto técnico original cogitava Streamlit/Dash |
| Cliente HTTP | gerado de `openapi.yaml` via openapi-typescript-codegen |

---

## Estrutura de Diretórios

```
TCC---Inventory-Forecasting/
├── CLAUDE.md                    ← este arquivo
├── SPECS.md                     ← referência técnica completa
├── ia-predictor/
│   ├── openapi.yaml             ← FONTE DA VERDADE dos contratos de API
│   ├── backend/                 ← aplicação Python (monolito modular)
│   │   ├── main.py              ← entrypoint FastAPI
│   │   ├── config.py            ← Settings (pydantic-settings + .env)
│   │   ├── auth/                ← JWT, bcrypt, dependencies, seed_users
│   │   ├── api/                 ← routers HTTP (um por recurso)
│   │   ├── schemas/             ← Pydantic (contratos request/response)
│   │   ├── services/            ← casos de uso (orquestração)
│   │   ├── domain/              ← lógica pura SEM I/O
│   │   │   ├── etl/             ← parser, normalizer, deduplicator
│   │   │   ├── features/        ← time_series, exogenous, importance
│   │   │   └── models/          ← stationarity, order_selection, trainer, evaluator, forecaster
│   │   └── infrastructure/      ← DB, storage, scheduler
│   ├── data/
│   │   ├── raw/                 ← XLSX brutos (upload)
│   │   └── processed/
│   │       └── contas_a_receber.csv   ← base consolidada (sep=";")
│   ├── models/                  ← artefatos joblib por produto
│   ├── training_scripts/        ← experimentação pré-produção do SARIMAX (fora do backend)
│   │   ├── preprocessing/       ← XLSX bruto → CSV consolidado/treino (docs/prediction/pre_processing.md)
│   │   ├── eda/                 ← análise exploratória (sazonalidade, CV, seleção Top-N)
│   │   ├── baseline/            ← Modelo A0 (SARIMA puro) e A1 (SARIMAX interno)
│   │   ├── enriched/            ← Modelo B (SARIMAX interno + exógenas externas)
│   │   ├── alternative_models/  ← ETS, XGBoost, Prophet, rede neural global
│   │   ├── validation/          ← walk-forward CV, testes de resíduos/significância (compartilhado)
│   │   ├── output/               ← CSV/JSON gerados pelo preprocessing/ (gitignored)
│   │   └── results/             ← metrics/ e plots/ da experimentação (staging, não é o results/ de produção)
│   └── tests/
│       ├── unit/                ← testes de domínio isolado
│       ├── integration/         ← testes de API e pipeline
│       └── fixtures/            ← sample.xlsx, sample_data.csv
├── app-react/                   ← frontend React (existente)
│   └── src/
│       ├── services/api/        ← GERADO de openapi.yaml (não editar manualmente)
│       └── app/
│           ├── auth/            ← AuthContext, LoginPage, PrivateRoute
│           ├── pages/           ← Dashboard, ProductDetail, Alerts, Simulation
│           └── components/      ← ForecastChart, AlertList, UploadPanel, ExportButton
├── specs/
│   └── 001-sistema-previsao-estoque/
│       ├── spec.md              ← especificação funcional (User Stories)
│       ├── plan.md              ← plano técnico e arquitetura
│       └── tasks.md             ← 80+ tarefas por fase com TDD
└── docs/                        ← documentação organizada por área (ver docs/README.md)
    ├── project/                 ← projeto técnico (PDF) e estado atual do sistema
    ├── prediction/              ← ADRs de modelagem + plano de experimentos comparativos
    ├── backend/                 ← ADRs de arquitetura de serviço/API
    ├── database/                ← ADRs de persistência
    ├── frontend/                ← ADRs do dashboard React
    └── uml/                     ← diagramas UML (caminho fixo, seção 6.4 do artigo)
```

---

## Regras Invioláveis (Constituição v1.1.0)

Consulte `.specify/memory/constitution.md` para o texto completo. Resumo:

1. **Domínio Puro**: `backend/domain/` NUNCA importa FastAPI, SQLAlchemy ou APScheduler.
2. **SARIMAX central**: não introduzir LSTM/XGBoost sem evidência de superioridade no dataset.
3. **Validação obrigatória**: walk-forward CV (≥4 folds) antes de `status = "trained"`.
4. **Linguagem do usuário**: mensagens de erro e alertas em PT-BR sem jargão técnico.
5. **Rastreabilidade**: todo upload e retrain gravados em tabelas `processing_log` e `retrain_history`.
6. **Segurança por padrão**: JWT obrigatório em todos os `/api/v1/*`; bcrypt para senhas; API não expõe dados pessoais de clientes.

---

## Comandos Essenciais

```bash
# Instalar dependências do backend
pip install -r ia-predictor/requirements.txt

# Criar usuários iniciais (roda uma vez ou via startup)
python ia-predictor/backend/auth/seed_users.py

# Iniciar o servidor de desenvolvimento
uvicorn backend.main:app --reload --app-dir ia-predictor

# Acessar documentação interativa
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)

# Rodar testes unitários
pytest ia-predictor/tests/unit/ -v

# Rodar testes de integração
pytest ia-predictor/tests/integration/ -v

# Regenerar cliente TypeScript após mudar openapi.yaml
cd app-react && npm run generate:api

# Iniciar frontend React
cd app-react && npm run dev
```

---

## Variáveis de Ambiente (.env)

```
# Banco
DATABASE_URL=sqlite:///./floricultura.db

# Diretórios
DATA_DIR=data
MODELS_DIR=models

# Auth (OBRIGATÓRIO configurar antes do primeiro boot)
JWT_SECRET_KEY=<string_aleatoria_32_chars_minimo>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=8
REFRESH_TOKEN_EXPIRE_DAYS=7

# Usuários iniciais
ADMIN_EMAIL=gestora@floricultura.com
ADMIN_PASSWORD=<senha_forte>
VIEWER_EMAIL=gerente@floricultura.com
VIEWER_PASSWORD=<senha_forte>

# Pipeline ML
TOP_N_PRODUCTS=20
TEST_MONTHS=3
FUTURE_MONTHS=3
MIN_OBSERVATIONS=15
LOG_CV_THRESHOLD=0.7

# Scheduler
RETRAIN_DAY_OF_WEEK=mon
RETRAIN_HOUR=2
```

---

## Modelo de Dados — Tabelas SQLite

| Tabela | Propósito |
| --- | --- |
| `users` | Usuários com e-mail, hash bcrypt, role (admin/viewer) |
| `products` | Catálogo com total_sold e updated_at |
| `model_artifacts` | Ordem, métricas, paths de artefatos, status por produto |
| `forecasts_cache` | Previsões geradas (evita recalcular a cada request) |
| `processing_log` | Log de cada upload XLSX (filename, hash, rows) |
| `retrain_history` | Histórico de retrains (trigger, duração, contagens) |

---

## Pipeline SARIMAX — Decisões Técnicas

| Decisão | Valor | Motivo |
| --- | --- | --- |
| D (diferenciação sazonal) | 0 | 26 meses < 3 ciclos completos (36); P/Q capturam sazonalidade |
| d (diferenciação regular) | 0 ou 1 (via ADF) | limitado a 1 para não consumir dados de treino |
| log1p | se CV > 0.7 | estabiliza variância em séries com alta variabilidade |
| Grid de ordens | 36 combinações (p,q ∈ 0..2; P,Q ∈ 0..1) | balanceia tempo e qualidade |
| Critério de seleção | AIC | equilíbrio ajuste vs. parcimônia |
| Ponderação de exógenas | RF MDI, clip(lower=0.1) | evita multicolinearidade sem zerar variáveis |
| Meses de alta temporada | {5, 10, 11, 12} | Maio (Mães), Out/Nov/Dez (comemorativas) |
| Mínimo de observações | 15 meses | abaixo disso: insufficient_data, sem modelo |
| Hold-out para avaliação | 3 meses | test_pred vs. ts_test |
| Walk-forward CV | 4 folds | obrigatório antes de status = "trained" |
| Granularidade de produção | Mensal | ciclo de reposição semanal/mensal; dados diários têm >70% de zeros por produto |
| Avaliação comparativa mensal vs. diária | walk-forward nos mesmos produtos | contribuição acadêmica (ii) do artigo — relatório, não muda a granularidade de produção |

---

## Limiares de Qualidade dos Modelos

| Métrica | Limiar | Status se falhar |
| --- | --- | --- |
| MAPE (alto giro) | < 20% | `low_confidence` |
| SMAPE (top 2 produtos) | < 30% | `low_confidence` |
| Observações mínimas | ≥ 15 mensais | `insufficient_data` |
| Ljung-Box (p-value) | > 0.05 | log de aviso; não bloqueia deploy |
| Shapiro-Wilk (p-value) | > 0.05 | log de aviso; não bloqueia deploy |

`low_confidence` ≠ falha: previsão ainda é gerada, mas com aviso visual no dashboard.
Ljung-Box e Shapiro-Wilk compõem a dimensão de "diagnóstico de resíduos" da validação
(seção 6.5 do artigo) — não bloqueiam o deploy, mas MUST ser logados por modelo treinado.

---

## Contratos de API — Perfis de Acesso

| Endpoint | Método | Perfil |
| --- | --- | --- |
| `/health` | GET | público |
| `/auth/login` | POST | público |
| `/auth/refresh` | POST | qualquer |
| `/auth/me` | GET | qualquer |
| `/api/v1/upload` | POST | **admin** |
| `/api/v1/models/retrain` | POST | **admin** |
| Demais `/api/v1/*` | GET/POST | viewer |

---

## Spec-Kit

Este projeto usa GitHub Spec-Kit (`specify-cli 0.14.3`) instalado como skills em `.claude/skills/`.

Comandos disponíveis (invocar via Skill tool ou como `/speckit-*`):

| Skill | Propósito |
| --- | --- |
| `/speckit-constitution` | Atualizar princípios em `.specify/memory/constitution.md` |
| `/speckit-specify` | Criar nova spec de feature em `specs/` |
| `/speckit-plan` | Criar plano técnico para a spec ativa |
| `/speckit-tasks` | Gerar lista de tarefas a partir do plano |
| `/speckit-analyze` | Verificar consistência entre spec, plan e tasks |
| `/speckit-converge` | Comparar codebase atual com tasks pendentes |
| `/speckit-implement` | Executar próxima tarefa pendente do tasks.md |

---

## Artefatos de Referência

| Arquivo | Conteúdo |
| --- | --- |
| `SPECS.md` | Especificação técnica completa (arquitectura, módulos, schemas) |
| `ia-predictor/openapi.yaml` | Contratos de API em OpenAPI 3.0 (fonte da verdade) |
| `specs/001-sistema-previsao-estoque/spec.md` | User Stories e requisitos funcionais |
| `specs/001-sistema-previsao-estoque/plan.md` | Plano técnico com constitution check |
| `specs/001-sistema-previsao-estoque/tasks.md` | 80+ tarefas organizadas em 9 fases |
| `.specify/memory/constitution.md` | 6 princípios governantes (v1.1.1) |
| `docs/README.md` | Índice da documentação por área + convenção de ADRs |
| `docs/prediction/`, `docs/backend/`, `docs/database/`, `docs/frontend/` | ADRs organizados por área (ver `docs/README.md` para a lista completa) |
| `docs/project/Projeto Tecnico Verde Perto Final...pdf` | Projeto técnico acadêmico original (fonte primária, revisado pelo orientador) |
| `docs/project/current_files_state.md` | Raio-x do que já foi feito (dados, pré-processamento, modelagem) vs. requisitos do artigo |
| `docs/prediction/plano_experimentos_modelagem.md` | Plano de experimentos: SARIMAX baseline × enriquecido × redes neurais/outros modelos |
| `docs/prediction/pre_processing.md` | O que os scripts de `training_scripts/preprocessing/` fazem e por quê (colunas removidas/discretizadas) |
| `docs/uml/` *(parcial — 2 de 5 diagramas)* | Diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica (seção 6.4 do artigo) |
| `docs/eda_report.md` *(a criar)* | Relatório de análise exploratória — sazonalidade, tendências, comportamento por unidade, perfil de demanda |
