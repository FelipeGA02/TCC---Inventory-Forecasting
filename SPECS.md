# SPECS — Sistema de Previsão de Estoque (Floricultura)

> Implementação do zero · Monolito Modular · FastAPI + SARIMAX + React  
> Segurança: JWT (python-jose) + bcrypt · Perfis: admin / viewer · LGPD  
> Frontend: cliente TypeScript gerado de openapi.yaml (openapi-typescript-codegen)  
> Metodologia: ágil/iterativa (software) + CRISP-DM (dados e modelagem)  
> Versão: 1.2 · Data: 2026-08-21  
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

Sistema de previsão de demanda para a Floricultura Verde Perto (unidades em Nova Lima —
Jardim Canadá — e Itabirito/MG), rede com 3 unidades operacionais. A base de dados cobre
Jan/2024–Fev/2026 (324k+ transações, 5.100+ SKUs). O horizonte de previsão é de **2 a 3
semanas** (operacionalmente mapeado para granularidade mensal com previsão de 1–3 meses
à frente), alinhado ao ciclo de reposição da empresa.

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
    ├─► Upload XLSX (mensal, do sistema financeiro)
    │        │
    │        ▼
    │   [ETL Pipeline]
    │   XLSX → parse → dedup → contas_a_receber.csv
    │        │
    │        ▼
    │   [Feature Engineering]
    │   CSV → séries mensais + variáveis exógenas
    │        │
    │        ▼
    │   [SARIMAX Pipeline]
    │   RF importance → ponderação → seleção de ordem (AIC) → fit → persist
    │        │
    │        ▼
    │   [Model Registry] (SQLite)
    │   salva: ordem, métricas, artefato pickle, status
    │        │
    │        ▼
    │   [FastAPI]  ←── requisições do React Dashboard
    │   /forecast, /alerts, /simulation, /export, /metrics
    │        │
    │        ▼
    │   [React Dashboard]
    │   gráficos · alertas · simulações · exportação
    │
    └─► Scheduler (APScheduler)
        toda segunda-feira 02:00 → retrain automático
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
| SARIMAX como modelo central | LSTM, XGBoost | M4 Competition: ARIMA supera ML com N<50 por sazonalidade. 26 meses = ~26 obs mensais |
| Granularidade mensal (produção) | Diária | Ciclo de reposição é semanal/mensal; dados diários têm >70% de zeros por produto — resultado obtido justamente pela avaliação comparativa exigida como contribuição acadêmica (ii); ver seção 12.5 |
| RF para ponderação de exógenas | Stepwise AIC, Lasso | Reduz multicolinearidade sem viés de seleção (Breiman 2001) |
| SQLite | PostgreSQL | Volume adequado; zero infra; fácil backup |
| APScheduler in-process | Celery+Redis | Não há fila de tarefas; um job semanal não justifica infra adicional |
| joblib para persistência de modelos | pickle nativo | Mais seguro com arrays NumPy grandes |
| React (dashboard) | Streamlit, Dash | Artigo original deixava "a definir após prototipagem" (seção 6.3); app-react/ já existia e cobre requisitos de RNF-01 (usabilidade) com mais controle de UI |

### 2.3 Tratamento de Produtos com Demanda Intermitente

