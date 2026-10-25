"""Preenche o histórico da previsão (`forecast_history`) num banco que já tinha treino
gravado antes da tabela existir: usa o walk-forward (`backtest_points`) e a última geração
(`forecasts_cache`) do último treino concluído. Pode rodar mais de uma vez: dia já gravado
antes do início da última geração não muda.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.semear_historico
"""
from __future__ import annotations

from backend.infrastructure.database import SessionLocal, create_tables, engine
from backend.services import treino_service


def main() -> None:
    print(f"[semear_historico] banco: {engine.url.render_as_string(hide_password=True)}", flush=True)
    create_tables()
    with SessionLocal() as db:
        n = treino_service.semear_historico(db)
    print(f"[semear_historico] {n} dias gravados", flush=True)


if __name__ == "__main__":
    main()
