"""Banco que já existia antes de uma coluna nova: `create_all` não altera tabela existente,
então `completar_colunas` acrescenta o que falta (o Neon com as tabelas da versão anterior)."""
from datetime import date

from sqlalchemy import create_engine, inspect, text

from backend.infrastructure.database import Base, completar_colunas


def test_historico_antigo_ganha_job_id(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'antigo.db'}")
    with engine.begin() as conn:  # a tabela como a main a criou, ligada ao treino do painel
        conn.execute(text(
            "CREATE TABLE forecast_history (id INTEGER PRIMARY KEY, unit_id VARCHAR NOT NULL, "
            "level VARCHAR NOT NULL, item VARCHAR NOT NULL, day DATE NOT NULL, predicted FLOAT NOT NULL, "
            "lower_95 FLOAT NOT NULL, upper_95 FLOAT NOT NULL, source VARCHAR NOT NULL, "
            "origin_date DATE NOT NULL, retrain_id INTEGER, run_id INTEGER)"))
    Base.metadata.create_all(engine)  # cria as que faltam; a forecast_history fica como estava
    assert "job_id" not in {c["name"] for c in inspect(engine).get_columns("forecast_history")}

    completar_colunas(engine)
    completar_colunas(engine)  # idempotente
    assert {"job_id", "store_closed", "event_factor"} <= {
        c["name"] for c in inspect(engine).get_columns("forecast_history")}
    with engine.begin() as conn:
        conn.execute(Base.metadata.tables["forecast_history"].insert(), {
            "unit_id": "itabirito", "level": "category", "item": "grama", "day": date(2026, 3, 1),
            "predicted": 1.0, "lower_95": 0.0, "upper_95": 2.0, "source": "forecast",
            "origin_date": date(2026, 3, 1), "job_id": None, "store_closed": True})


def test_planilha_antiga_ganha_o_treino_que_a_usou(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'antigo.db'}")
    with engine.begin() as conn:  # processing_log como era: ligada ao treino antigo (retrain_id)
        conn.execute(text(
            "CREATE TABLE processing_log (id INTEGER PRIMARY KEY, kind VARCHAR NOT NULL, filename VARCHAR NOT NULL, "
            "file_sha256 VARCHAR NOT NULL, file_size_bytes INTEGER NOT NULL, reference_month VARCHAR, "
            "status VARCHAR NOT NULL, stage VARCHAR, message VARCHAR, user_id INTEGER, started_at DATETIME NOT NULL, "
            "finished_at DATETIME, rows_read INTEGER NOT NULL, rows_added INTEGER NOT NULL, "
            "rows_duplicate INTEGER NOT NULL, rows_skipped INTEGER NOT NULL, quality JSON, retrain_id INTEGER)"))
    Base.metadata.create_all(engine)
    completar_colunas(engine)
    assert "forecast_job_id" in {c["name"] for c in inspect(engine).get_columns("processing_log")}


def test_previsao_antiga_ganha_o_fator_das_datas(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'antigo.db'}")
    with engine.begin() as conn:  # series_forecasts como era antes do ADR-019
        conn.execute(text(
            "CREATE TABLE series_forecasts (id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL, "
            "forecast_date DATE NOT NULL, predicted FLOAT NOT NULL, lower_95 FLOAT NOT NULL, upper_95 FLOAT NOT NULL)"))
    Base.metadata.create_all(engine)
    completar_colunas(engine)
    assert "event_factor" in {c["name"] for c in inspect(engine).get_columns("series_forecasts")}