Produtos com CV > 0.7 (`std/mean > 0.7`) recebem transformação `log1p` antes do SARIMAX e back-transform `expm1` nas previsões. Produtos com menos de 15 observações mensais são **excluídos** do pipeline automático e sinalizados no banco como `status = 'insufficient_data'`.

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
│   │   ├── router_forecast.py       # GET /forecast/{product_id}, GET /forecast/batch
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
│   │   ├── forecast.py
│   │   ├── alert.py
│   │   ├── simulation.py
│   │   ├── report.py
│   │   └── model_status.py
│   │
│   ├── services/                    # Camada de aplicação — casos de uso
│   │   ├── __init__.py
│   │   ├── upload_service.py        # orquestra ETL após upload
│   │   ├── forecast_service.py      # carrega modelo + gera previsão
│   │   ├── alert_service.py         # calcula alertas de reposição
│   │   ├── simulation_service.py    # aplica delta de promoção sobre previsão
│   │   ├── report_service.py        # gera PDF / Excel
│   │   └── retrain_service.py       # orquestra retrain completo
│   │
│   ├── domain/                      # Camada de domínio — lógica pura (sem I/O)
│   │   ├── __init__.py
│   │   │
│   │   ├── etl/                     # Pipeline de ingestão
│   │   │   ├── __init__.py
│   │   │   ├── parser.py            # XLSX → records (migrado do código existente)
│   │   │   ├── deduplicator.py      # remoção de duplicatas por (doc_numero, produto_cod)
│   │   │   └── normalizer.py        # cast de tipos, limpeza de strings, parse de datas
│   │   │
│   │   ├── features/                # Engenharia de atributos
│   │   │   ├── __init__.py
│   │   │   ├── time_series.py       # prepare_monthly_series(df, produto_cod) → pd.Series
│   │   │   ├── exogenous.py         # build_exogenous_features(df, produto_cod) → pd.DataFrame
│   │   │   └── importance.py        # compute_rf_importance(), weight_features()
│   │   │
│   │   └── models/                  # Modelagem SARIMAX
│   │       ├── __init__.py
│   │       ├── stationarity.py      # check_stationarity(), suggest_d()
│   │       ├── order_selection.py   # select_sarimax_order() via grid AIC/BIC
│   │       ├── sarimax_trainer.py   # fit_sarimax(), run_product_pipeline()
│   │       ├── evaluator.py         # evaluate_model(), walk_forward_cv(), residual_tests()
│   │       └── forecaster.py        # generate_forecast(model_artifact, horizon) → ForecastResult
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
│           └── weekly_retrain.py    # configura APScheduler, define job de retrain
│
├── data/
│   ├── raw/                         # XLSX brutos (upload do usuário)
│   └── processed/
│       ├── contas_a_receber.csv     # base consolidada (sep=";")
│       └── processamento_log.json
│
├── models/                          # Artefatos treinados (joblib)
│   └── {produto_cod}/
│       ├── sarimax_result.pkl       # SARIMAXResultsWrapper serializado
│       ├── importances.pkl          # pd.Series de importâncias RF
│       ├── scaler.pkl               # StandardScaler (se usado)
│       └── metadata.json            # ordem, métricas, data de treino
│
├── results/
│   ├── metrics/                     # CSVs de métricas consolidadas
│   └── plots/                       # Gráficos (opcionais em produção)
│
├── training_scripts/                # Experimentação pré-produção do SARIMAX — roda fora do
│   │                                 # backend, nunca é importado por ele (ver docs/predicao/
│   │                                 # plano_experimentos_modelagem.md)
│   ├── __init__.py
│   ├── eda/                         # Fase 1.1 — sazonalidade, tendência, CV por produto, Top-N
│   ├── baseline/                    # Fase 1 — Modelo A0 (SARIMA puro) e A1 (SARIMAX interno)
│   ├── enriched/                    # Fase 3 — Modelo B (SARIMAX interno + exógenas externas)
│   ├── alternative_models/          # Fase 4 — ETS/Holt-Winters, XGBoost, Prophet, NN global
│   ├── validation/                  # Walk-forward CV, testes de resíduos e de significância
│   │                                 # (Diebold-Mariano/Wilcoxon) — compartilhado entre fases
│   └── results/                     # metrics/ e plots/ da experimentação (staging; distinto
│                                     # do results/ de produção acima — só migra para lá o
│                                     # pipeline vencedor, na Fase 5)
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_normalizer.py
│   │   ├── test_time_series.py
│   │   ├── test_exogenous.py
│   │   ├── test_order_selection.py
│   │   ├── test_evaluator.py
│   │   └── test_forecaster.py
│   ├── integration/
│   │   ├── test_etl_pipeline.py
│   │   ├── test_sarimax_pipeline.py
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
    - Strip de strings, upper em produto_cod e cliente_cod
    - Remove registros com qtdade <= 0 ou emissao nula
    Retorna DataFrame com dtypes corretos.
    """
```

### 4.3 `domain/etl/deduplicator.py`

```python
def deduplicate(
    new_df: pd.DataFrame,
    existing_csv: str | Path,
    key_fields: tuple[str, ...] = ("doc_numero", "produto_cod"),
) -> pd.DataFrame:
    """
    Carrega chaves existentes do CSV, filtra registros novos que já existam.
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

## 5. Camada de Modelos — SARIMAX

### 5.1 `domain/features/time_series.py`

```python
def prepare_monthly_series(df: pd.DataFrame, produto_cod: str) -> pd.Series:
    """
    Agrega qtdade por período mensal (freq='MS').
    Preenche meses ausentes com 0 (reindex completo do range).
    Índice: DatetimeIndex com freq='MS'.
    Levanta ValueError se len(series) < MIN_OBSERVATIONS (15).
    """

MIN_OBSERVATIONS = 15
```

### 5.2 `domain/features/exogenous.py`

**Variáveis exógenas construídas** (por período mensal):

