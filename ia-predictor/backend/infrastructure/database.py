"""Camada de infraestrutura de banco de dados: engine, sessão, ORM e criação de tabelas.

Mantido como módulo único (em vez do pacote `database/{engine,models,migrations}.py`
sugerido em SPECS.md) para acompanhar o layout já commitado em `ia-predictor/backend/`.
Diagrama: `docs/database/modelo_dados.drawio`.

Quatro grupos de tabelas:

  * Acesso: `users`.
  * Base de vendas: `units`, `categories`, `products`, `sales` (os campos da planilha que
    o sistema usa — a planilha em si não é guardada), `calendar_days` e `processing_log`
    (cada planilha recebida: nome, hash e resultado da carga).
  * Previsão: `retrain_history` (cada execução do treino) e o que ela produz —
    `model_artifacts` (um modelo por loja e por produto regular) e `backtest_points` —, e
    `forecast_runs` (cada geração da previsão: ao fim de cada treino e quando o calendário
    muda depois dele) com o seu `forecasts_cache`. O painel mostra os próximos 14 dias da
    última geração concluída; as anteriores ficam para comparação.
  * Serviço de previsão (botão do admin): `forecast_jobs` (cada disparo, com o andamento),
    `forecast_job_logs`, e por série treinada `series_models`, `series_forecasts` e
    `series_backtest_points`. Independente do grupo anterior — não muda o painel.

Resumos por loja, categoria e produto (volume, SKUs, encomendas, venda das últimas 8
semanas...) não são gravados: saem de `sales` até `retrain_history.data_until`. Produto
"regular" é o que tem `model_artifacts` de nível `product` na execução.

`info={"hint": ...}` documenta os valores aceitos e aparece no diagrama.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
    event,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

Base = declarative_base()

_RUN_STATUS = {"hint": "pending|running|done|error"}
_RETRAIN_STATUS = {"hint": "pending|running|done|error|skipped"}


# --------------------------------------------------------------------------- #
# Acesso
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, info={"hint": "admin|viewer"})
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


# --------------------------------------------------------------------------- #
# Base de vendas
# --------------------------------------------------------------------------- #
class Unit(Base):
    """Loja. `name` é o valor da coluna `unidade` da base pré-processada (Etapa 3)."""

    __tablename__ = "units"

    id = Column(String, primary_key=True, info={"hint": "jardim-canada|itabirito"})
    name = Column(String, unique=True, nullable=False)
    city = Column(String, nullable=False)


class Category(Base):
    """Uma das 4 categorias do negócio (Grama, Plantas diversas, Produtos de jardim, Flores
    de corte) ou Serviço e taxa, que entra na base mas não é produto
    (`show_on_dashboard = False`, fica fora da previsão)."""

    __tablename__ = "categories"

    id = Column(String, primary_key=True, info={"hint": "grama|plantas-diversas|..."})
    name = Column(String, nullable=False)
    source_category = Column(String, unique=True, nullable=False)  # `categoria` da Etapa 3
    description = Column(String, nullable=False, default="")
    show_on_dashboard = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)


class Product(Base):
    __tablename__ = "products"

    code = Column(String, primary_key=True)  # `produto_cod` (preserva zeros à esquerda)
    name = Column(String, nullable=False)  # nome mais recente na base
    category_id = Column(String, ForeignKey("categories.id"), nullable=False, index=True)
    subcategory = Column(String, nullable=True)  # `categoria_fina` da Etapa 3
    total_sold = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class ProcessingLog(Base):
    """Cada planilha "Contas a Receber" recebida e o resultado da carga.

    A planilha não é guardada: os campos usados vão para `sales` e o resto é descartado.
    `file_sha256` impede carregar o mesmo arquivo duas vezes (só conta carga `done`).
    """

    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String, nullable=False, default="upload", info={"hint": "upload|initial_load"})
    filename = Column(String, nullable=False)
    file_sha256 = Column(String, nullable=False, index=True)
    file_size_bytes = Column(Integer, nullable=False)
    reference_month = Column(String, nullable=True, info={"hint": "YYYY-MM"})
    status = Column(String, nullable=False, default="pending", info=_RUN_STATUS)
    stage = Column(String, nullable=True)  # etapa atual, em linguagem da loja
    message = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    rows_read = Column(Integer, default=0, nullable=False)
    rows_added = Column(Integer, default=0, nullable=False)
    rows_duplicate = Column(Integer, default=0, nullable=False)
    rows_skipped = Column(Integer, default=0, nullable=False)
    quality = Column(JSON, nullable=True)  # resumo da limpeza (linhas removidas e por quê)
    retrain_id = Column(Integer, ForeignKey("retrain_history.id"), nullable=True)


class Sale(Base):
    """Uma linha de produto de um documento de venda — os campos da planilha que o
    sistema usa.

    Ficam de fora: nome e código do cliente, vendedor, operador e observação (dados
    pessoais ou sem uso), ICMS retido (sempre zero) e total do documento (só confere a
    integridade na carga). O cliente vira `is_registered_customer`; a empresa emissora vira
    `unit_id`. `is_bulk_order` marca documentos com mais de 2.000 un. (ADR-013).

    `ix_sales_dedup` cobre a chave que descarta linhas já carregadas por outra planilha
    (`DUPLICATE_KEY_FIELDS` da Etapa 1: número da nota, produto, data, quantidade e valor).
    Não é único: o mesmo produto pode vir em duas linhas iguais da mesma nota.
    """

    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_date = Column(Date, nullable=False)  # `emissao`
    unit_id = Column(String, ForeignKey("units.id"), nullable=False)  # de `empresa`
    document_type = Column(String, nullable=False)  # `doc_tipo`
    document_number = Column(String, nullable=False)  # `doc_numero`
    product_code = Column(String, ForeignKey("products.code"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)  # `qtdade` (negativa = devolução)
    unit_price = Column(Float, nullable=False, default=0.0)  # `vl_unit`
    gross_amount = Column(Float, nullable=False, default=0.0)  # `vl_total`
    discount = Column(Float, nullable=False, default=0.0)  # `vl_desconto`
    net_amount = Column(Float, nullable=False, default=0.0)  # `tot_liq`
    payment_method = Column(String, nullable=False, default="")  # `pagamento`
    is_registered_customer = Column(Boolean, nullable=False, default=False)
    is_bulk_order = Column(Boolean, nullable=False, default=False)
    import_id = Column(Integer, ForeignKey("processing_log.id"), nullable=True, index=True)

    __table_args__ = (
        Index("ix_sales_unit_date", "unit_id", "sale_date"),
        Index("ix_sales_dedup", "document_number", "product_code", "sale_date", "quantity", "gross_amount"),
    )


class CalendarDay(Base):
    """Calendário por loja (Etapa 10): exógenas do L1 e marcação de dia fechado.

    Precisa cobrir até `forecast_runs.end_date`. `updated_at` diz à conferência diária
    (03:00) se algum dia mudou depois da última geração da previsão.
    """

    __tablename__ = "calendar_days"

    unit_id = Column(String, ForeignKey("units.id"), primary_key=True)
    day = Column(Date, primary_key=True)
    store_closed = Column(Boolean, nullable=False, default=False)
    exceptional_opening = Column(Boolean, nullable=False, default=False)
    holiday_name = Column(String, nullable=True)
    special_date_name = Column(String, nullable=True)  # data comemorativa
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# --------------------------------------------------------------------------- #
# Previsão
# --------------------------------------------------------------------------- #
class RetrainHistory(Base):
    """Uma execução do treino (modelos das lojas e dos produtos regulares). Ao terminar,
    dispara uma `forecast_runs` com `trigger = retrain`.

    O treino agendado (segunda 02:00) é registrado como `skipped`, sem modelos nem
    previsão, quando não há venda nova desde o último treino `done` (mesmo `data_until`) e
    `config` é a mesma: ajustaria o mesmo modelo com os mesmos dados.
    """

    __tablename__ = "retrain_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String, nullable=False, info={"hint": "scheduled|manual|upload|import"})
    status = Column(String, nullable=False, default="pending", info=_RETRAIN_STATUS)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message = Column(String, nullable=True)
    data_until = Column(Date, nullable=True)  # último dia com venda usado no treino
    config = Column(JSON, nullable=True)  # horizonte, m, limiares, critério de regular...
    units_trained = Column(Integer, default=0, nullable=False)
    products_modeled = Column(Integer, default=0, nullable=False)


class ModelArtifact(Base):
    """Previsor de um treino, em três níveis:

    * `unit`: SARIMAX da loja;
    * `category` (`category_id`): desagregação loja → categoria — previsão da loja ×
      participação da categoria no mesmo dia da semana (últimas 8 semanas). Não tem modelo
      próprio (`sarimax_order` e `artifact_path` nulos); é testada nas mesmas rodadas da
      loja e por isso tem `status`, `metrics` e `backtest_points` como os outros;
    * `product` (`product_code`): SARIMAX do produto regular.

    Só `mase` e `ci95_coverage_pct` são colunas porque definem o `status`; o resto do
    walk-forward fica em `metrics` e a configuração do ajuste em `params`. Produto regular
    sem ordem que convirja fica com `sarimax_order` e `artifact_path` nulos e status
    `insufficient_data`.

    `artifact_path` (joblib, relativo a `MODELS_DIR`) é o modelo ajustado que uma nova
    geração (`trigger = calendar` ou `manual`) carrega para prever sem reajustar.
    """

    __tablename__ = "model_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    retrain_id = Column(Integer, ForeignKey("retrain_history.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(String, ForeignKey("units.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    product_code = Column(String, ForeignKey("products.code"), nullable=True)
    level = Column(String, nullable=False, info={"hint": "unit|category|product"})
    status = Column(String, nullable=False, info={"hint": "trained|low_confidence|..."})
    sarimax_order = Column(JSON, nullable=True, info={"hint": "[p,d,q]"})
    seasonal_order = Column(JSON, nullable=True, info={"hint": "[P,D,Q,m]"})
    artifact_path = Column(String, nullable=True)
    mase = Column(Float, nullable=True)
    ci95_coverage_pct = Column(Float, nullable=True)
    # unit/product: {aic, transformation, window_type, window_days, training_base, exog_features}
    # category: {share_window_weeks}
    params = Column(JSON, nullable=True)
    # {folds, folds_beating_naive, days_evaluated, mae, relative_error_naive, ci95_width,
    #  mean_daily_sales, forecast_to_actual_pct, total_error_14d_pct}
    metrics = Column(JSON, nullable=True)
    trained_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (Index("ix_model_retrain_unit", "retrain_id", "unit_id", "product_code"),)


class ForecastRun(Base):
    """Uma geração da previsão com os modelos de `retrain_id`: ao fim de cada treino
    (`retrain`) e quando `calendar_days` muda depois dela (`calendar`, conferido às 03:00).

    Gerar todo dia repetiria os mesmos números: com o mesmo modelo e os mesmos dados, a
    previsão de um dia não depende de quando é calculada. Por isso cada geração prevê de
    uma vez de `start_date` (dia seguinte a `retrain_history.data_until`) até `end_date`
    (`FORECAST_STORED_DAYS` dias), e a API entrega os `FORECAST_HORIZON_DAYS` dias a partir
    de hoje — a janela anda com a data sem recalcular. Se hoje + horizonte passa de
    `end_date`, a base está desatualizada (o painel avisa). `products_served` é a contagem
    de produtos com previsão (Princípio V).
    """

    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    retrain_id = Column(Integer, ForeignKey("retrain_history.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger = Column(String, nullable=False, info={"hint": "retrain|calendar|manual"})
    status = Column(String, nullable=False, default="pending", info=_RUN_STATUS)
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    message = Column(String, nullable=True)
    start_date = Column(Date, nullable=False)  # primeiro dia previsto
    end_date = Column(Date, nullable=False)  # último dia previsto
    units_served = Column(Integer, default=0, nullable=False)
    products_served = Column(Integer, default=0, nullable=False)


class ForecastCache(Base):
    """Previsão diária com faixa de 95%. `run_id` dá a geração; `model_id`, o previsor —
    a loja (total das 4 categorias), uma categoria ou um produto regular. `level` repete o
    `model_artifacts.level` para filtrar sem junção.

    Loja fechada e evento do dia vêm de `calendar_days`.
    """

    __tablename__ = "forecasts_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(Integer, ForeignKey("model_artifacts.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String, nullable=False, info={"hint": "unit|category|product"})
    forecast_date = Column(Date, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)

    __table_args__ = (Index("ix_forecast_run_level", "run_id", "level"),)


class BacktestPoint(Base):
    """Dia do walk-forward de um previsor (loja, categoria ou produto): previsto × real ×
    naïve. Alimenta o histórico da previsão e o gráfico de acerto de cada nível.

    Rodadas a cada 14 dias com horizonte de 14: cada dia pertence a uma só origem. O erro
    da rodada é a soma de |predicted − actual| por `origin_date` nos dias de loja aberta.
    """

    __tablename__ = "backtest_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model_artifacts.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_date = Column(Date, nullable=False)
    day = Column(Date, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)
    actual = Column(Float, nullable=False)
    naive = Column(Float, nullable=False)


# --------------------------------------------------------------------------- #
# Serviço de previsão (categorias + produtos de grama, botão do admin)
# --------------------------------------------------------------------------- #
class ForecastJob(Base):
    """Um disparo do serviço de previsão (`backend/services/servico_previsao.py`): SARIMAX
    direto nas 4 categorias e em cada produto de grama, por loja.

    Separado de `retrain_history`: o painel atual lê aquela tabela e espera loja +
    desagregação; este serviço treina categoria direto (ADR-016) e não pode trocar o que o
    painel mostra.

    `data_fingerprint` é a impressão digital das vendas, do calendário e do catálogo quando
    o treino leu os dados. Um disparo com a mesma impressão do último `done` é registrado
    como `skipped` (Princípio V) e não treina. `heartbeat_at` é gravado a cada 30 s enquanto o treino roda: `running`
    sem sinal há mais de 3 min é de um processo que caiu e vira `error`.
    """

    __tablename__ = "forecast_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String, nullable=False, default="manual", info={"hint": "manual"})
    status = Column(String, nullable=False, default="pending", info=_RETRAIN_STATUS)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    data_fingerprint = Column(String(64), nullable=True, index=True)
    data_until = Column(Date, nullable=True)  # último dia com venda usado no treino
    config = Column(JSON, nullable=True)  # m, d, D, janela, origens, horizonte, limiares
    total_series = Column(Integer, default=0, nullable=False)  # séries com dados para treinar
    done_series = Column(Integer, default=0, nullable=False)  # delas, quantas já terminaram
    current_series = Column(String, nullable=True)  # rótulo da série em treino, para o progresso
    progress_pct = Column(Float, default=0.0, nullable=False)
    series_trained = Column(Integer, default=0, nullable=False)
    series_low_confidence = Column(Integer, default=0, nullable=False)
    series_insufficient = Column(Integer, default=0, nullable=False)
    series_failed = Column(Integer, default=0, nullable=False)
    message = Column(String, nullable=True)


class ForecastJobLog(Base):
    """Linha do log de um disparo do serviço de previsão (o que aconteceu em cada série)."""

    __tablename__ = "forecast_job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    logged_at = Column(DateTime, default=datetime.now, nullable=False)
    level = Column(String, nullable=False, default="info", info={"hint": "info|warning|error"})
    series_key = Column(String, nullable=True)
    message = Column(String, nullable=False)


class SeriesModel(Base):
    """Uma série treinada (ou recusada) num disparo do serviço de previsão.

    `level = category` (`category_id`) ou `product` (`product_code`, sempre de Grama).
    `series_key` = `loja:nível:id`. Série sem dados suficientes fica registrada com
    `status = insufficient_data` e o motivo em `message`, sem previsão. `metrics` é o
    walk-forward nos dias de loja aberta; `params`, o que foi ajustado.
    """

    __tablename__ = "series_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(String, ForeignKey("units.id"), nullable=False)
    level = Column(String, nullable=False, info={"hint": "category|product"})
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    product_code = Column(String, ForeignKey("products.code"), nullable=True)
    series_key = Column(String, nullable=False)
    status = Column(String, nullable=False, info={"hint": "trained|low_confidence|insufficient_data|error"})
    sarimax_order = Column(JSON, nullable=True, info={"hint": "[p,d,q]"})
    seasonal_order = Column(JSON, nullable=True, info={"hint": "[P,D,Q,m]"})
    aic = Column(Float, nullable=True)
    mase = Column(Float, nullable=True)
    ci95_coverage_pct = Column(Float, nullable=True)
    # {origens, dias_avaliados, mae, rmse, mase, erro_relativo_naive, origens_vence_naive_pct,
    #  cobertura_ic95_pct, largura_ic95, venda_media_dia, previsto_sobre_real_pct, origens_com_falha}
    metrics = Column(JSON, nullable=True)
    # {trend, transformation, training_base, window_days, ordens_convergidas, dias_historico, dias_com_venda_janela}
    params = Column(JSON, nullable=True)
    train_start = Column(Date, nullable=True)  # janela da previsão final
    train_end = Column(Date, nullable=True)
    message = Column(String, nullable=True)
    trained_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (Index("ix_series_models_job_unit", "job_id", "unit_id"),)


class SeriesForecast(Base):
    """Previsão diária com faixa de 95% de uma série: os `FORECAST_HORIZON_DAYS` dias
    seguintes ao último dia com venda."""

    __tablename__ = "series_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("series_models.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)


class SeriesBacktestPoint(Base):
    """Previsto × real × naïve do walk-forward de uma série. A origem anda 1 dia e cada
    origem prevê os 14 seguintes, então o mesmo dia aparece em várias origens (`horizon`
    diz a distância até a origem)."""

    __tablename__ = "series_backtest_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("series_models.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_date = Column(Date, nullable=False)
    day = Column(Date, nullable=False)
    horizon = Column(Integer, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)
    actual = Column(Float, nullable=False)
    naive = Column(Float, nullable=False)


# --------------------------------------------------------------------------- #
# Engine e sessão
# --------------------------------------------------------------------------- #
def database_url(url: str) -> str:
    """Aceita a URL como o Neon (e outros Postgres gerenciados) entrega —
    `postgres://` ou `postgresql://` — e fixa o driver psycopg 3."""
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


_URL = database_url(settings.DATABASE_URL)
_IS_SQLITE = _URL.startswith("sqlite")

engine = create_engine(
    _URL,
    connect_args={"check_same_thread": False, "timeout": 30} if _IS_SQLITE else {},
    # Neon suspende o servidor ocioso e fecha as conexões: testa antes de usar e renova a
    # cada 5 min, para a primeira requisição depois da pausa não falhar.
    **({} if _IS_SQLITE else {"pool_pre_ping": True, "pool_recycle": 300}),
)

if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record) -> None:
        # WAL: leituras do painel continuam enquanto a carga ou o treino escrevem (ADR-005).
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Cria todas as tabelas se ainda não existirem (idempotente)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency: fornece uma sessão de banco por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
