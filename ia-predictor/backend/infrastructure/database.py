"""Camada de infraestrutura de banco de dados: engine, sessão, ORM e criação de tabelas.

Mantido como módulo único (em vez do pacote `database/{engine,models,migrations}.py`
sugerido em SPECS.md) para acompanhar o layout já commitado em `ia-predictor/backend/`.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin" | "viewer"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Product(Base):
    __tablename__ = "products"

    produto_cod = Column(String, primary_key=True)
    produto_nome = Column(String)
    total_sold = Column(Float)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod = Column(String, ForeignKey("products.produto_cod"), index=True)
    status = Column(String)  # trained | low_confidence | error | insufficient_data | training
    sarimax_order = Column(String)       # e.g. "(1,1,1)"
    seasonal_order = Column(String)      # e.g. "(1,0,1,12)"
    use_log = Column(Boolean, default=False)
    artifact_path = Column(String)
    importance_path = Column(String)
    mae = Column(Float)
    rmse = Column(Float)
    mape = Column(Float)
    smape = Column(Float)
    r2 = Column(Float)
    aic = Column(Float)
    bic = Column(Float)
    ljung_box_pvalue = Column(Float, nullable=True)
    shapiro_pvalue = Column(Float, nullable=True)
    error_message = Column(String, nullable=True)
    trained_at = Column(DateTime)
    observations = Column(Integer)


class ForecastCache(Base):
    __tablename__ = "forecasts_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    produto_cod = Column(String, ForeignKey("products.produto_cod"), index=True)
    forecast_date = Column(String)  # "2026-08-01"
    predicted = Column(Float)
    lower_95 = Column(Float)
    upper_95 = Column(Float)
    generated_at = Column(DateTime)
    model_id = Column(Integer, ForeignKey("model_artifacts.id"))


class ProcessingLog(Base):
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String)
    file_hash = Column(String)
    rows_added = Column(Integer)
    rows_skipped = Column(Integer)
    rows_duplicate = Column(Integer)
    processed_at = Column(DateTime, default=func.now())


class RetrainHistory(Base):
    __tablename__ = "retrain_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    trigger = Column(String)  # "scheduled" | "manual"
    products_trained = Column(Integer, default=0)
    products_failed = Column(Integer, default=0)
    status = Column(String, default="running")  # running | completed | failed


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)
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