| Grupo | Variável | Descrição |
|---|---|---|
| Mercado geral | `mkt_qtd_total` | Qtd total vendida (todos produtos) |
| Mercado geral | `mkt_valor_total` | Faturamento total |
| Mercado geral | `mkt_desconto_total` | Desconto total concedido |
| Mercado geral | `mkt_n_pedidos` | Número único de pedidos |
| Mercado geral | `mkt_n_clientes` | Número único de clientes |
| Mercado geral | `mkt_preco_medio` | Preço médio geral |
| Mercado geral | `mkt_taxa_desconto` | `desconto_total / valor_total` |
| Produto | `prod_preco_medio` | Preço médio do produto |
| Produto | `prod_desconto_medio` | Desconto médio no produto |
| Produto | `prod_n_clientes` | Clientes únicos do produto |
| Produto | `prod_n_pedidos` | Pedidos únicos do produto |
| Produto | `prod_taxa_desconto` | `desconto_medio / preco_medio` |
| Calendário | `mes` | Mês numérico (1–12) |
| Calendário | `trimestre` | Trimestre (1–4) |
| Calendário | `alta_temporada` | 1 se mês ∈ {5,10,11,12} (Mães, Out/Nov/Natal) |

```python
def build_exogenous_features(df: pd.DataFrame, produto_cod: str) -> pd.DataFrame:
    """
    Constrói DataFrame de exógenas mensais para o produto.
    Índice: DatetimeIndex com freq='MS'.
    Preenche NaN com 0 (produto sem venda no mês).
    """
```

### 5.3 `domain/features/importance.py`

```python
def compute_rf_importance(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_estimators: int = 200,
    random_state: int = 42,
) -> pd.Series:
    """
    Treina RandomForestRegressor, retorna importâncias MDI normalizadas (soma=1).
    """

def weight_features(X: pd.DataFrame, importances: pd.Series) -> pd.DataFrame:
    """
    Pondera colunas de X pelas importâncias.
    Aplica clip(lower=0.1) para nunca zerar variável.
    """
```

### 5.4 `domain/models/stationarity.py`

```python
def check_stationarity(ts: pd.Series, alpha: float = 0.05) -> StationarityResult:
    """
    Executa ADF e KPSS.
    Retorna dataclass com estatísticas e flag is_stationary.
    """

def suggest_d(ts: pd.Series, max_d: int = 1) -> int:
    """Retorna 0 ou 1. Série curta (26 obs): não usar d>1."""
```

### 5.5 `domain/models/order_selection.py`

```python
def select_sarimax_order(
    ts_train: pd.Series,
    exog_train: pd.DataFrame,
    d: int,
    D: int = 0,          # D=0: série curta (<3 ciclos sazonais completos)
    m: int = 12,
    p_range: range = range(0, 3),
    q_range: range = range(0, 3),
    P_range: range = range(0, 2),
    Q_range: range = range(0, 2),
    criterion: str = "aic",
) -> tuple[tuple[int,int,int], tuple[int,int,int,int]]:
    """
    Grid search exaustivo: 3×3×2×2 = 36 combinações.
    Retorna (order, seasonal_order) com menor AIC/BIC.
    Falhas individuais são silenciadas; se todas falharem levanta RuntimeError.
    """
```

**Nota D=0**: com 26 meses de histórico temos menos de 3 ciclos sazonais completos (3×12=36). D=1 causaria sobrediferenciação. O padrão sazonal é capturado pelos termos AR/MA sazonais (P, Q) com m=12.

### 5.6 `domain/models/sarimax_trainer.py`

```python
def fit_sarimax(
    ts_train: pd.Series,
    exog_train: pd.DataFrame,
    order: tuple[int,int,int],
    seasonal_order: tuple[int,int,int,int],
) -> SARIMAXResultsWrapper:
    """Ajusta e retorna modelo treinado. maxiter=300."""

def run_product_pipeline(
    df: pd.DataFrame,
    produto_cod: str,
    test_months: int = 3,
    future_months: int = 3,
    log_cv_threshold: float = 0.7,
) -> ProductPipelineResult:
    """
    Pipeline completo para um produto:
    1. prepare_monthly_series
    2. build_exogenous_features
    3. train/test split (últimos test_months como hold-out)
    4. compute_rf_importance (apenas em treino)
    5. weight_features
    6. suggest_d → select_sarimax_order → fit_sarimax
    7. generate_forecast (test + future)
    8. evaluate_model
    Retorna ProductPipelineResult (dataclass).
    """
```

**`ProductPipelineResult`** (dataclass):
```python
@dataclass
class ProductPipelineResult:
    produto_cod: str
    order: tuple
    seasonal_order: tuple
    use_log: bool
    metrics: dict           # MAE, RMSE, MAPE_%, SMAPE_%, R2
    importances: pd.Series
    ts_train: pd.Series
    ts_test: pd.Series
    in_sample_pred: pd.Series
    test_pred: pd.Series
    future_pred: pd.Series  # próximos future_months meses
    future_idx: pd.DatetimeIndex
    aic: float
    bic: float
    trained_at: datetime
```

