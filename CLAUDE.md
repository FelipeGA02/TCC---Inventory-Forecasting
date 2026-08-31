# CLAUDE.md — Sistema de Previsão de Estoque · Floricultura

Guia para sessões de desenvolvimento com Claude Code.
Leia este arquivo antes de qualquer implementação.

---

## O que é este projeto

TCC de Ciência da Computação (Centro Universitário Dom Helder, 2026), em parceria com a
Floricultura Verde Perto (unidades em Nova Lima — Jardim Canadá — e Itabirito/MG).
Sistema de **recomendação de reposição diária** para rede de floricultura com 3 unidades
operacionais, baseado em modelagem hierárquica (SARIMAX na demanda agregada +
desagregação para SKU + política de reposição perecível-consciente) e dashboard React.

**Domínio**: floricultura · alta perecibilidade (flores de corte duram 3–7 dias) ·
sazonalidade semanal + datas comemorativas  
**Dados**: 324k+ transações · Jan/2024–Fev/2026 · 5.100+ SKUs · 3 unidades  
**Entregável**: quantidade sugerida de reposição por produto **por dia**, horizonte de
**14 dias**, com risco de perda (murcha) e de ruptura  
**Granularidade**: diária. Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`
(revisão de escopo de 2026-08-30 — antes era mensal)  
**Metodologia**: ágil/iterativa para o software; CRISP-DM (compreensão do negócio →
compreensão dos dados → preparação → modelagem → avaliação → implantação) para o
pipeline de dados e modelagem preditiva

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Backend API | FastAPI 0.111 + Python 3.11 |
| Modelagem | statsmodels 0.14 (SARIMAX — camada agregada L1) + scikit-learn 1.4 (RF) + Croston/TSB/SBA (demanda intermitente por SKU — trilha de comparação) |
| Análise exploratória (EDA) | Jupyter Notebooks + matplotlib, seaborn, plotly (não entram no runtime de produção) |
| Auth | python-jose (JWT HS256) + passlib (bcrypt) |
| Banco | SQLite via SQLAlchemy 2.0 |
| Scheduler | APScheduler 3.10 (ajuste dos modelos L1 segunda 02:00 · geração de previsão+reposição diária 03:00) |
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
│   │   │   ├── features/        ← daily_series (unidade×categoria), calendar_exogenous, importance
│   │   │   ├── models/          ← L1: stationarity, order_selection, trainer, evaluator, forecaster
│   │   │   ├── disaggregation/  ← L2: rateio categoria→SKU (share móvel × perfil dia-da-semana)
│   │   │   └── replenishment/   ← L3: política de reposição (shelf-life, estoque de segurança)
│   │   └── infrastructure/      ← DB, storage, scheduler
│   ├── data/
│   │   ├── raw/                 ← XLSX brutos (upload)
│   │   └── processed/
│   │       └── contas_a_receber.csv   ← base consolidada (sep=";")
│   ├── models/                  ← artefatos joblib por unidade×categoria (L1) + params L2/L3
│   ├── training_scripts/        ← experimentação pré-produção (fora do backend)
│   │   ├── preprocessing/       ← XLSX bruto → série diária por unidade×categoria (docs/prediction/01-pre_processing.md)
│   │   ├── eda/                 ← análise exploratória (sazonalidade semanal, esparsidade por SKU, Top-N)
│   │   ├── baseline/            ← L1: A0 (SARIMA puro) e A1 (SARIMAX + exógenas de calendário) diário
│   │   ├── enriched/            ← L1 Modelo B (SARIMAX + exógenas externas: clima, feriados municipais)
│   │   ├── alternative_models/  ← Croston/TSB/SBA por SKU, ETS, XGBoost, rede neural global
│   │   ├── replenishment/       ← L2 desagregação + L3 política; simulação de perda/ruptura
│   │   ├── validation/          ← walk-forward CV (origem móvel, h=14d), MASE/RMSSE, resíduos (compartilhado)
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
│           ├── pages/           ← Dashboard, ProductDetail, Replenishment, Alerts, Simulation
│           └── components/      ← ForecastChart (diário), ReplenishmentTable, AlertList, UploadPanel, ExportButton
├── specs/
│   └── 001-sistema-previsao-estoque/
│       ├── spec.md              ← especificação funcional (User Stories)
│       ├── plan.md              ← plano técnico e arquitetura
│       └── tasks.md             ← tarefas por fase com TDD
└── docs/                        ← documentação organizada por área (ver docs/README.md)
    ├── project/                 ← projeto técnico (PDF) e estado atual do sistema
    ├── prediction/              ← ADRs de modelagem + plano de experimentos comparativos
    ├── backend/                 ← ADRs de arquitetura de serviço/API
    ├── database/                ← ADRs de persistência
    ├── frontend/                ← ADRs do dashboard React
    └── uml/                     ← diagramas UML (caminho fixo, seção 6.4 do artigo)
```

