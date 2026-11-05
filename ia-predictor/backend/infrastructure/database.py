"""Camada de infraestrutura de banco de dados: engine, sessão, ORM e criação de tabelas.

Mantido como módulo único (em vez do pacote `database/{engine,models,migrations}.py`
sugerido em SPECS.md) para acompanhar o layout já commitado em `ia-predictor/backend/`.
Diagrama: `docs/database/modelo_dados.drawio`.

Três grupos de tabelas:

  * Acesso: `users` e `revoked_tokens` (sessões encerradas no logout).
  * Base de vendas: `units`, `categories`, `products`, `sales` (os campos da planilha que
    o sistema usa — a planilha em si não é guardada), `calendar_days` e `processing_log`
    (cada planilha gravada: nome, hash, resultado da carga e o treino que a usou primeiro).
  * Previsão (ADR-017): `forecast_jobs` (cada treino, disparado pelo botão "Treinar
    previsões" ou pelo script `treinar_previsoes`), `forecast_job_logs` e, por série — as 4
    categorias e cada produto de grama, por loja —, `series_models`, `series_forecasts` e
    `series_backtest_points`. As telas leem o último treino `done`. Cada treino concluído
    atualiza `forecast_history`, o previsto de cada dia já passado (congelado), para o
    histórico da previsão.

Resumos por loja, categoria e produto (volume, SKUs, encomendas grandes, venda das últimas 8
semanas...) não são gravados: saem de `sales` até `forecast_jobs.data_until`.

As tabelas do treino anterior (`retrain_history`, `model_artifacts`, `backtest_points`,
`forecast_runs`, `forecasts_cache`: modelo da loja, desagregação e produtos regulares) saíram
do ORM. Num banco antigo elas continuam lá, sem uso.

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
    UniqueConstraint,
    create_engine,
    event,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

Base = declarative_base()

_RUN_STATUS = {"hint": "pending|running|done|error"}
_JOB_STATUS = {"hint": "pending|running|done|error|skipped"}


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


class RevokedToken(Base):
    """Token de renovação encerrado no logout: `/auth/refresh` passa a recusá-lo. A linha
    só serve até o token expirar sozinho e é apagada depois disso."""

    __tablename__ = "revoked_tokens"

    jti = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


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
    `quality` traz o resumo da limpeza, o período da planilha e os dias de loja aberta que
    ficaram sem venda (avisados na conferência antes de gravar). `forecast_job_id` é o
    primeiro treino concluído que usou as vendas desta planilha.

    `kind = "reclassification"` não é planilha: registra a reclassificação das encomendas
    grandes da base inteira (`scripts/reclassificar_encomendas.py`, ADR-018), com os limiares
    de cada loja em `quality.limiar_encomenda_un`, ou a das categorias do catálogo
    (`scripts/reclassificar_produtos.py`), com cada produto em `quality.produtos_reclassificados`.
    Fica fora da lista de arquivos das telas.
    """

    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String, nullable=False, default="upload",
                  info={"hint": "upload|initial_load|reclassification"})
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
    quality = Column(JSON, nullable=True)  # limpeza, período, dias faltando e avisos
    forecast_job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="SET NULL"), nullable=True)


class Sale(Base):
    """Uma linha de produto de um documento de venda — os campos da planilha que o
    sistema usa.

    Ficam de fora: nome e código do cliente, vendedor, operador e observação (dados
    pessoais ou sem uso), ICMS retido (sempre zero) e total do documento (só confere a
    integridade na carga). O cliente vira `is_registered_customer`; a empresa emissora vira
    `unit_id`. `is_bulk_order` marca os documentos acima do limiar de encomenda grande da loja:
    média + 4 desvios-padrão da quantidade de todos os pedidos dela (ADR-018). Cada planilha
    recalcula o limiar, gravado em `processing_log.quality.limiar_encomenda_un`, e classifica
    só as linhas que insere — a marcação gravada não muda depois.

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
    """Calendário por loja (Etapa 10): exógenas do SARIMAX e marcação de dia fechado.

    Precisa cobrir os 14 dias seguintes à última venda (o treino usa o padrão da loja,
    fechada só no domingo, no dia que faltar, e registra o aviso). `updated_at` entra na
    impressão digital do treino: mudar o calendário permite treinar de novo.
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
# Previsão: treino das categorias e dos produtos de grama, por loja (ADR-017)
# --------------------------------------------------------------------------- #
class ForecastJob(Base):
    """Um disparo do serviço de previsão (`backend/services/servico_previsao.py`): SARIMAX
    direto nas 4 categorias e em cada produto de grama, por loja.

    É o treino da previsão do sistema (ADR-017): a previsão de 14 dias, o histórico e os
    relatórios leem o último disparo `done`. `trigger`: `manual` (botão "Treinar
    previsões") ou `script` (`backend/scripts/treinar_previsoes.py`, fora da API).

    `data_fingerprint` é a impressão digital das vendas, do calendário e do catálogo quando
    o treino leu os dados. Um disparo com a mesma impressão do último `done` é registrado
    como `skipped` (Princípio V) e não treina. `heartbeat_at` é gravado a cada 30 s enquanto o treino roda: `running`
    sem sinal há mais de 3 min é de um processo que caiu e vira `error`.
    """

    __tablename__ = "forecast_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String, nullable=False, default="manual", info={"hint": "manual|script"})
    status = Column(String, nullable=False, default="pending", info=_JOB_STATUS)
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
    # {origens, dias_avaliados, mae, rmse, mase, erro_relativo_naive, origens_vence_naive(_pct),
    #  cobertura_ic95_pct, largura_ic95, venda_media_dia, previsto_sobre_real_pct, erro_total_14d_pct,
    #  origens_com_falha, ljung_box_p, shapiro_p} — os dois últimos, dos resíduos do ajuste final
    metrics = Column(JSON, nullable=True)
    # {trend, transformation, training_base, window_days, ordens_convergidas, dias_historico,
    #  dias_com_venda_janela, encomendas_grandes, coeficientes (do ajuste final: termo → valor),
    #  fator_datas (a série leva o fator das datas comemorativas, ADR-019), ajustes_datas (os da
    #  previsão: evento, data, fator, multiplicador, anos, dias)}
    params = Column(JSON, nullable=True)
    train_start = Column(Date, nullable=True)  # janela da previsão final
    train_end = Column(Date, nullable=True)
    message = Column(String, nullable=True)
    trained_at = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (Index("ix_series_models_job_unit", "job_id", "unit_id"),)