### 5.7 `domain/models/evaluator.py`

```python
def evaluate_model(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """MAE, RMSE, MAPE_%, SMAPE_%, R2."""

def walk_forward_cv(
    df: pd.DataFrame,
    produto_cod: str,
    n_splits: int = 4,
    horizon: int = 1,
    min_train: int = 14,
) -> pd.DataFrame:
    """
    Expanding-window CV.
    Retorna DataFrame com colunas: fold, train_size, MAE, RMSE, MAPE_%, SMAPE_%, R2.
    """

def residual_tests(result: SARIMAXResultsWrapper) -> dict:
    """
    Ljung-Box (lag=min(10, n//5)) e Shapiro-Wilk.
    Retorna: {ljung_box_pvalue, shapiro_pvalue, residuals_normal, no_autocorrelation}
    """
```

**Critérios de aceitação** (do artigo, seção 6.5):
- MAPE < 20% para produtos de alto giro
- SMAPE < 30% para pelo menos os 2 produtos de maior volume

### 5.8 `domain/models/forecaster.py`

```python
def generate_forecast(
    model_result: SARIMAXResultsWrapper,
    importances: pd.Series,
    last_exog: pd.DataFrame,
    horizon_months: int,
    use_log: bool,
    last_date: pd.Timestamp,
) -> ForecastResult:
    """
    Gera previsão para horizon_months meses futuros.
    Extrapola variáveis exógenas: replica último mês + ajusta campos calendário.
    Aplica expm1 se use_log=True.
    Retorna ForecastResult com datas, valores, intervalo de confiança (±1.96*std).
    """

@dataclass
class ForecastResult:
    dates: list[str]           # ISO 8601, primeiro dia do mês
    predicted: list[float]
    lower_95: list[float]
    upper_95: list[float]
    horizon_months: int
    generated_at: str          # ISO 8601
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
app.include_router(router_alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(router_simulation.router, prefix="/api/v1", tags=["simulation"])
app.include_router(router_reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(router_models.router, prefix="/api/v1", tags=["models"])
```

### 6.2 `backend/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    RESULTS_DIR: str = "results"
    DATABASE_URL: str = "sqlite:///./floricultura.db"
    TOP_N_PRODUCTS: int = 20          # produtos a incluir no pipeline automático
    TEST_MONTHS: int = 3              # hold-out para avaliação
    FUTURE_MONTHS: int = 3            # horizonte de previsão futuro
    RETRAIN_DAY_OF_WEEK: str = "mon"  # segunda-feira
    RETRAIN_HOUR: int = 2             # 02:00
    MIN_OBSERVATIONS: int = 15        # mínimo para treinar modelo
    LOG_CV_THRESHOLD: float = 0.7     # limiar para log-transform
    ALERT_STOCK_DAYS: int = 21        # janela de reposição (3 semanas)
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
- `sort_by: str = "total_sold"` (total_sold | name | mape)
- `search: str = ""` (busca em produto_cod e produto_nome)

**Response 200** (`ProductListResponse`):
```json
{
  "total": 5134,
  "items": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "total_sold": 128450.0,
      "model_status": "trained",
      "last_mape": 8.3,
      "last_trained_at": "2026-07-21T02:00:00"
    }
  ]
}
```

`model_status`: `"trained"` | `"insufficient_data"` | `"error"` | `"pending"`

---

### 7.4 `GET /api/v1/products/{produto_cod}`

**Response 200** (`ProductDetailResponse`):
```json
{
  "produto_cod": "147",
  "produto_nome": "ROSA VERMELHA 40CM",
  "total_sold": 128450.0,
  "monthly_history": [
    {"date": "2024-01-01", "quantity": 4200.0},
    {"date": "2024-02-01", "quantity": 3800.0}
  ],
  "top_customers": [
    {"cliente_cod": "001", "cliente_nome": "ATACADÃO FLORES", "total": 18000.0}
  ],
  "model_status": "trained",
  "metrics": {
    "MAE": 312.4,
    "RMSE": 418.1,
    "MAPE_%": 8.3,
    "SMAPE_%": 7.9,
    "R2": 0.87
  },
  "sarimax_order": "(1,1,1)",
  "seasonal_order": "(1,0,1,12)",
  "use_log_transform": false,
  "last_trained_at": "2026-07-21T02:00:00"
}
```

---

### 7.5 `GET /api/v1/forecast/{produto_cod}`

Query params:
- `horizon_months: int = 3` (1–6)