---

## Regras Invioláveis (Constituição v2.0.0)

Consulte `.specify/memory/constitution.md` para o texto completo. Resumo:

1. **Domínio Puro**: `backend/domain/` NUNCA importa FastAPI, SQLAlchemy ou APScheduler.
2. **Estatística antes de ML**: SARIMAX é o modelo central da camada agregada L1
   (`unidade × categoria`, diário). Croston/TSB/SBA são permitidos no nível de SKU
   (série quase toda zero, SARIMAX inaplicável). NN/boosting só com evidência empírica.
3. **Validação obrigatória**: walk-forward CV (≥4 folds, origem móvel, h=14 dias) +
   `MASE < 1.0` + simulação de perda/ruptura melhor que regra ingênua, antes de `status = "trained"`.
4. **Linguagem do usuário**: mensagens de erro e alertas em PT-BR sem jargão técnico.
5. **Rastreabilidade**: todo upload e retrain gravados em `processing_log` e `retrain_history`;
   geração diária registra data e contagem de SKUs atendidos.
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

# Pipeline ML — camada agregada L1 (unidade × categoria, diário)
TOP_N_PRODUCTS=20               # SKUs com desagregação (L2) e reposição (L3) detalhadas
FORECAST_HORIZON_DAYS=14        # horizonte da previsão e da recomendação de reposição
TEST_DAYS=28                    # hold-out para avaliação
MIN_OBSERVATIONS_DAYS=180       # mínimo de dias por unidade×categoria para treinar L1
SEASONAL_PERIOD=7              # sazonalidade semanal do SARIMAX (m=7)
LOG_CV_THRESHOLD=0.7           # log1p acima deste CV

# Política de reposição (L3)
SAFETY_STOCK_DAYS=2            # estoque de segurança em dias de demanda
SHELF_LIFE_DEFAULT_DAYS=7      # validade usada quando a categoria não tem parâmetro próprio

# Scheduler
RETRAIN_DAY_OF_WEEK=mon        # ajuste (fit) dos modelos L1
RETRAIN_HOUR=2
DAILY_FORECAST_HOUR=3          # geração diária de previsão + reposição a partir do cache
```

---

## Modelo de Dados — Tabelas SQLite

| Tabela | Propósito |
| --- | --- |
| `users` | Usuários com e-mail, hash bcrypt, role (admin/viewer) |
| `products` | Catálogo com `categoria`, `unidade`, `total_sold`, `updated_at` |
| `categories` | Categoria × unidade: `shelf_life_dias`, status e métricas do modelo L1 |
| `model_artifacts` | Ordem, métricas (MASE/RMSSE/cobertura), paths de artefatos, status por `unidade × categoria` |
| `forecasts_cache` | Previsão diária por SKU (regenerada todo dia às 03:00) |
| `replenishment_cache` | Recomendação de reposição por SKU/dia (qtd, cadência, risco de perda/ruptura) |
| `processing_log` | Log de cada upload XLSX (filename, hash, rows) |
| `retrain_history` | Histórico de ajustes semanais dos modelos L1 (trigger, duração, contagens) |

---

## Pipeline Hierárquico — Decisões Técnicas

Ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` para o racional completo.

### L1 — SARIMAX na demanda agregada (`unidade × categoria`, série diária)

| Decisão | Valor | Motivo |
| --- | --- | --- |
| Alvo | qtd diária somada por `unidade × categoria` | série densa (poucos zeros), ao contrário do SKU |
| m (período sazonal) | 7 | sazonalidade semanal (fim de semana vende mais) |
| D (diferenciação sazonal) | 0 | histórico < 3 ciclos anuais; P/Q semanais capturam o padrão |
| d (diferenciação regular) | 0 ou 1 (via ADF) | limitado a 1 para não consumir dados de treino |
| log1p | se CV > 0.7 | estabiliza variância |
| Grid de ordens | p,q ∈ 0..2; P,Q ∈ 0..1; m=7 | balanceia tempo e qualidade |
| Critério de seleção | AIC | ajuste vs. parcimônia |
| Exógenas | dummies/Fourier de dia-da-semana, feriado nacional/municipal, véspera, "dias até data comemorativa" | ponderadas por RF MDI, clip(lower=0.1) |
| Datas comemorativas | Dia das Mães (2º dom. maio), Namorados (12/jun), Finados (2/nov), Natal | exógena "dias até a data", substitui o `alta_temporada` binário |
| Mínimo de observações | 180 dias | abaixo disso: `insufficient_data` para a categoria inteira |
| Hold-out para avaliação | 28 dias | |
| Walk-forward CV | ≥4 folds, origem móvel, horizonte 14 dias | obrigatório antes de `status = "trained"` |

