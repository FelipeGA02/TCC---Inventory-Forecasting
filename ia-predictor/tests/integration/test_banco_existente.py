"""Banco que já existia antes de uma coluna nova: `create_all` não altera tabela existente,
então `completar_colunas` acrescenta o que falta (o Neon com as tabelas da versão anterior)."""
from datetime import date

from sqlalchemy import create_engine, inspect, text

from backend.infrastructure.database import Base, completar_colunas, remover_baixa_confianca


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


def test_banco_antigo_perde_a_baixa_confianca(tmp_path):
    """`low_confidence` saiu do sistema: a série que o tinha teve previsão (vira `trained`) e a
    contagem do treino, NOT NULL sem valor padrão, soma em `series_trained` e é apagada."""
    engine = create_engine(f"sqlite:///{tmp_path / 'antigo.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE forecast_jobs ADD COLUMN series_low_confidence INTEGER NOT NULL DEFAULT 0"))
        conn.execute(text("INSERT INTO forecast_jobs (id, trigger, status, created_at, total_series, done_series, "
                          "progress_pct, series_trained, series_low_confidence, series_insufficient, series_failed) "
                          "VALUES (1, 'manual', 'done', '2026-11-05', 23, 23, 100, 9, 14, 20, 0)"))
        conn.execute(text("INSERT INTO units (id, name, city) VALUES ('itabirito', 'Itabirito', 'Itabirito')"))
        conn.execute(text("INSERT INTO series_models (job_id, unit_id, level, series_key, status, trained_at) VALUES "
                          "(1, 'itabirito', 'category', 'a', 'low_confidence', '2026-11-05'), "
                          "(1, 'itabirito', 'category', 'b', 'insufficient_data', '2026-11-05')"))
    remover_baixa_confianca(engine)
    remover_baixa_confianca(engine)  # idempotente
    assert "series_low_confidence" not in {c["name"] for c in inspect(engine).get_columns("forecast_jobs")}
    with engine.begin() as conn:
        assert conn.execute(text("SELECT series_trained FROM forecast_jobs")).scalar() == 23
        assert sorted(conn.execute(text("SELECT status FROM series_models")).scalars()) == [
            "insufficient_data", "trained"]