**Response 200** (`ForecastResponse`):
```json
{
  "produto_cod": "147",
  "produto_nome": "ROSA VERMELHA 40CM",
  "horizon_months": 3,
  "forecast": [
    {
      "date": "2026-08-01",
      "predicted": 4850.0,
      "lower_95": 3920.0,
      "upper_95": 5780.0,
      "month_label": "Ago/2026"
    },
    {
      "date": "2026-09-01",
      "predicted": 4200.0,
      "lower_95": 3310.0,
      "upper_95": 5090.0,
      "month_label": "Set/2026"
    },
    {
      "date": "2026-10-01",
      "predicted": 6100.0,
      "lower_95": 4980.0,
      "upper_95": 7220.0,
      "month_label": "Out/2026"
    }
  ],
  "generated_at": "2026-07-28T14:32:00",
  "model_trained_at": "2026-07-21T02:00:00"
}
```

**Errors**:
- `404` — produto não encontrado
- `409` — modelo não treinado para este produto (`model_status != "trained"`)

---

### 7.6 `GET /api/v1/forecast/batch`

Query params:
- `top_n: int = 10`
- `horizon_months: int = 3`

**Response 200** (`ForecastBatchResponse`):
```json
{
  "horizon_months": 3,
  "generated_at": "2026-07-28T14:32:00",
  "forecasts": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "next_month_predicted": 4850.0,
      "next_month_lower_95": 3920.0,
      "next_month_upper_95": 5780.0,
      "next_month_date": "2026-08-01"
    }
  ]
}
```

---

### 7.7 `GET /api/v1/alerts`

Query params:
- `limit: int = 50`
- `severity: str = "all"` (all | high | medium)

**Lógica de alerta**: previsão do próximo mês × fator de sazonalidade ≥ estoque estimado atual. Como o sistema não tem estoque atual real, o alerta é calculado como: produto com previsão no próximo mês **≥ 20% acima** da média dos últimos 3 meses (indicativo de pico de demanda = necessidade de reposição antecipada).

**Response 200** (`AlertListResponse`):
```json
{
  "generated_at": "2026-07-28T14:32:00",
  "total_alerts": 7,
  "items": [
    {
      "produto_cod": "147",
      "produto_nome": "ROSA VERMELHA 40CM",
      "severity": "high",
      "reason": "Previsão de Ago/2026 (4850 un) é 38% acima da média recente (3510 un)",
      "predicted_next_month": 4850.0,
      "recent_avg_3m": 3510.0,
      "variation_pct": 38.2,
      "alert_date": "2026-08-01"
    }
  ]
}
```

---

### 7.8 `POST /api/v1/simulation`

**Request** (`SimulationRequest`):
```json
{
  "produto_cod": "147",
  "horizon_months": 3,
  "scenarios": [
    {
      "label": "Promoção 15%",
      "discount_pct": 15.0,
      "apply_months": ["2026-08-01"]
    },
    {
      "label": "Venda casada com produto 150",
      "bundle_product_cod": "150",
      "expected_uplift_pct": 10.0,
      "apply_months": ["2026-08-01", "2026-09-01"]
    }
  ]
}
```

**Modelo de simulação**: o impacto é aplicado como multiplicador sobre a previsão SARIMAX base. O delta de promoção é estimado usando o coeficiente `prod_taxa_desconto` do modelo SARIMAX, escalado pelo percentual informado. Para vendas casadas, aplica-se o `expected_uplift_pct` diretamente como fator multiplicativo (1 + uplift/100).

**Response 200** (`SimulationResponse`):
```json
{
  "produto_cod": "147",
  "base_forecast": [
    {"date": "2026-08-01", "predicted": 4850.0}
  ],
  "scenarios": [
    {
      "label": "Promoção 15%",
      "forecast": [
        {"date": "2026-08-01", "predicted": 5680.0, "delta": 830.0, "delta_pct": 17.1}
      ]
    }
  ]
}
```

---

### 7.9 `GET /api/v1/reports/export`

Query params:
- `format: str` — `"excel"` | `"pdf"`
- `top_n: int = 10`
- `horizon_months: int = 3`

**Response 200**: arquivo binário com header `Content-Disposition: attachment`

**Conteúdo do Excel**:
- Aba "Previsões": tabela com todos os produtos e previsões por mês
- Aba "Métricas": MAE, RMSE, MAPE, SMAPE, R² por produto
- Aba "Alertas": lista de alertas gerados

**Conteúdo do PDF**:
- Cabeçalho com data de geração
- Tabela de previsões (top N produtos, próximo mês)
- Lista de alertas
- Rodapé com disclaimer de confiabilidade

---

### 7.10 `GET /api/v1/models/status`

**Response 200** (`ModelStatusResponse`):
```json
{
  "last_retrain_at": "2026-07-21T02:00:00",
  "next_retrain_at": "2026-07-28T02:00:00",
  "total_products": 5134,
  "trained_products": 18,
  "failed_products": 2,
  "insufficient_data_products": 5114,
  "is_training": false,
  "training_progress_pct": null
}
```

---