### L2 — Desagregação categoria → SKU

| Decisão | Valor | Motivo |
| --- | --- | --- |
| Método | participação móvel (share das últimas 4–8 semanas) × perfil de dia-da-semana do SKU | evita modelar série quase toda zero por SKU |
| Fallback | SKU com < 28 dias com venda ou < 8 vendas → rateio uniforme da categoria | |

### L3 — Política de reposição

| Decisão | Valor | Motivo |
| --- | --- | --- |
| `shelf_life_dias` | tabela por categoria (flor de corte 4, folhagem 7, arranjo 3, vaso 30, insumo 180) | **a confirmar com a parceira** |
| Cobertura-alvo | `min(shelf_life_dias, FORECAST_HORIZON_DAYS)` | não repor mais do que vende antes de murchar |
| Estoque de segurança | `SAFETY_STOCK_DAYS` dias de demanda prevista | |
| Estoque atual | 0 por padrão (compra "a seco"); campo opcional para contagem manual | floricultura não tem estoque em tempo real |

### Comparação acadêmica (ii)

SARIMAX hierárquico (L1+L2) **×** demanda intermitente por SKU (Croston/TSB/SBA),
ambos diários, mesmos splits de walk-forward. Substitui a antiga comparação "mensal ×
diária" — relatório em `docs/`.

---

## Limiares de Qualidade dos Modelos

| Métrica | Limiar | Status se falhar |
| --- | --- | --- |
| MASE (L1 e SKU) | < 1.0 (bate a naïve sazonal semanal) | `low_confidence` |
| Cobertura empírica do IC 95% | ∈ [90%, 98%] | `low_confidence` |
| Simulação de reposição (perda + ruptura) | melhor que regra ingênua de 7 dias | `low_confidence` |
| Observações mínimas L1 (`unidade × categoria`) | ≥ 180 dias | `insufficient_data` |
| Observações mínimas SKU | ≥ 28 dias com venda ou ≥ 8 vendas | fallback de rateio da categoria |
| Ljung-Box (p-value, resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |
| Shapiro-Wilk (p-value, resíduos L1) | > 0.05 | log de aviso; não bloqueia deploy |

`low_confidence` ≠ falha: previsão/reposição ainda é gerada, mas com aviso visual no dashboard.
MAPE e SMAPE continuam calculados e reportados, mas são **informativos** (instáveis com
contagem baixa) — não classificam. Ljung-Box e Shapiro-Wilk compõem a dimensão de
"diagnóstico de resíduos" (seção 6.5 do artigo) — não bloqueiam o deploy, mas MUST ser
logados por modelo L1 treinado.

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
| `/api/v1/forecast/{produto_cod}` | GET | viewer — previsão diária, `horizon_days` |
| `/api/v1/replenishment/{produto_cod}` | GET | viewer — qtd a repor por dia, risco de perda/ruptura |
| `/api/v1/replenishment/batch` | GET | viewer — reposição dos top N para o dashboard |
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
| `specs/001-sistema-previsao-estoque/tasks.md` | Tarefas organizadas por fase (TDD) |
| `.specify/memory/constitution.md` | 6 princípios governantes (v2.0.0) |
| `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md` | **Espinha da revisão de escopo mensal→diário** — arquitetura L1/L2/L3, validação, shelf-life |
| `docs/README.md` | Índice da documentação por área + convenção de ADRs |
| `docs/prediction/`, `docs/backend/`, `docs/database/`, `docs/frontend/` | ADRs organizados por área (ver `docs/README.md` para a lista completa) |
| `docs/project/Projeto Tecnico Verde Perto Final...pdf` | Projeto técnico acadêmico original (fonte primária, revisado pelo orientador) |
| `docs/project/current_files_state.md` | Raio-x do que já foi feito (dados, pré-processamento, modelagem) vs. requisitos do artigo |
| `docs/prediction/plano_experimentos_modelagem.md` | Plano de experimentos: L1 baseline × enriquecido × demanda intermitente/outros modelos |
| `docs/prediction/01-pre_processing.md` | O que os scripts de `training_scripts/preprocessing/` fazem e por quê (série diária por unidade×categoria; colunas removidas) |
| `docs/uml/` *(parcial — 2 de 5 diagramas)* | Diagramas de casos de uso, atividades, classes, modelo de dados e arquitetura lógica (seção 6.4 do artigo) |
| `docs/eda_report.md` *(a criar)* | Relatório de análise exploratória — sazonalidade, tendências, comportamento por unidade, perfil de demanda |
