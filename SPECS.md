# SPECS — Sistema de Previsão de Estoque (Floricultura)

> Implementação do zero · Monolito Modular · FastAPI + SARIMAX (hierárquico) + React  
> Segurança: JWT (python-jose) + bcrypt · Perfis: admin / viewer · LGPD  
> Frontend: cliente TypeScript gerado de openapi.yaml (openapi-typescript-codegen)  
> Metodologia: ágil/iterativa (software) + CRISP-DM (dados e modelagem)  
> Versão: 2.0 · Data: 2026-08-30 (revisão de escopo: mensal → diário — ver
> `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`)  
> Autores: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Índice

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)  
2. [Decisões de Arquitetura](#2-decisões-de-arquitetura)  
3. [Estrutura de Diretórios](#3-estrutura-de-diretórios)  
4. [Camada de Dados — ETL Pipeline](#4-camada-de-dados--etl-pipeline)  
5. [Camada de Modelos — SARIMAX](#5-camada-de-modelos--sarimax)  
6. [Camada de Aplicação — FastAPI](#6-camada-de-aplicação--fastapi)  
7. [Contratos de API (Endpoints)](#7-contratos-de-api-endpoints)  
8. [Schemas Pydantic](#8-schemas-pydantic)  
9. [Banco de Dados](#9-banco-de-dados)  
10. [Agendamento — Weekly Retrain](#10-agendamento--weekly-retrain)  
11. [Configuração e Variáveis de Ambiente](#11-configuração-e-variáveis-de-ambiente)  
12. [Estratégia de Testes](#12-estratégia-de-testes)  
13. [Mapeamento de Requisitos](#13-mapeamento-de-requisitos)

---

## 1. Visão Geral do Sistema

### 1.1 Problema e Escopo

Sistema de **recomendação de reposição diária** para a Floricultura Verde Perto (unidades
em Nova Lima — Jardim Canadá — e Itabirito/MG), rede com 3 unidades operacionais. A base
cobre Jan/2024–Fev/2026 (324k+ transações, 5.100+ SKUs). O sistema prevê a demanda
**por dia** para os próximos **14 dias** e traduz isso em quanto repor de cada produto,
respeitando a validade (produtos perecíveis — flores de corte duram 3–7 dias).

Modelagem hierárquica (ver `docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`):

- **L1** — SARIMAX na série **diária** agregada por `unidade × categoria` (densa);
- **L2** — desagregação proporcional da previsão da categoria para cada SKU do Top-N;
- **L3** — política de reposição perecível-consciente (shelf-life + estoque de segurança).

### 1.1.1 Metodologia

- **Desenvolvimento de software**: abordagem ágil e iterativa, com entregas parciais
  orientadas a valor (histórias de usuário → implementação → testes → validação com a
  entidade parceira a cada ciclo).
- **Dados e modelagem preditiva**: CRISP-DM (*Cross-Industry Standard Process for Data
  Mining*), adaptado ao contexto de séries temporais — compreensão do negócio,
  compreensão dos dados, preparação dos dados, modelagem, avaliação e implantação.
- **Levantamento de requisitos**: reuniões formais com a entidade parceira (entrevistas
  com responsáveis operacionais + análise dos relatórios financeiros disponíveis),
  priorizados por impacto operacional e estratégico (Tabela 1, seção 13).

### 1.2 Fluxo de Ponta a Ponta

```
[Usuário]
    │
    ├─► Upload XLSX (do sistema financeiro)
    │        │
    │        ▼
    │   [ETL Pipeline]
    │   XLSX → parse → normalize (deriva categoria/unidade) → dedup → contas_a_receber.csv
    │        │
    │        ▼
    │   [L1 — Feature Engineering + SARIMAX]  (por unidade × categoria)
    │   série diária → exógenas de calendário → RF importance → seleção de ordem (AIC, m=7)
    │   → fit → walk-forward CV (h=14) → persist
    │        │
    │        ▼
    │   [Model Registry] (SQLite) — ordem, MASE/RMSSE/cobertura, artefato joblib, status
    │        │
    │        ▼
    │   [L2 — Desagregação]  previsão da categoria → SKU (share móvel × perfil dia-da-semana)
    │        │
    │        ▼
    │   [L3 — Política de reposição]  demanda SKU + shelf-life + estoque de segurança
    │   → qtd a repor / dia, cadência, risco de perda/ruptura → replenishment_cache
    │        │
    │        ▼
    │   [FastAPI]  ←── requisições do React Dashboard
    │   /forecast (diário), /replenishment, /alerts, /simulation, /export, /models/status
    │        │
    │        ▼
    │   [React Dashboard]  gráficos diários · reposição de hoje · alertas · simulações · exportação
    │
    ├─► Scheduler (APScheduler) — segunda 02:00 → reajuste (fit) dos modelos L1
    └─► Scheduler (APScheduler) — todo dia 03:00 → geração de previsão + reposição (do cache)
```

### 1.3 Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend API | FastAPI 0.111 | async, auto-docs OpenAPI, Pydantic nativo |
| ML / Stats | statsmodels 0.14, scikit-learn 1.4 | SARIMAX estabelecido, RF para importância |
| Dados | pandas 2.2, numpy 1.26 | pipeline tabulair |
| EDA / prototipagem | Jupyter Notebooks + matplotlib, seaborn, plotly | análise exploratória (seção 4.2 do artigo); não entram no runtime de produção |
| Banco | SQLite + SQLAlchemy 2.0 | zero infra, adequado para volume |
| Scheduler | APScheduler 3.10 | retrain semanal em-processo |
| Serialização de modelos | joblib | scikit-learn ecosystem |
| Export | openpyxl (Excel), reportlab (PDF) | REQ-10 |
| Frontend | React 18 + Recharts + MUI | existente no app-react/ — decisão pós-prototipagem; o artigo original (seção 6.3) cogitava Streamlit/Dash "a definir" |
| Controle de versão | Git | já em uso |

---

## 2. Decisões de Arquitetura

### 2.1 Clean Architecture em 4 Camadas

```
┌─────────────────────────────────────────────┐
│  Camada de Apresentação (FastAPI Routers)    │  ← HTTP, WebSocket
├─────────────────────────────────────────────┤
│  Camada de Aplicação (Services / Use Cases) │  ← orquestração
├─────────────────────────────────────────────┤
│  Camada de Domínio (Pipeline + Models)      │  ← lógica de negócio pura
├─────────────────────────────────────────────┤
│  Camada de Infraestrutura (DB, FS, Sched.)  │  ← I/O externo
└─────────────────────────────────────────────┘
```

**Regra de dependência**: camadas superiores dependem das inferiores; nunca o inverso. O domínio não importa FastAPI nem SQLAlchemy.

### 2.2 Rationale das Decisões Principais

| Decisão | Alternativa descartada | Motivo |
|---|---|---|
| SARIMAX no L1 (série diária agregada por unidade × categoria) | LSTM, XGBoost por SKU | M4/M5: métodos estatísticos superam ML em séries curtas; a série agregada é densa (~790 pts diários) |
| Granularidade **diária**, arquitetura hierárquica L1→L2→L3 | Previsão mensal por produto | Produtos perecíveis (validade 3–7 dias): a decisão relevante é "quanto repor hoje". A série diária por SKU é >90% zeros → SKU não é modelado sozinho (L2 desagrega). Ver ADR-009 e seção 12.5 |
| Croston/TSB/SBA no nível de SKU | Só L2 | Trilha de comparação (contribuição acadêmica ii); SARIMAX inaplicável a série quase toda zero |
| RF para ponderação de exógenas | Stepwise AIC, Lasso | Reduz multicolinearidade sem viés de seleção (Breiman 2001) |
| SQLite | PostgreSQL | Volume adequado; zero infra; fácil backup |
| APScheduler in-process | Celery+Redis | Não há fila de tarefas; um job semanal não justifica infra adicional |
| joblib para persistência de modelos | pickle nativo | Mais seguro com arrays NumPy grandes |
| React (dashboard) | Streamlit, Dash | Artigo original deixava "a definir após prototipagem" (seção 6.3); app-react/ já existia e cobre requisitos de RNF-01 (usabilidade) com mais controle de UI |

### 2.3 Tratamento de Demanda Intermitente e Séries Curtas

- **L1** (`unidade × categoria`, diário): séries com CV > 0.7 (`std/mean`) recebem
  `log1p` antes do SARIMAX e back-transform `expm1` nas previsões. `unidade × categoria`
  com menos de **180 dias** de histórico são sinalizados como `status = 'insufficient_data'`
  — a categoria inteira fica sem previsão.
- **L2** (SKU): a série diária por SKU é majoritariamente zero e **não** é modelada
  diretamente. A previsão da categoria é rateada por participação móvel (últimas 4–8
  semanas) × perfil de dia-da-semana do SKU. SKU com < 28 dias com venda ou < 8 vendas
  totais cai no rateio uniforme da categoria.
- **Comparação**: modelos de demanda intermitente (Croston/TSB/SBA) são avaliados por
  SKU contra a abordagem hierárquica em `training_scripts/alternative_models/` (seção 12.5).

---

## 3. Estrutura de Diretórios

```
ia-predictor/
│
├── backend/                         # Pacote principal da aplicação
│   ├── __init__.py
│   │
│   ├── main.py                      # Entrypoint FastAPI (cria app, inclui routers, inicia scheduler)
│   ├── config.py                    # Settings via pydantic-settings (lê .env)
│   ├── dependencies.py              # Injeção de dependências FastAPI (get_db, get_model_registry)
│   │
│   ├── api/                         # Camada de apresentação — routers HTTP
│   │   ├── __init__.py
│   │   ├── router_upload.py         # POST /upload
│   │   ├── router_products.py       # GET /products, GET /products/{id}
│   │   ├── router_forecast.py       # GET /forecast/{produto_cod}, GET /forecast/batch  (diário)
│   │   ├── router_replenishment.py  # GET /replenishment/{produto_cod}, GET /replenishment/batch
│   │   ├── router_alerts.py         # GET /alerts
│   │   ├── router_simulation.py     # POST /simulation
│   │   ├── router_reports.py        # GET /reports/export
│   │   ├── router_models.py         # GET /models/status, POST /models/retrain
│   │   └── router_health.py         # GET /health
│   │
│   ├── schemas/                     # Pydantic models (request / response)
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── product.py
│   │   ├── forecast.py              # DailyPoint, ForecastResponse
│   │   ├── replenishment.py         # ReplenishmentDay, ReplenishmentRecommendation
│   │   ├── alert.py
│   │   ├── simulation.py
│   │   ├── report.py
│   │   └── model_status.py
│   │
│   ├── services/                    # Camada de aplicação — casos de uso
│   │   ├── __init__.py
│   │   ├── upload_service.py        # orquestra ETL após upload
│   │   ├── forecast_service.py      # carrega modelo L1 + gera previsão diária (L1 + L2)
│   │   ├── replenishment_service.py # aplica política L3 sobre a previsão do SKU
│   │   ├── alert_service.py         # calcula alertas de pico de demanda / risco de sobra
│   │   ├── simulation_service.py    # aplica delta de promoção sobre previsão
│   │   ├── report_service.py        # gera PDF / Excel
│   │   └── retrain_service.py       # orquestra reajuste semanal dos modelos L1
│   │
│   ├── domain/                      # Camada de domínio — lógica pura (sem I/O)
│   │   ├── __init__.py
│   │   │
│   │   ├── etl/                     # Pipeline de ingestão
│   │   │   ├── __init__.py
│   │   │   ├── parser.py            # XLSX → records (migrado do código existente)
│   │   │   ├── deduplicator.py      # dedup por (doc_numero, produto_cod, emissao, qtdade, vl_total)
│   │   │   └── normalizer.py        # tipos, limpeza, datas; deriva categoria + unidade
│   │   │
│   │   ├── features/                # Engenharia de atributos (L1)
│   │   │   ├── __init__.py
│   │   │   ├── daily_series.py      # prepare_daily_series(df, unidade, categoria) → pd.Series (freq='D')
│   │   │   ├── calendar_exogenous.py # dia-da-semana, feriados, dias-até-data-comemorativa
│   │   │   └── importance.py        # compute_rf_importance(), weight_features()
│   │   │
│   │   ├── models/                  # Modelagem SARIMAX (L1)
│   │   │   ├── __init__.py
│   │   │   ├── stationarity.py      # check_stationarity(), suggest_d()
│   │   │   ├── order_selection.py   # select_sarimax_order() via grid AIC (m=7)
│   │   │   ├── sarimax_trainer.py   # fit_sarimax(), run_category_pipeline()
│   │   │   ├── evaluator.py         # mase(), rmsse(), ic_coverage(), walk_forward_cv(h=14), residual_tests()
│   │   │   └── forecaster.py        # generate_daily_forecast(model, horizon_days) → ForecastResult
│   │   │
│   │   ├── disaggregation/          # L2 — categoria → SKU
│   │   │   ├── __init__.py
│   │   │   └── sku_split.py         # disaggregate(previsao_cat, df_hist, produto_cod)
│   │   │
│   │   └── replenishment/           # L3 — política de reposição
│   │       ├── __init__.py
│   │       ├── policy.py            # recommend(previsao_sku, shelf_life, safety_stock, estoque)
│   │       └── simulation.py        # simulate_policy() — perda + ruptura vs. regra ingênua
│   │
│   └── infrastructure/              # Camada de infraestrutura — I/O
│       ├── __init__.py
│       ├── database/
│       │   ├── __init__.py
│       │   ├── engine.py            # cria engine SQLite + session factory
│       │   ├── models.py            # SQLAlchemy ORM models
│       │   └── migrations.py        # cria tabelas na primeira execução
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── file_manager.py      # leitura/escrita de CSV, pickle de modelos
│       │   └── model_registry.py    # salva/carrega artefatos + metadados no DB
│       └── scheduler/
│           ├── __init__.py
│           ├── weekly_retrain.py    # APScheduler — segunda 02:00: reajuste (fit) dos modelos L1
│           └── daily_generation.py  # APScheduler — todo dia 03:00: previsão diária + reposição
│
├── data/
│   ├── raw/                         # XLSX brutos (upload do usuário)
│   └── processed/
│       ├── contas_a_receber.csv     # base consolidada (sep=";")
│       └── processamento_log.json
│
├── models/                          # Artefatos treinados (joblib) — um por unidade × categoria
│   └── {unidade}__{categoria}/
│       ├── sarimax_result.pkl       # SARIMAXResultsWrapper serializado (L1)
│       ├── importances.pkl          # pd.Series de importâncias RF das exógenas de calendário
│       └── metadata.json            # ordem, MASE/RMSSE/cobertura, shelf_life_dias, data de treino
│
├── results/
│   ├── metrics/                     # CSVs de métricas consolidadas
│   └── plots/                       # Gráficos (opcionais em produção)
│
├── training_scripts/                # Experimentação pré-produção do SARIMAX — roda fora do
│   │                                 # backend, nunca é importado por ele (ver docs/prediction/
│   │                                 # plano_experimentos_modelagem.md)
│   ├── __init__.py
│   ├── preprocessing/                # XLSX bruto → CSV transacional (docs/prediction/
│   │   │                             # 01-pre_processing.md) — parser, dedup, drop de colunas;
│   │   │                             # escreve só em training_scripts/output/
│   │   ├── constants.py
│   │   ├── helpers.py
│   │   ├── parser.py
│   │   ├── build_dataset.py         # Etapa 1 — parsing + dedup entre arquivos + log
│   │   ├── reduce_schema.py         # Etapa 2 — 20 → 9 colunas
│   │   ├── map_taxonomy.py          # Etapa 3 — deriva unidade + categoria
│   │   └── taxonomy/                # tabelas de/para versionadas (unidades.py, categorias.py)
│   ├── eda/                         # Fase 1.1 — sazonalidade semanal, esparsidade por SKU, Top-N
│   ├── baseline/                    # Fase 1 — L1 A0 (SARIMA puro diário) e A1 (SARIMAX + calendário)
│   ├── enriched/                    # Fase 3 — L1 Modelo B (SARIMAX + exógenas externas)
│   ├── replenishment/               # Fase 3–4 — L2 desagregação + L3 política + simulação
│   ├── alternative_models/          # Fase 4 — Croston/TSB/SBA por SKU, ETS, XGBoost, NN global
│   ├── validation/                  # Walk-forward CV (h=14), MASE/RMSSE, resíduos, significância
│   │                                 # (Diebold-Mariano/Wilcoxon) — compartilhado entre fases
│   ├── output/                      # CSV/JSON gerados por preprocessing/ (gitignored)
│   └── results/                     # metrics/ e plots/ da experimentação (staging; distinto
│                                     # do results/ de produção acima — só migra para lá o
│                                     # pipeline vencedor, na Fase 5)
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_normalizer.py
│   │   ├── test_daily_series.py
│   │   ├── test_calendar_exogenous.py
│   │   ├── test_order_selection.py
│   │   ├── test_evaluator.py          # mase, rmsse, ic_coverage, walk_forward(h=14)
│   │   ├── test_forecaster.py
│   │   ├── test_sku_split.py          # L2
│   │   └── test_replenishment_policy.py  # L3
│   ├── integration/
│   │   ├── test_etl_pipeline.py
│   │   ├── test_l1_pipeline.py
│   │   ├── test_replenishment_pipeline.py
│   │   └── test_api_endpoints.py
│   └── fixtures/
│       ├── sample_data.csv          # 50 linhas de dados reais anonimizados
│       └── sample.xlsx              # XLSX mínimo para testes de parser
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 4. Camada de Dados — ETL Pipeline

### 4.1 `domain/etl/parser.py`

**Responsabilidade**: converter XLSX do sistema financeiro em lista de registros normalizados.

```python
# Contrato público
def parse_xlsx(input_path: str | Path) -> tuple[list[dict], list[dict]]:
    """
    Retorna (records, skipped).
    records: lista de dicts com chaves de FIELDS
    skipped: lista de dicts {'line': int, 'reason': str, 'content': str}
    """
```

**Campos extraídos** (19 campos):
```
doc_tipo, doc_numero, pagamento, emissao, operador,
cliente_cod, cliente_nome, empresa, vendedor, obs,
produto_cod, produto_nome, qtdade, vl_unit,
vl_total, vl_desconto, tot_liq, icms_ret, total_liquido_doc
```

**Invariantes**:
- `emissao` é parseado como `dd/mm/yyyy`
- Campos numéricos aceitam vírgula como separador decimal
- Registro é marcado em `skipped` se faltar campo obrigatório (doc_numero, produto_cod, qtdade, emissao)

### 4.2 `domain/etl/normalizer.py`

```python
def normalize_records(records: list[dict]) -> pd.DataFrame:
    """
    - Cast de tipos (emissao → datetime, qtdade/vl_* → float)
    - Strip de strings, upper em produto_cod
    - Remove registros com qtdade <= 0 ou emissao nula
    - Deriva `unidade` (normaliza `empresa`, incl. o "CANAD�" corrompido)
    - Deriva `categoria` do produto (de/para versionado; "Outros" se ausente)
    Retorna DataFrame com dtypes corretos.
    """
```

### 4.3 `domain/etl/deduplicator.py`

```python
def deduplicate(
    new_df: pd.DataFrame,
    existing_csv: str | Path,
    key_fields: tuple[str, ...] = ("doc_numero", "produto_cod", "emissao", "qtdade", "vl_total"),
) -> pd.DataFrame:
    """
    Carrega chaves existentes do CSV, filtra registros novos que já existam
    (dedup só ENTRE arquivos — nunca dentro do mesmo). Ver docs/prediction/01-pre_processing.md §2.
    Retorna apenas registros genuinamente novos.
    """
```

### 4.4 Fluxo de Upload (orquestrado por `services/upload_service.py`)

```
upload_service.process_upload(file_path: Path) -> UploadResult
    │
    ├─ parser.parse_xlsx(file_path)              → (records, skipped)
    ├─ normalizer.normalize_records(records)      → df_new
    ├─ deduplicator.deduplicate(df_new, csv)     → df_unique
    ├─ file_manager.append_to_csv(df_unique)     → rows_added
    ├─ file_manager.log_processing(...)          → atualiza processamento_log.json
    └─ retrain_service.schedule_async_retrain()  → dispara retrain em background (se configurado)
```

**Resultado** retornado ao frontend:
```json
{
  "filename": "contas_jan2026.xlsx",
  "rows_added": 3821,
  "rows_skipped": 12,
  "rows_duplicate": 44,
  "processing_time_seconds": 8.3,
  "retrain_scheduled": true
}
```

---

## 5. Camada de Modelos — Hierárquica (L1 SARIMAX → L2 desagregação → L3 reposição)

### 5.1 `domain/features/daily_series.py` (L1)

```python
def prepare_daily_series(df: pd.DataFrame, unidade: str, categoria: str) -> pd.Series:
    """
    Soma qtdade por dia (freq='D') para o par (unidade, categoria).
    Reindex completo do range (dias sem venda = 0).
    Índice: DatetimeIndex com freq='D'.
    Levanta ValueError se len(series) < MIN_OBSERVATIONS_DAYS (180).
    """

MIN_OBSERVATIONS_DAYS = 180
```

### 5.2 `domain/features/calendar_exogenous.py` (L1)

Exógenas **só de calendário** (todas conhecidas para os dias futuros — sem leakage):

| Grupo | Variável | Descrição |
|---|---|---|
| Dia da semana | `dow_1..dow_6` **ou** `dow_sin/dow_cos` | dummies (baseline segunda) ou termos de Fourier `m=7` |
| Feriado | `feriado` | 1 em feriado nacional ou municipal (Nova Lima / Itabirito) |
| Feriado | `vespera_feriado` | 1 no dia anterior a um feriado |
| Data comemorativa | `dias_ate_maes`, `dias_ate_namorados`, `dias_ate_finados`, `dias_ate_natal` | contagem regressiva (clip em ~21 dias); substitui `alta_temporada` binário |
| Sazonalidade anual | `mes`, `estacao` | aproximação (histórico < 3 ciclos anuais) |

```python
def build_calendar_exogenous(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """DataFrame de exógenas de calendário alinhado a idx (freq='D')."""
```

> Exógenas externas (clima, indicadores) são avaliadas na Fase 3 do plano de
> experimentos; entram aqui se o walk-forward mostrar ganho significativo.

### 5.3 `domain/features/importance.py`

```python
def compute_rf_importance(X_train, y_train, n_estimators=200, random_state=42) -> pd.Series:
    """RandomForestRegressor → importâncias MDI normalizadas (soma=1)."""

def weight_features(X: pd.DataFrame, importances: pd.Series) -> pd.DataFrame:
    """Pondera colunas de X pelas importâncias. clip(lower=0.1) — nunca zera variável."""
```

### 5.4 `domain/models/stationarity.py`

```python
def check_stationarity(ts: pd.Series, alpha: float = 0.05) -> StationarityResult:
    """ADF + KPSS → dataclass com estatísticas e flag is_stationary."""

def suggest_d(ts: pd.Series, max_d: int = 1) -> int:
    """Retorna 0 ou 1 (limita d a 1 para não consumir treino)."""
```

### 5.5 `domain/models/order_selection.py`

```python
def select_sarimax_order(
    ts_train: pd.Series,
    exog_train: pd.DataFrame,
    d: int,
    D: int = 0,          # D=0: histórico < 3 ciclos anuais
    m: int = 7,          # sazonalidade SEMANAL
    p_range: range = range(0, 3),
    q_range: range = range(0, 3),
    P_range: range = range(0, 2),
    Q_range: range = range(0, 2),
    criterion: str = "aic",
) -> tuple[tuple[int,int,int], tuple[int,int,int,int]]:
    """
    Grid search: 3×3×2×2 combinações. Retorna (order, seasonal_order) de menor AIC.
    Falhas individuais silenciadas; se todas falharem, RuntimeError.
    """
```

**Nota D=0, m=7**: a sazonalidade dominante da série diária de varejo é a **semanal**
(fim de semana vende mais). `D=1` semanal amplificaria ruído de alta frequência numa
série de ~790 pontos com apenas ~26 meses. O padrão semanal é capturado por `P, Q` com
`m=7`; a sazonalidade anual, por exógenas de calendário (ADR-004, seção "Revisão").

### 5.6 `domain/models/sarimax_trainer.py`

```python
def fit_sarimax(ts_train, exog_train, order, seasonal_order) -> SARIMAXResultsWrapper:
    """Ajusta e retorna o modelo L1. maxiter=300."""

def run_category_pipeline(
    df: pd.DataFrame,
    unidade: str,
    categoria: str,
    test_days: int = 28,
    horizon_days: int = 14,
    log_cv_threshold: float = 0.7,
) -> CategoryPipelineResult:
    """
    Pipeline L1 completo para um par (unidade, categoria):
    1. prepare_daily_series
    2. build_calendar_exogenous
    3. train/test split (últimos test_days como hold-out)
    4. compute_rf_importance (só treino) → weight_features
    5. suggest_d → select_sarimax_order → fit_sarimax
    6. generate_daily_forecast (test + futuro)
    7. evaluate: mase, rmsse, ic_coverage, walk_forward_cv(h=14), residual_tests
    8. simular política L3 no hold-out vs. regra ingênua de 7 dias
    Retorna CategoryPipelineResult (dataclass).
    """
```

**`CategoryPipelineResult`** (dataclass):
```python
@dataclass
class CategoryPipelineResult:
    unidade: str
    categoria: str
    order: tuple
    seasonal_order: tuple        # (P, D, Q, 7)
    use_log: bool
    metrics: dict                # MASE, RMSSE, IC_coverage_pct, MAE, RMSE, MAPE_% (informativo)
    replenishment_sim: dict      # perda + ruptura da política vs. regra ingênua
    importances: pd.Series
    ts_train: pd.Series
    ts_test: pd.Series
    test_pred: pd.Series
    future_pred: pd.Series       # próximos horizon_days dias
    future_idx: pd.DatetimeIndex
    aic: float
    bic: float
    trained_at: datetime
```

### 5.7 `domain/models/evaluator.py`

```python
def mase(y_true, y_pred, y_train, m: int = 7) -> float:
    """Mean Absolute Scaled Error — denominador = MAE da naïve sazonal semanal no treino."""

def rmsse(y_true, y_pred, y_train, m: int = 7) -> float:
    """Root Mean Squared Scaled Error (usada na M5)."""

def ic_coverage(y_true, lower, upper) -> float:
    """% de observações dentro do intervalo de 95% (esperado 90–98)."""

def walk_forward_cv(df, unidade, categoria, n_splits=4, horizon=14, min_train=150) -> pd.DataFrame:
    """
    Rolling-origin CV, horizonte 14 dias.
    Colunas: fold, train_size, MASE, RMSSE, IC_coverage_pct, MAE, RMSE.
    """

def residual_tests(result: SARIMAXResultsWrapper) -> dict:
    """Ljung-Box (lag=min(14, n//5)) + Shapiro-Wilk → p-values e flags."""
```

**Critérios de aceitação** (constituição v2.0.0, seção 6.5 do artigo):
- `MASE < 1.0` (L1 e no SKU após desagregação)
- cobertura empírica do IC 95% ∈ [90%, 98%]
- simulação de reposição (perda + ruptura) melhor que a regra ingênua "média dos últimos 7 dias"

### 5.8 `domain/models/forecaster.py`

```python
def generate_daily_forecast(
    model_result: SARIMAXResultsWrapper,
    importances: pd.Series,
    horizon_days: int,
    use_log: bool,
    last_date: pd.Timestamp,
) -> ForecastResult:
    """
    Previsão para horizon_days dias. Exógenas de calendário futuras são DETERMINÍSTICAS
    (build_calendar_exogenous sobre o índice futuro). expm1 se use_log=True.
    IC 95% = ±1.96*std.
    """

@dataclass
class ForecastResult:
    dates: list[str]           # ISO 8601, um por dia
    predicted: list[float]
    lower_95: list[float]
    upper_95: list[float]
    horizon_days: int
    generated_at: str

```

### 5.9 `domain/disaggregation/sku_split.py` (L2)

```python
def disaggregate(
    previsao_categoria: pd.Series,     # previsão diária da (unidade, categoria)
    df_hist: pd.DataFrame,             # histórico transacional do SKU e da categoria
    produto_cod: str,
    lookback_weeks: int = 6,
) -> pd.Series:
    """
    previsao_sku[d] = previsao_categoria[d] * share_movel(sku) * ajuste_dow(sku)
      share_movel  = participação do SKU na categoria nas últimas lookback_weeks semanas
      ajuste_dow   = perfil de dia-da-semana do SKU (normalizado, média 1)
    Fallback (SKU com < 28 dias com venda OU < 8 vendas): rateio uniforme
      previsao_sku[d] = previsao_categoria[d] / n_skus_ativos_categoria
    """
```

### 5.10 `domain/replenishment/policy.py` e `simulation.py` (L3)

```python
def recommend(
    previsao_sku: pd.Series,           # demanda diária prevista do SKU (14 dias)
    shelf_life_dias: int,
    safety_stock_days: int = 2,
    current_stock: float = 0.0,
    horizon_days: int = 14,
) -> ReplenishmentResult:
    """
    Para cada dia t:
      cobertura   = min(shelf_life_dias, horizon_days)
      demanda_cob = soma(previsao_sku[t : t+cobertura])
      safety      = safety_stock_days * media(previsao_sku)
      qty[t]      = max(0, demanda_cob + safety - current_stock)
      waste[t]    = max(0, current_stock + qty[t] - soma(previsao_sku[t : t+shelf_life_dias]))
    Deriva: reorder_in_days (cadência), cover_until, stockout_risk_pct, risk_label.
    """

def simulate_policy(hold_out: pd.Series, policy, naive_baseline) -> dict:
    """Roda a política e a regra ingênua sobre o hold-out. Retorna perda e ruptura de cada."""

@dataclass
class ReplenishmentResult:
    days: list[dict]           # {date, forecast_demand, qty_to_order, cover_until, expected_waste, stockout_risk_pct}
    reorder_in_days: int
    risk_label: str            # ok | risco_ruptura | risco_perda
    reason: str                # PT-BR sem jargão
    generated_at: str
```

---

## 6. Camada de Aplicação — FastAPI

### 6.1 `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import (
    router_upload, router_products, router_forecast,
    router_alerts, router_simulation, router_reports,
    router_models, router_health,
)
from backend.infrastructure.database.migrations import create_tables
from backend.infrastructure.scheduler.weekly_retrain import start_scheduler

app = FastAPI(
    title="Floricultura — API de Previsão de Estoque",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    create_tables()
    start_scheduler()

# Prefixo /api/v1 em todos os routers
app.include_router(router_health.router, tags=["health"])
app.include_router(router_upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(router_products.router, prefix="/api/v1", tags=["products"])
app.include_router(router_forecast.router, prefix="/api/v1", tags=["forecast"])
app.include_router(router_replenishment.router, prefix="/api/v1", tags=["replenishment"])
app.include_router(router_alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(router_simulation.router, prefix="/api/v1", tags=["simulation"])
app.include_router(router_reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(router_models.router, prefix="/api/v1", tags=["models"])
```

`startup` também registra os **dois** jobs do APScheduler: `weekly_retrain`
(segunda 02:00) e `daily_generation` (todo dia 03:00).

### 6.2 `backend/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    RESULTS_DIR: str = "results"
    DATABASE_URL: str = "sqlite:///./floricultura.db"
    TOP_N_PRODUCTS: int = 20              # SKUs com desagregação (L2) e reposição (L3) detalhadas
    FORECAST_HORIZON_DAYS: int = 14       # horizonte da previsão e da reposição
    TEST_DAYS: int = 28                   # hold-out para avaliação
    MIN_OBSERVATIONS_DAYS: int = 180      # mínimo de dias por unidade×categoria para treinar L1
    SEASONAL_PERIOD: int = 7             # m — sazonalidade semanal do SARIMAX
    LOG_CV_THRESHOLD: float = 0.7        # limiar para log-transform
    SAFETY_STOCK_DAYS: int = 2           # estoque de segurança (dias de demanda) — L3
    SHELF_LIFE_DEFAULT_DAYS: int = 7     # validade quando a categoria não tem parâmetro próprio
    RETRAIN_DAY_OF_WEEK: str = "mon"     # reajuste (fit) dos modelos L1
    RETRAIN_HOUR: int = 2                # 02:00
    DAILY_FORECAST_HOUR: int = 3         # geração diária de previsão + reposição — 03:00
    MAX_UPLOAD_MB: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 7. Contratos de API (Endpoints)

### 7.0 Segurança — Autenticação JWT

Todos os endpoints `/api/v1/*` exigem `Authorization: Bearer <token>`.  
Endpoints públicos: `GET /health`, `POST /auth/login`.

#### `POST /auth/login`

**Request**:
```json
{ "email": "gestora@floricultura.com", "password": "senha123" }
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "role": "admin",
  "expires_in": 28800
}
```

**Errors**: `401` credenciais inválidas · `422` campos ausentes

---

#### `POST /auth/refresh`

**Request**: `Authorization: Bearer <refresh_token>`  
**Response 200**: `{ "access_token": "eyJ...", "expires_in": 28800 }`

---

#### `GET /auth/me`

**Response 200**:
```json
{ "id": 1, "email": "gestora@floricultura.com", "name": "Ana Gestora", "role": "admin" }
```

---

#### Controle de Perfis por Endpoint

| Endpoint | Perfil mínimo |
| --- | --- |
| `POST /api/v1/upload` | **admin** |
| `POST /api/v1/models/retrain` | **admin** |
| `GET /api/v1/products` | viewer |
| `GET /api/v1/forecast/*` | viewer |
| `GET /api/v1/replenishment/*` | viewer |
| `GET /api/v1/alerts` | viewer |
| `POST /api/v1/simulation` | viewer |
| `GET /api/v1/reports/export` | viewer |
| `GET /api/v1/models/status` | viewer |

Tentativa de acesso acima do perfil retorna `403 Forbidden` com mensagem:  
`{"detail": "Você não tem permissão para esta ação."}`

---

### 7.1 `GET /health`

**Resposta 200**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "scheduler": "running"
}
```

---

### 7.2 `POST /api/v1/upload`

**Request**: `multipart/form-data`
- `file`: arquivo `.xlsx` ou `.xlsm` (max 50 MB)

**Response 200** (`UploadResponse`):
```json
{
  "filename": "contas_jan2026.xlsx",
  "rows_added": 3821,
  "rows_skipped": 12,
  "rows_duplicate": 44,
  "processing_time_seconds": 8.3,
  "retrain_scheduled": true,
  "errors": []
}
```

**Errors**:
- `400` — arquivo não é XLSX
- `413` — arquivo > 50 MB
- `422` — estrutura do XLSX não reconhecida (missing "Documento:")

---

### 7.3 `GET /api/v1/products`

Query params:
- `limit: int = 50`
- `offset: int = 0`
- `sort_by: str = "total_sold"` (total_sold | name | mase)
- `search: str = ""` (busca em produto_cod e produto_nome)
- `model_status: str` (opcional — filtra por status do modelo L1 da categoria)

**Response 200** (`ProductListResponse`):
```json
{
  "total": 5134,
  "items": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "categoria": "Flor de corte",
      "unidade": "Jardim Canadá",
      "total_sold": 128450.0,
      "model_status": "trained",
      "last_mase": 0.82,
      "last_trained_at": "2026-03-02T02:00:00"
    }
  ]
}
```

`model_status` (do modelo L1 da categoria): `"trained"` | `"low_confidence"` | `"insufficient_data"` | `"error"` | `"pending"`

---

### 7.4 `GET /api/v1/products/{produto_cod}`

**Response 200** (`ProductDetailResponse`):
```json
{
  "produto_cod": "147",
  "produto_nome": "ROSA VERMELHA 40CM",
  "categoria": "Flor de corte",
  "unidade": "Jardim Canadá",
  "shelf_life_dias": 4,
  "total_sold": 128450.0,
  "daily_history": [
    {"date": "2026-02-28", "quantity": 41.0},
    {"date": "2026-03-01", "quantity": 58.0}
  ],
  "model_status": "trained",
  "metrics": {
    "MASE": 0.82,
    "RMSSE": 0.79,
    "IC_coverage_pct": 94.1,
    "MAE": 6.4,
    "RMSE": 9.1,
    "MAPE_%": 18.3
  },
  "sarimax_order": "(1,1,1)",
  "seasonal_order": "(1,0,1,7)",
  "use_log_transform": false,
  "last_trained_at": "2026-03-02T02:00:00"
}
```

`daily_history` e `metrics` do produto refletem a série do SKU e o modelo L1 da sua
categoria. Sem dados pessoais de clientes (LGPD).

---

### 7.5 `GET /api/v1/forecast/{produto_cod}`

Query params:
- `horizon_days: int = 14` (1–28)

**Response 200** (`ForecastResponse`):
```json
{
  "produto_cod": "147",
  "produto_nome": "ROSA VERMELHA 40CM",
  "categoria": "Flor de corte",
  "unidade": "Jardim Canadá",
  "horizon_days": 14,
  "forecast": [
    {
      "date": "2026-03-07",
      "predicted": 48.0,
      "lower_95": 31.0,
      "upper_95": 65.0,
      "weekday": "sábado",
      "is_weekend": true,
      "is_holiday": false,
      "commemorative_label": null
    },
    {
      "date": "2026-03-08",
      "predicted": 44.0,
      "lower_95": 28.0,
      "upper_95": 60.0,
      "weekday": "domingo",
      "is_weekend": true,
      "is_holiday": false,
      "commemorative_label": null
    }
  ],
  "generated_at": "2026-03-06T03:00:00",
  "model_trained_at": "2026-03-02T02:00:00"
}
```

**Errors**:
- `404` — produto não encontrado
- `409` — modelo da categoria indisponível (`model_status` ∈ {`insufficient_data`, `error`, `pending`})

---

### 7.6 `GET /api/v1/forecast/batch`

Query params:
- `top_n: int = 10`
- `horizon_days: int = 14`

**Response 200** (`ForecastBatchResponse`):
```json
{
  "horizon_days": 14,
  "generated_at": "2026-03-06T03:00:00",
  "forecasts": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "next_7d_predicted": 260.0,
      "next_7d_lower_95": 205.0,
      "next_7d_upper_95": 315.0,
      "window_start": "2026-03-07"
    }
  ]
}
```

---

### 7.7 `GET /api/v1/replenishment/{produto_cod}`

Query params:
- `horizon_days: int = 14` (1–28)
- `current_stock: float = 0` (estoque atual em unidades; 0 = compra "a seco")

**Modelo (L3)**: para cada dia `t`, `cobertura = min(shelf_life_dias, horizon_days)`;
`qty_to_order[t] = max(0, Σ previsao_sku[t..t+cobertura-1] + safety_stock − current_stock)`;
`expected_waste[t] = max(0, current_stock + qty_to_order[t] − Σ previsao_sku[t..t+shelf_life_dias-1])`.

**Response 200** (`ReplenishmentRecommendation`):
```json
{
  "produto_cod": "147",
  "produto_nome": "ROSA VERMELHA 40CM",
  "categoria": "Flor de corte",
  "unidade": "Jardim Canadá",
  "shelf_life_dias": 4,
  "safety_stock_days": 2,
  "current_stock": 0.0,
  "reorder_in_days": 3,
  "risk_label": "ok",
  "reason": "Validade curta (4 dias) — repor 40 unidades cobre até terça sem sobra.",
  "days": [
    {
      "date": "2026-03-07",
      "forecast_demand": 48.0,
      "qty_to_order": 40.0,
      "cover_until": "2026-03-10",
      "expected_waste": 0.0,
      "stockout_risk_pct": 4.0
    }
  ],
  "generated_at": "2026-03-06T03:00:00"
}
```

**Errors**: `404` produto não encontrado · `409` categoria sem modelo disponível

---

### 7.8 `GET /api/v1/replenishment/batch`

Query params: `top_n: int = 10`

**Response 200** (`ReplenishmentBatchResponse`): "Reposição de Hoje" do dashboard.
```json
{
  "ref_date": "2026-03-06",
  "generated_at": "2026-03-06T03:00:00",
  "items": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "qty_to_order_today": 40.0,
      "cover_until": "2026-03-10",
      "reorder_in_days": 3,
      "risk_label": "ok"
    }
  ]
}
```

---

### 7.9 `GET /api/v1/alerts`

Query params:
- `limit: int = 50`
- `severity: str = "all"` (all | high | medium)

**Lógica de alerta**:
- `pico_demanda` — SKU cuja soma da previsão dos **próximos 7 dias** está **≥ 20% acima**
  da média das **últimas 4 semanas**. `high` se ≥ 30%, `medium` entre 20–30%.
- `risco_sobra` — SKU de validade curta (`shelf_life_dias` baixo) com previsão em queda,
  onde `expected_waste` da política L3 é relevante.

**Response 200** (`AlertListResponse`):
```json
{
  "generated_at": "2026-03-06T03:00:00",
  "total_alerts": 7,
  "items": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "kind": "pico_demanda",
      "severity": "high",
      "reason": "Previsão dos próximos 7 dias (260 un) é 38% acima da média das últimas 4 semanas (188 un). Pico esperado no sábado (Dia das Mães).",
      "predicted_next_7d": 260.0,
      "recent_avg_4w": 188.0,
      "variation_pct": 38.2,
      "peak_date": "2026-05-09",
      "alert_window_start": "2026-03-07"
    }
  ]
}
```

---

### 7.10 `POST /api/v1/simulation`

**Request** (`SimulationRequest`):
```json
{
  "produto_cod": "147",
  "horizon_days": 14,
  "scenarios": [
    {
      "label": "Promoção 15%",
      "discount_pct": 15.0,
      "apply_dates": ["2026-05-07", "2026-05-08", "2026-05-09"]
    },
    {
      "label": "Venda casada com produto 150",
      "bundle_product_cod": "150",
      "expected_uplift_pct": 10.0,
      "apply_dates": ["2026-05-08", "2026-05-09"]
    }
  ]
}
```

**Modelo de simulação**: multiplicador sobre a previsão **diária** base (L1+L2). O delta de
desconto usa o coeficiente de preço/desconto do modelo L1 da categoria, escalado pelo
percentual; venda casada aplica `(1 + expected_uplift_pct/100)`. A reposição (L3) é
recalculada sobre a previsão simulada.

**Response 200** (`SimulationResponse`):
```json
{
  "produto_cod": "147",
  "base_forecast": [
    {"date": "2026-05-08", "predicted": 52.0}
  ],
  "scenarios": [
    {
      "label": "Promoção 15%",
      "forecast": [
        {"date": "2026-05-08", "predicted": 61.0, "delta": 9.0, "delta_pct": 17.3}
      ]
    }
  ]
}
```

---

### 7.11 `GET /api/v1/reports/export`

Query params:
- `format: str` — `"excel"` | `"pdf"`
- `top_n: int = 10`
- `horizon_days: int = 14`

**Response 200**: arquivo binário com header `Content-Disposition: attachment`

**Conteúdo do Excel**:
- Aba "Reposição": qtd a repor por produto/dia, cobre-até, cadência, risco
- Aba "Previsão diária": previsão + IC 95% por produto/dia
- Aba "Métricas": MASE, RMSSE, cobertura do IC por `unidade × categoria`
- Aba "Alertas": lista de alertas gerados

**Conteúdo do PDF**:
- Cabeçalho com data de geração
- Tabela de reposição (top N produtos, próximos 14 dias)
- Lista de alertas
- Rodapé com disclaimer de confiabilidade

---

### 7.12 `GET /api/v1/models/status`

**Response 200** (`ModelStatusResponse`) — contagens por `unidade × categoria`:
```json
{
  "last_retrain_at": "2026-03-02T02:00:00",
  "next_retrain_at": "2026-03-09T02:00:00",
  "last_daily_generation_at": "2026-03-06T03:00:00",
  "skus_covered": 20,
  "total_categories": 24,
  "trained_categories": 19,
  "low_confidence_categories": 3,
  "failed_categories": 0,
  "insufficient_data_categories": 2,
  "is_training": false,
  "training_progress_pct": null
}
```

---

### 7.13 `POST /api/v1/models/retrain`

Dispara reajuste manual dos modelos L1 (assíncrono). Máximo 1 reajuste em execução por vez.

**Request**: corpo vazio

**Response 202**:
```json
{
  "message": "Atualização dos modelos iniciada em segundo plano.",
  "started_at": "2026-03-06T15:00:00"
}
```

**Errors**:
- `409` — reajuste já em execução

---

## 8. Schemas Pydantic

```python
# backend/schemas/forecast.py
from pydantic import BaseModel
from typing import Optional

class DailyPoint(BaseModel):
    date: str
    quantity: float

class ForecastPoint(BaseModel):
    date: str
    predicted: float
    lower_95: float
    upper_95: float
    weekday: str
    is_weekend: bool
    is_holiday: bool
    commemorative_label: Optional[str] = None

class ForecastResponse(BaseModel):
    produto_cod: str
    produto_nome: str
    categoria: str
    unidade: str
    horizon_days: int
    forecast: list[ForecastPoint]
    generated_at: str
    model_trained_at: str

# backend/schemas/replenishment.py
class ReplenishmentDay(BaseModel):
    date: str
    forecast_demand: float
    qty_to_order: float
    cover_until: str
    expected_waste: float
    stockout_risk_pct: float

class ReplenishmentRecommendation(BaseModel):
    produto_cod: str
    produto_nome: str
    categoria: str
    unidade: str
    shelf_life_dias: int
    safety_stock_days: int
    current_stock: float
    reorder_in_days: int
    risk_label: str           # ok | risco_ruptura | risco_perda
    reason: str
    days: list[ReplenishmentDay]
    generated_at: str

# backend/schemas/product.py
class ProductSummary(BaseModel):
    produto_cod: str
    produto_nome: str
    categoria: str
    unidade: str
    total_sold: float
    model_status: str   # trained | low_confidence | insufficient_data | error | pending
    last_mase: Optional[float]
    last_trained_at: Optional[str]

class ProductListResponse(BaseModel):
    total: int
    items: list[ProductSummary]

# backend/schemas/alert.py
class AlertItem(BaseModel):
    produto_cod: str
    produto_nome: str
    kind: str           # pico_demanda | risco_sobra
    severity: str       # high | medium
    reason: str
    predicted_next_7d: float
    recent_avg_4w: float
    variation_pct: float
    peak_date: Optional[str] = None
    alert_window_start: str

class AlertListResponse(BaseModel):
    generated_at: str
    total_alerts: int
    items: list[AlertItem]

# backend/schemas/simulation.py
class SimulationScenario(BaseModel):
    label: str
    discount_pct: Optional[float] = None
    bundle_product_cod: Optional[str] = None
    expected_uplift_pct: Optional[float] = None
    apply_dates: list[str]

class SimulationRequest(BaseModel):
    produto_cod: str
    horizon_days: int = 14
    scenarios: list[SimulationScenario]

class SimulationForecastPoint(BaseModel):
    date: str
    predicted: float
    delta: float
    delta_pct: float

class SimulationScenarioResult(BaseModel):
    label: str
    forecast: list[SimulationForecastPoint]

class SimulationResponse(BaseModel):
    produto_cod: str
    base_forecast: list[dict]
    scenarios: list[SimulationScenarioResult]

# backend/schemas/upload.py
class UploadResponse(BaseModel):
    filename: str
    rows_added: int
    rows_skipped: int
    rows_duplicate: int
    processing_time_seconds: float
    retrain_scheduled: bool
    errors: list[str]

# backend/schemas/model_status.py
class ModelStatusResponse(BaseModel):
    last_retrain_at: Optional[str]
    next_retrain_at: Optional[str]
    last_daily_generation_at: Optional[str]
    skus_covered: int
    total_categories: int
    trained_categories: int
    low_confidence_categories: int
    failed_categories: int
    insufficient_data_categories: int
    is_training: bool
    training_progress_pct: Optional[float]
```

---

## 9. Banco de Dados

### 9.1 SQLAlchemy ORM Models (`infrastructure/database/models.py`)

```python
# Tabela: products
class Product(Base):
    __tablename__ = "products"
    produto_cod     = Column(String, primary_key=True)
    produto_nome    = Column(String)
    categoria       = Column(String, index=True)
    unidade         = Column(String, index=True)
    total_sold      = Column(Float)   # atualizado após cada ETL
    updated_at      = Column(DateTime, default=func.now())

# Tabela: categories  (unidade × categoria — unidade de modelagem L1)
class Category(Base):
    __tablename__ = "categories"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    unidade           = Column(String, index=True)
    categoria         = Column(String, index=True)
    shelf_life_dias   = Column(Integer)     # validade (default por config até a parceira confirmar)
    model_status      = Column(String)      # trained | low_confidence | insufficient_data | error | pending
    mase              = Column(Float)
    rmsse             = Column(Float)
    ic_coverage_pct   = Column(Float)
    observations_days = Column(Integer)
    trained_at        = Column(DateTime)

# Tabela: model_artifacts  (um por categoria)
class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    category_id     = Column(Integer, ForeignKey("categories.id"), index=True)
    status          = Column(String)    # trained | low_confidence | insufficient_data | error | training
    sarimax_order   = Column(String)    # e.g. "(1,1,1)"
    seasonal_order  = Column(String)    # e.g. "(1,0,1,7)"
    use_log         = Column(Boolean, default=False)
    artifact_path   = Column(String)
    importance_path = Column(String)
    mase            = Column(Float)
    rmsse           = Column(Float)
    ic_coverage_pct = Column(Float)
    aic             = Column(Float)
    bic             = Column(Float)
    error_message   = Column(String, nullable=True)
    trained_at      = Column(DateTime)
    observations_days = Column(Integer)  # dias no treino

# Tabela: forecasts_cache  (previsão diária por SKU — regenerada todo dia)
class ForecastCache(Base):
    __tablename__ = "forecasts_cache"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod     = Column(String, ForeignKey("products.produto_cod"), index=True)
    forecast_date   = Column(String)    # "2026-03-07"
    predicted       = Column(Float)
    lower_95        = Column(Float)
    upper_95        = Column(Float)
    generated_at    = Column(DateTime)
    model_id        = Column(Integer, ForeignKey("model_artifacts.id"))

# Tabela: replenishment_cache  (recomendação por SKU/dia)
class ReplenishmentCache(Base):
    __tablename__ = "replenishment_cache"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod       = Column(String, ForeignKey("products.produto_cod"), index=True)
    ref_date          = Column(String)  # dia da recomendação
    qty_to_order      = Column(Float)
    cover_until       = Column(String)
    reorder_in_days   = Column(Integer)
    expected_waste    = Column(Float)
    stockout_risk_pct = Column(Float)
    risk_label        = Column(String)  # ok | risco_ruptura | risco_perda
    generated_at      = Column(DateTime)

# Tabela: processing_log
class ProcessingLog(Base):
    __tablename__ = "processing_log"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    filename        = Column(String)
    file_hash       = Column(String)
    rows_added      = Column(Integer)
    rows_skipped    = Column(Integer)
    rows_duplicate  = Column(Integer)
    processed_at    = Column(DateTime, default=func.now())

# Tabela: retrain_history  (reajuste semanal dos modelos L1)
class RetrainHistory(Base):
    __tablename__ = "retrain_history"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    started_at         = Column(DateTime)
    finished_at        = Column(DateTime, nullable=True)
    trigger            = Column(String)    # "scheduled" | "manual"
    categories_trained = Column(Integer)
    categories_failed  = Column(Integer)
    status             = Column(String)    # running | completed | failed
```

### 9.2 `infrastructure/storage/model_registry.py`

```python
class ModelRegistry:
    def save_artifact(self, result: CategoryPipelineResult) -> ModelArtifact:
        """Serializa model_result e importances com joblib, salva paths + métricas no DB."""

    def load_artifact(self, unidade: str, categoria: str) -> tuple[SARIMAXResultsWrapper, pd.Series, ModelArtifact]:
        """Carrega pkl e retorna (model_result, importances, metadata)."""

    def get_status(self, unidade: str, categoria: str) -> str:
        """Status do modelo L1 mais recente para a categoria."""

    def list_trained_categories(self) -> list[tuple[str, str]]:
        """Pares (unidade, categoria) com status ∈ {'trained', 'low_confidence'}."""

    def mark_training(self, unidade: str, categoria: str) -> None: ...
    def mark_error(self, unidade: str, categoria: str, error: str) -> None: ...
```

---

## 10. Agendamento — Reajuste Semanal + Geração Diária

### 10.1 `infrastructure/scheduler/weekly_retrain.py` + `daily_generation.py`

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.services.retrain_service import RetrainService
from backend.services.forecast_service import ForecastService
from backend.services.replenishment_service import ReplenishmentService

_scheduler = BackgroundScheduler()

def start_scheduler():
    _scheduler.add_job(
        func=lambda: RetrainService().run_full_retrain(trigger="scheduled"),
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0),
        id="weekly_retrain", replace_existing=True, misfire_grace_time=3600,
    )
    _scheduler.add_job(
        func=_run_daily_generation,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_generation", replace_existing=True, misfire_grace_time=3600,
    )
    _scheduler.start()

def _run_daily_generation():
    # para cada SKU do Top-N: L1 forecast (cache) → L2 desagregação → L3 reposição
    ForecastService().regenerate_all()      # popula forecasts_cache
    ReplenishmentService().regenerate_all()  # popula replenishment_cache
```

### 10.2 `services/retrain_service.py`

```python
class RetrainService:
    def run_full_retrain(self, trigger: str = "manual") -> RetrainSummary:
        """
        1. Carrega contas_a_receber.csv completo
        2. Agrupa por (unidade, categoria)
        3. Para cada par:
           a. run_category_pipeline()          # L1 fit + walk-forward + simulação L3
           b. model_registry.save_artifact()
        4. Invalida forecasts_cache + replenishment_cache
        5. Registra RetrainHistory no DB
        Exceções por categoria são capturadas e logadas; não abortam o pipeline.
        """
```

**`RetrainSummary`**:
```python
@dataclass
class RetrainSummary:
    started_at: datetime
    finished_at: datetime
    trigger: str
    categories_trained: int
    categories_failed: int
    categories_insufficient: int
    errors: list[dict]   # {unidade, categoria, error_message}
```

---

## 11. Configuração e Variáveis de Ambiente

**`.env.example`**:
```env
# Diretórios
DATA_DIR=data
MODELS_DIR=models
RESULTS_DIR=results

# Banco
DATABASE_URL=sqlite:///./floricultura.db

# Pipeline (L1 — unidade × categoria, diário)
TOP_N_PRODUCTS=20
FORECAST_HORIZON_DAYS=14
TEST_DAYS=28
MIN_OBSERVATIONS_DAYS=180
SEASONAL_PERIOD=7
LOG_CV_THRESHOLD=0.7
MAX_UPLOAD_MB=50

# Política de reposição (L3)
SAFETY_STOCK_DAYS=2
SHELF_LIFE_DEFAULT_DAYS=7

# Scheduler
RETRAIN_DAY_OF_WEEK=mon
RETRAIN_HOUR=2
DAILY_FORECAST_HOUR=3
```

**`requirements.txt`** (backend, do zero):
```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pydantic-settings==2.2.1
sqlalchemy==2.0.30
pandas==2.2.2
numpy==1.26.4
statsmodels==0.14.2
scikit-learn==1.4.2
scipy==1.13.0
openpyxl==3.1.3
joblib==1.4.2
apscheduler==3.10.4
reportlab==4.2.0
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

**Frontend — geração do cliente TypeScript**:

```bash
# Instalar gerador (uma vez, no diretório app-react/)
npm install --save-dev @openapitools/openapi-generator-cli

# Adicionar ao package.json scripts:
# "generate:api": "openapi-generator-cli generate -i ../ia-predictor/openapi.yaml -g typescript-fetch -o src/services/api --additional-properties=supportsES6=true"

# Rodar sempre que openapi.yaml mudar:
npm run generate:api
```

O cliente gerado em `app-react/src/services/api/` expõe:

```typescript
// Exemplo de uso no React
import { AuthApi, ForecastApi, Configuration } from '../services/api'

const config = new Configuration({ accessToken: localStorage.getItem('token') ?? '' })
const forecastApi = new ForecastApi(config)

const result = await forecastApi.getForecast({ produtoCod: '147', horizonDays: 14 })
```

Qualquer mudança nos schemas do backend quebra o build TypeScript — erros de contrato detectados em compile time, não em runtime.

---

## 12. Estratégia de Testes

### 12.1 Testes Unitários (pytest)

| Arquivo | Cobertura |
|---|---|
| `test_parser.py` | parse_xlsx com fixture de XLSX mínimo; estrutura de records; campos obrigatórios |
| `test_normalizer.py` | cast de tipos; qtdade<=0 removida; deriva categoria/unidade |
| `test_deduplicator.py` | dedup por (doc_numero, produto_cod, emissao, qtdade, vl_total) só entre arquivos |
| `test_daily_series.py` | reindex diário completo (dias sem venda = 0); erro com <180 dias |
| `test_calendar_exogenous.py` | dummies de dia-da-semana; flag de feriado; "dias até Dia das Mães" |
| `test_importance.py` | importâncias somam 1; weight_features respeita clip(0.1) |
| `test_stationarity.py` | suggest_d retorna 0 para série estacionária |
| `test_order_selection.py` | grid m=7; tupla válida; tolera falhas individuais |
| `test_evaluator.py` | mase/rmsse/ic_coverage com arrays conhecidos; walk_forward_cv(h=14, n_splits=2) |
| `test_forecaster.py` | ForecastResult com 14 datas; back-transform expm1 quando use_log |
| `test_sku_split.py` | shares somam 1 na categoria; fallback uniforme para SKU de baixo giro |
| `test_replenishment_policy.py` | qty=0 quando estoque cobre; cobertura limitada por shelf_life; waste cresce com validade curta |
| `test_alert_service.py` | severity=high se variação 7d > 30%; medium 20–30%; flag risco_sobra |
| `test_simulation_service.py` | delta = 0 sem cenários; multiplicador correto; reposição recalculada |

### 12.2 Testes de Integração

| Arquivo | Cobertura |
|---|---|
| `test_etl_pipeline.py` | upload_service.process_upload com XLSX real (fixture) → CSV atualizado |
| `test_l1_pipeline.py` | run_category_pipeline(unidade, categoria) da fixture → result com todas as chaves |
| `test_replenishment_pipeline.py` | categoria treinada → previsão por SKU (L2) → recomendação por SKU/dia (L3) |
| `test_api_endpoints.py` | TestClient FastAPI: /health, /upload, /products, /forecast/{id}, /replenishment/{id}, /alerts |

### 12.3 Validação Estatística (critérios formais do artigo, seção 6.5)

A validação do sistema segue as **três dimensões** definidas na seção 6.5 do artigo:

1. **Validação estatística dos modelos** — MASE, RMSSE, cobertura do IC 95% em hold-out
   (28 dias) e walk-forward CV (≥ 4 folds, origem móvel, horizonte 14 dias). Limiar:
   `MASE < 1.0` (L1 e SKU). Métrica de negócio: simulação de **perda + ruptura** da
   política L3 vs. regra ingênua de 7 dias. MAPE/SMAPE são calculados mas informativos.
2. **Testes de diagnóstico de resíduos** — Ljung-Box (ausência de autocorrelação) e
   Shapiro-Wilk (normalidade) nos resíduos dos modelos L1.
3. **Testes funcionais do sistema** — upload, processamento, visualização e exportação
   com dados reais da entidade parceira; consistência, desempenho e usabilidade com
   usuários não técnicos.

```python
# tests/integration/test_model_quality.py
def test_mase_abaixo_de_1_categorias_alto_giro():
    """MASE < 1.0 nas unidade × categoria de maior volume (constituição v2.0.0)"""
    ...

def test_cobertura_ic_95():
    """Cobertura empírica do intervalo de 95% ∈ [90%, 98%]"""
    ...

def test_politica_reposicao_bate_ingenua():
    """Perda + ruptura da política L3 < regra 'média dos últimos 7 dias' no hold-out"""
    ...

def test_residuos_ljung_box_e_shapiro():
    """p-values > 0.05 (log de aviso; não bloqueia deploy)"""
    ...
```

### 12.4 Ferramentas de Modelagem — Diagramas UML (seção 6.4 do artigo)

Entregável acadêmico obrigatório, produzido com ferramenta de modelagem UML compatível
com os padrões acadêmicos exigidos e versionado em `docs/uml/`:

| Diagrama | Cobertura |
|---|---|
| Casos de uso | Atores (admin, viewer) × funcionalidades (upload, forecast diário, reposição, alertas, simulação, export) |
| Atividades | Fluxo ETL → L1 (features + SARIMAX) → reajuste semanal; fluxo de geração diária L1→L2→L3 |
| Classes | Entidades de domínio (Produto, Categoria, Transação, Modelo, Previsão, Reposição, Alerta) e suas relações |
| Modelo de dados | Diagrama ER das tabelas SQLite (seção 9.1) |
| Arquitetura lógica | As 4 camadas da Clean Architecture (seção 2.1) |

### 12.5 Avaliação Comparativa — SARIMAX Hierárquico vs. Demanda Intermitente por SKU

Contribuição acadêmica (ii) do artigo: comparação formal, via walk-forward CV (origem
móvel, horizonte 14 dias, **mesmos splits**), entre duas arquiteturas **diárias** para
um catálogo perecível de cauda longa:

- **A — SARIMAX hierárquico**: L1 (SARIMAX por `unidade × categoria`) + L2 (desagregação
  proporcional para SKU);
- **B — Demanda intermitente por SKU**: Croston / TSB / SBA direto na série diária do SKU.

Métricas lado a lado: MASE e RMSSE no nível de SKU + a simulação de reposição (perda +
ruptura) de cada abordagem. Relatório em
`docs/prediction/comparacao_hierarquico_vs_intermitente.md`. Substitui a antiga comparação
"mensal × diária" (a granularidade diária deixou de ser hipótese e passou a ser a decisão
de produção — ver ADR-009).

---

## 13. Mapeamento de Requisitos

| Código | Requisito (artigo) | Implementação |
|---|---|---|
| REQ-01 | Upload de planilhas XLSX | `POST /api/v1/upload` + `upload_service.py` |
| REQ-02 | Previsão de curto prazo p/ reposição | `GET /api/v1/forecast/{id}` (diário, `horizon_days=14`) + `GET /api/v1/replenishment/{id}` |
| REQ-03 | Atualização automática | APScheduler: reajuste L1 segunda 02:00; geração diária 03:00 |
| REQ-04 | Indicadores de desempenho para não-técnicos | `GET /api/v1/models/status` + métricas (MASE→"precisão") em `/products/{id}` |
| REQ-05 | Gráficos de tendência | `daily_history` em `/products/{id}` + `forecast` diário (dados para Recharts) |
| REQ-06 | Produtos mais vendidos em períodos especiais | exógena "dias até data comemorativa" no L1; `GET /products?sort_by=total_sold` |
| REQ-07 | Produtos comprados juntos | `GET /api/v1/products/{id}/bundles` *(fase 2 — market basket analysis)* |
| REQ-08 | Simulação de promoções e vendas casadas | `POST /api/v1/simulation` |
| REQ-09 | Alertas de reposição | `GET /api/v1/alerts` (pico de demanda / risco de sobra) |
| REQ-10 | Exportação PDF e Excel | `GET /api/v1/reports/export?format=pdf|excel` |
| REQ-11 | Dashboard centralizado | React app-react/ consome todos os endpoints acima |
| REQ-12 | Documentação funcional e técnica | Este documento + OpenAPI `/docs` gerado automaticamente |
| RNF-01 | Usabilidade para não-técnicos | Mensagens de erro em PT-BR; UI sem jargão técnico |
| RNF-02 | Rastreabilidade e logs | `processing_log` + `retrain_history` no DB; log da geração diária |
| RNF-03 | Reajuste < 2h; geração diária < 15min | ~15–40 pares unidade × categoria; grid m=7 |
| RNF-04 | Segurança e LGPD | JWT + perfis admin/viewer + bcrypt (P1 — seção 7.0) |
| RNF-05 | Manutenibilidade | Clean Architecture; sem lógica no router; domínio sem I/O |

---

## Ordem de Implementação Recomendada

Alinhada ao cronograma oficial do projeto técnico (Tabela 2, seção 8 do artigo):

| Etapa (artigo) | Período | Entrega |
|---|---|---|
| Levantamento e refinamento de requisitos | Abr/2026 | Backlog consolidado — `spec.md` |
| Modelagem e arquitetura do sistema | Mai/2026 | Diagramas UML + modelo de dados (`docs/uml/`) |
| Implementação do pipeline de ingestão | Jun/2026 | ETL inicial |
| Engenharia de atributos e análise exploratória | Jun/2026 | Features + relatório de EDA (`docs/eda_report.md`) |
| Modelagem preditiva SARIMAX | Jul–Ago/2026 | Modelos treinados, avaliados e documentados |
| Dashboard e módulo de simulações | Set/2026 | Interface funcional e validada |
| Testes integrados e ajustes finais | Out/2026 | Versão candidata à entrega |
| Documentação final e entrega | Nov/2026 | Projeto finalizado e documentado |

```
Sprint 0 (Mai/2026 — Modelagem e EDA):
  0a. docs/uml/ — casos de uso, atividades, classes, modelo de dados, arquitetura lógica
  0b. Análise exploratória em Jupyter Notebook (sazonalidade, tendências, unidade, perfil de demanda)
      → consolidar em docs/eda_report.md

Sprint 1 (Jun/2026):
  1. backend/config.py + backend/main.py (esqueleto)
  2. infrastructure/database/ (engine + models + migrations)
  3. domain/etl/ (parser + normalizer + deduplicator)
  4. services/upload_service.py
  5. api/router_upload.py + api/router_health.py
  6. tests/unit/test_parser + test_normalizer
  7. tests/integration/test_etl_pipeline

Sprint 2 (Jul/2026):
  8. domain/features/ (daily_series + calendar_exogenous + importance)
  9. domain/models/ L1 (stationarity + order_selection + sarimax_trainer + evaluator + forecaster)
  10. domain/disaggregation/ (L2) + domain/replenishment/ (L3, com simulação)
  11. infrastructure/storage/model_registry.py + services/retrain_service.py
  12. tests/unit/test_*model* + test_evaluator (mase/rmsse) + test_replenishment_policy

Sprint 3 (Ago/2026):
  13. api/router_products + router_forecast + router_replenishment + router_alerts
  14. services/forecast_service (L1+L2) + replenishment_service (L3) + alert_service
  15. infrastructure/scheduler/weekly_retrain.py + daily_generation.py
  16. tests/integration/test_api_endpoints
  17. Comparação SARIMAX hierárquico × demanda intermitente (seção 12.5) — relatório

Sprint 4 (Set/2026):
  18. api/router_simulation + services/simulation_service
  19. api/router_reports + services/report_service (Excel + PDF)
  20. api/router_models (status + manual retrain)
  21. Integração com React (app-react/) — inclui página "Reposição de Hoje"

Sprint 5 (Out/2026 — Testes integrados):
  22. Testes funcionais com usuários da empresa parceira (percurso guiado das User Stories)
  23. Ajustes finais → versão candidata à entrega

Sprint 6 (Nov/2026 — Documentação final):
  24. docs/quickstart.md + documentação técnica consolidada
  25. Entrega final
```

---

*Documento gerado em 2026-07-28; revisado em 2026-08-30 (escopo mensal → diário, ver
`docs/prediction/ADR-009-granularidade-diaria-e-reposicao.md`). Baseado no artigo TCC,
código existente em `ia-predictor/` e requisitos validados com a entidade parceira.*