### 7.11 `POST /api/v1/models/retrain`

Dispara retrain manual (assíncrono). Protegido por rate-limit: máximo 1 retrain em execução por vez.

**Request**: corpo vazio

**Response 202**:
```json
{
  "message": "Retrain iniciado em background.",
  "started_at": "2026-07-28T15:00:00"
}
```

**Errors**:
- `409` — retrain já em execução

---

## 8. Schemas Pydantic

```python
# backend/schemas/forecast.py
from pydantic import BaseModel
from typing import Optional

class ForecastPoint(BaseModel):
    date: str
    predicted: float
    lower_95: float
    upper_95: float
    month_label: str

class ForecastResponse(BaseModel):
    produto_cod: str
    produto_nome: str
    horizon_months: int
    forecast: list[ForecastPoint]
    generated_at: str
    model_trained_at: str

# backend/schemas/product.py
class ProductSummary(BaseModel):
    produto_cod: str
    produto_nome: str
    total_sold: float
    model_status: str   # trained | insufficient_data | error | pending
    last_mape: Optional[float]
    last_trained_at: Optional[str]

class ProductListResponse(BaseModel):
    total: int
    items: list[ProductSummary]

# backend/schemas/alert.py
class AlertItem(BaseModel):
    produto_cod: str
    produto_nome: str
    severity: str       # high | medium
    reason: str
    predicted_next_month: float
    recent_avg_3m: float
    variation_pct: float
    alert_date: str

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
    apply_months: list[str]

class SimulationRequest(BaseModel):
    produto_cod: str
    horizon_months: int = 3
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
    total_products: int
    trained_products: int
    failed_products: int
    insufficient_data_products: int
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
    total_sold      = Column(Float)   # atualizado após cada ETL
    updated_at      = Column(DateTime, default=func.now())

# Tabela: model_artifacts
class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod     = Column(String, ForeignKey("products.produto_cod"), index=True)
    status          = Column(String)    # trained | error | insufficient_data | training
    sarimax_order   = Column(String)    # e.g. "(1,1,1)"
    seasonal_order  = Column(String)    # e.g. "(1,0,1,12)"
    use_log         = Column(Boolean, default=False)
    artifact_path   = Column(String)    # caminho do .pkl do modelo
    importance_path = Column(String)    # caminho do .pkl das importâncias
    mae             = Column(Float)
    rmse            = Column(Float)
    mape            = Column(Float)
    smape           = Column(Float)
    r2              = Column(Float)
    aic             = Column(Float)
    bic             = Column(Float)
    error_message   = Column(String, nullable=True)
    trained_at      = Column(DateTime)
    observations    = Column(Integer)   # número de meses no treino

# Tabela: forecasts_cache
class ForecastCache(Base):
    __tablename__ = "forecasts_cache"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod     = Column(String, ForeignKey("products.produto_cod"), index=True)
    forecast_date   = Column(String)    # "2026-08-01"
    predicted       = Column(Float)
    lower_95        = Column(Float)
    upper_95        = Column(Float)
    generated_at    = Column(DateTime)
    model_id        = Column(Integer, ForeignKey("model_artifacts.id"))

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

# Tabela: retrain_history
class RetrainHistory(Base):
    __tablename__ = "retrain_history"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    started_at      = Column(DateTime)
    finished_at     = Column(DateTime, nullable=True)
    trigger         = Column(String)    # "scheduled" | "manual"
    products_trained = Column(Integer)
    products_failed  = Column(Integer)
    status          = Column(String)    # running | completed | failed
```

### 9.2 `infrastructure/storage/model_registry.py`

```python
class ModelRegistry:
    def save_artifact(self, result: ProductPipelineResult) -> ModelArtifact:
        """Serializa model_result e importances com joblib, salva paths no DB."""

    def load_artifact(self, produto_cod: str) -> tuple[SARIMAXResultsWrapper, pd.Series, ModelArtifact]:
        """Carrega pkl e retorna (model_result, importances, metadata)."""

    def get_status(self, produto_cod: str) -> str:
        """Retorna status do modelo mais recente para o produto."""

    def list_trained_products(self) -> list[str]:
        """Retorna lista de produto_cod com status='trained'."""

    def mark_training(self, produto_cod: str) -> None:
        """Atualiza status para 'training'."""

    def mark_error(self, produto_cod: str, error: str) -> None:
        """Atualiza status para 'error' com mensagem."""
```

---

## 10. Agendamento — Weekly Retrain

### 10.1 `infrastructure/scheduler/weekly_retrain.py`

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.services.retrain_service import RetrainService

_scheduler = BackgroundScheduler()

def start_scheduler():
    _scheduler.add_job(
        func=_run_weekly_retrain,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0),
        id="weekly_retrain",
        replace_existing=True,
        misfire_grace_time=3600,   # tolera até 1h de atraso
    )
    _scheduler.start()