class SeriesForecast(Base):
    """Previsão diária com faixa de 95% de uma série: os `FORECAST_HORIZON_DAYS` dias
    seguintes ao último dia com venda. `event_factor`: o multiplicador da data comemorativa
    que entrou no previsto e na faixa (ADR-019); nulo sem ajuste — o previsto do modelo é
    `predicted / event_factor`."""

    __tablename__ = "series_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("series_models.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)
    event_factor = Column(Float, nullable=True)


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


class ForecastHistory(Base):
    """Histórico da previsão de cada categoria e produto de grama de uma loja: o previsto de
    cada dia, para a tela comparar com o vendido (que sai de `sales`, sem encomendas grandes).

    Ao contrário de `series_backtest_points` (refeito a cada treino), aqui o dia fica
    congelado (`domain.historico_previsao`): cada disparo concluído do serviço de previsão
    troca os dias do início da previsão dele em diante e nunca mexe nos anteriores; dia que
    nenhuma previsão cobriu (antes do 1º treino, ou treino seguinte com mais de 14 dias de
    intervalo) vem do 1º dia das janelas do walk-forward e só preenche dia vazio.

    `source`: `forecast` (previsão do disparo `job_id`) ou `walk_forward`. `origin_date`: 1º
    dia da janela — o início da previsão, ou o próprio dia no walk-forward. `item`: id da
    categoria ou código do produto. `store_closed`: se o calendário dava a loja fechada no
    dia quando ele foi previsto — explica um previsto zero se o calendário mudar depois.
    `event_factor`: o multiplicador da data comemorativa que entrou no previsto (ADR-019) —
    com ele, o previsto do modelo sem o ajuste (`predicted / event_factor`) fica guardado
    para medir, depois da data, se o ajuste ajudou.
    """

    __tablename__ = "forecast_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(String, ForeignKey("units.id"), nullable=False)
    level = Column(String, nullable=False, info={"hint": "category|product"})
    item = Column(String, nullable=False)
    day = Column(Date, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_95 = Column(Float, nullable=False)
    upper_95 = Column(Float, nullable=False)
    source = Column(String, nullable=False, info={"hint": "forecast|walk_forward"})
    origin_date = Column(Date, nullable=False)  # 1º dia da janela que previu o dia
    job_id = Column(Integer, ForeignKey("forecast_jobs.id", ondelete="SET NULL"), nullable=True)
    store_closed = Column(Boolean, nullable=True)
    event_factor = Column(Float, nullable=True)  # multiplicador da data comemorativa (ADR-019); nulo sem ajuste

    __table_args__ = (UniqueConstraint("unit_id", "level", "item", "day", name="uq_forecast_history_dia"),)


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
    completar_colunas(engine)


# Colunas acrescentadas a tabelas que já podem existir no banco (`create_all` não altera
# tabela existente). As removidas do ORM ficam no banco, nulas, sem uso.
_COLUNAS_NOVAS = {
    "forecast_history": {"job_id": "INTEGER REFERENCES forecast_jobs(id) ON DELETE SET NULL",
                         "store_closed": "BOOLEAN", "event_factor": "FLOAT"},
    "processing_log": {"forecast_job_id": "INTEGER REFERENCES forecast_jobs(id) ON DELETE SET NULL"},
    "series_forecasts": {"event_factor": "FLOAT"},
}


def completar_colunas(bind) -> None:
    """Acrescenta as colunas de `_COLUNAS_NOVAS` que faltam nas tabelas do banco."""
    nomes = inspect(bind)
    with bind.begin() as conn:
        for tabela, colunas in _COLUNAS_NOVAS.items():
            existentes = {c["name"] for c in nomes.get_columns(tabela)}
            for coluna, tipo in colunas.items():
                if coluna not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"))


def get_db() -> Session:
    """FastAPI dependency: fornece uma sessão de banco por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