def _run_weekly_retrain():
    service = RetrainService()
    service.run_full_retrain(trigger="scheduled")
```

### 10.2 `services/retrain_service.py`

```python
class RetrainService:
    def run_full_retrain(self, trigger: str = "manual") -> RetrainSummary:
        """
        1. Carrega contas_a_receber.csv completo
        2. Seleciona top_N produtos por qtdade total
        3. Para cada produto:
           a. run_product_pipeline()
           b. model_registry.save_artifact()
           c. Invalida cache de forecasts no DB
        4. Registra RetrainHistory no DB
        5. Retorna RetrainSummary
        Exceções por produto são capturadas e logadas; não abortam o pipeline.
        """
```

**`RetrainSummary`**:
```python
@dataclass
class RetrainSummary:
    started_at: datetime
    finished_at: datetime
    trigger: str
    products_trained: int
    products_failed: int
    products_insufficient: int
    errors: list[dict]   # {produto_cod, error_message}
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

# Pipeline
TOP_N_PRODUCTS=20
TEST_MONTHS=3
FUTURE_MONTHS=3
MIN_OBSERVATIONS=15
LOG_CV_THRESHOLD=0.7
ALERT_STOCK_DAYS=21
MAX_UPLOAD_MB=50

# Scheduler
RETRAIN_DAY_OF_WEEK=mon
RETRAIN_HOUR=2
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

const result = await forecastApi.getForecast({ productoCod: '147', horizonMonths: 3 })
```

Qualquer mudança nos schemas do backend quebra o build TypeScript — erros de contrato detectados em compile time, não em runtime.

---

## 12. Estratégia de Testes

### 12.1 Testes Unitários (pytest)

| Arquivo | Cobertura |
|---|---|
| `test_parser.py` | parse_xlsx com fixture de XLSX mínimo; estrutura de records; campos obrigatórios |
| `test_normalizer.py` | cast de tipos; linhas com qtdade<=0 removidas; datas inválidas |
| `test_deduplicator.py` | deduplicação por (doc_numero, produto_cod) |
| `test_time_series.py` | preenchimento de meses vazios; erro com <15 obs |
| `test_exogenous.py` | 15 colunas esperadas; alinhamento de índices; alta_temporada=1 em maio |
| `test_importance.py` | importâncias somam 1; weight_features respeita clip(0.1) |
| `test_stationarity.py` | suggest_d retorna 0 para série estacionária |
| `test_order_selection.py` | retorna tupla válida; lida com falhas individuais sem abort |
| `test_evaluator.py` | métricas corretas com arrays conhecidos; walk_forward_cv com n_splits=2 |
| `test_forecaster.py` | ForecastResult com N datas corretas; back-transform log |
| `test_alert_service.py` | severity=high se variação>30%; medium se 20–30% |
| `test_simulation_service.py` | delta = 0 sem cenários; multiplicador correto |

### 12.2 Testes de Integração

| Arquivo | Cobertura |
|---|---|
| `test_etl_pipeline.py` | upload_service.process_upload com XLSX real (fixture) → CSV atualizado |
| `test_sarimax_pipeline.py` | run_product_pipeline com produto da fixture → result com todas as chaves |
| `test_api_endpoints.py` | TestClient FastAPI: /health, /upload, /products, /forecast/{id}, /alerts |

### 12.3 Validação Estatística (critérios formais do artigo, seção 6.5)

A validação do sistema segue as **três dimensões** definidas na seção 6.5 do artigo:

1. **Validação estatística dos modelos** — MAE, RMSE, MAPE, SMAPE, R² em hold-out (3
   meses) e walk-forward CV (4 folds). Limiares: MAPE < 20% (alto giro), SMAPE < 30%
   (top 2 produtos).
2. **Testes de diagnóstico de resíduos** — Ljung-Box (ausência de autocorrelação) e
   Shapiro-Wilk (normalidade dos resíduos).
3. **Testes funcionais do sistema** — upload, processamento, visualização e exportação
   com dados reais da entidade parceira; consistência, desempenho e usabilidade com
   usuários não técnicos (T078 em `tasks.md`).

```python
# tests/integration/test_model_quality.py
def test_mape_aceitavel_produtos_alto_giro():
    """MAPE < 20% para os 2 produtos de maior volume (REQ validação seção 6.5)"""
    ...

def test_residuos_ljung_box():
    """p-value Ljung-Box > 0.05 (sem autocorrelação residual)"""
    ...

def test_residuos_shapiro_wilk():
    """p-value Shapiro-Wilk > 0.05 (normalidade dos resíduos)"""
    ...
```

### 12.4 Ferramentas de Modelagem — Diagramas UML (seção 6.4 do artigo)

Entregável acadêmico obrigatório, produzido com ferramenta de modelagem UML compatível
com os padrões acadêmicos exigidos e versionado em `docs/uml/`:

| Diagrama | Cobertura |
|---|---|
| Casos de uso | Atores (admin, viewer) × funcionalidades (upload, forecast, alertas, simulação, export) |
| Atividades | Fluxo do pipeline ETL → features → SARIMAX → forecast; fluxo de retrain semanal |
| Classes | Entidades de domínio (Produto, Transação, Modelo, Previsão, Alerta) e suas relações |
| Modelo de dados | Diagrama ER das tabelas SQLite (seção 9.1) |
| Arquitetura lógica | As 4 camadas da Clean Architecture (seção 2.1) |

### 12.5 Avaliação Comparativa de Granularidade — Mensal vs. Diária

Contribuição acadêmica (ii) do artigo (seção 3/5): comparação formal, via walk-forward
CV, entre modelos treinados em granularidade mensal e diária para o **mesmo conjunto de
produtos perecíveis**. Resultado documentado (relatório + métricas lado a lado) em
`docs/`; **não altera** a decisão de produção (granularidade mensal — seção 2.2), que já
se apoia em achado preliminar desta mesma análise (>70% de zeros por produto em base
diária).

---

## 13. Mapeamento de Requisitos

| Código | Requisito (artigo) | Implementação |
|---|---|---|
| REQ-01 | Upload de planilhas XLSX | `POST /api/v1/upload` + `upload_service.py` |
| REQ-02 | Previsão 2–3 semanas à frente | `GET /api/v1/forecast/{id}` com `horizon_months=3` |
| REQ-03 | Atualização automática semanal | APScheduler segunda-feira 02:00 → `retrain_service.py` |
| REQ-04 | Indicadores de desempenho para não-técnicos | `GET /api/v1/models/status` + campos de métricas em `/products/{id}` |
| REQ-05 | Gráficos de tendência | `monthly_history` em `/products/{id}` + `forecast` em `/forecast/{id}` (dados para Recharts) |
| REQ-06 | Produtos mais vendidos em períodos especiais | `alta_temporada` na feature exógena; `GET /products?sort_by=total_sold` |
| REQ-07 | Produtos comprados juntos | `GET /api/v1/products/{id}/bundles` *(fase 2 — market basket analysis)* |
| REQ-08 | Simulação de promoções e vendas casadas | `POST /api/v1/simulation` |
| REQ-09 | Alertas de reposição | `GET /api/v1/alerts` |
| REQ-10 | Exportação PDF e Excel | `GET /api/v1/reports/export?format=pdf|excel` |
| REQ-11 | Dashboard centralizado | React app-react/ consome todos os endpoints acima |
| REQ-12 | Documentação funcional e técnica | Este documento + OpenAPI `/docs` gerado automaticamente |
| RNF-01 | Usabilidade para não-técnicos | Mensagens de erro em PT-BR; UI sem jargão técnico |
| RNF-02 | Rastreabilidade e logs | `processing_log` + `retrain_history` no DB; `processamento_log.json` |
| RNF-03 | Retrain < 2h | top_N=20 produtos; grid 36 combinações por produto; ~3min/produto estimado |
| RNF-04 | Segurança e LGPD | *(fase 2 — auth por JWT + perfis)* |
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
  8. domain/features/ (time_series + exogenous + importance)
  9. domain/models/ (stationarity + order_selection + sarimax_trainer + evaluator + forecaster)
  10. infrastructure/storage/model_registry.py
  11. services/retrain_service.py
  12. tests/unit/test_*model* + test_evaluator (inclui Ljung-Box + Shapiro-Wilk)

Sprint 3 (Ago/2026):
  13. api/router_products + router_forecast + router_alerts
  14. services/forecast_service + alert_service
  15. infrastructure/scheduler/weekly_retrain.py
  16. tests/integration/test_api_endpoints
  17. Avaliação comparativa mensal vs. diária (seção 12.5) — relatório

Sprint 4 (Set/2026):
  18. api/router_simulation + services/simulation_service
  19. api/router_reports + services/report_service (Excel + PDF)
  20. api/router_models (status + manual retrain)
  21. Integração com React (app-react/)

Sprint 5 (Out/2026 — Testes integrados):
  22. Testes funcionais com usuários da empresa parceira (percurso guiado das User Stories)
  23. Ajustes finais → versão candidata à entrega

Sprint 6 (Nov/2026 — Documentação final):
  24. docs/quickstart.md + documentação técnica consolidada
  25. Entrega final
```

---

*Documento gerado em 2026-07-28. Baseado no artigo TCC, código existente em `ia-predictor/` e requisitos validados com a entidade parceira.*
