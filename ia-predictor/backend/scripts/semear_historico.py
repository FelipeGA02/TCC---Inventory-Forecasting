"""Preenche o histórico da previsão (`forecast_history`) a partir do último treino concluído
do serviço de previsão, num banco em que esse treino é anterior à gravação do histórico.
Pode rodar mais de uma vez: dia já gravado antes do início da previsão não muda.

`--recriar` apaga o histórico antes — o que o treino antigo do painel gravou, se houver.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.semear_historico [--recriar]
"""
from __future__ import annotations

import argparse

from backend.infrastructure.database import SessionLocal, create_tables, engine
from backend.services import servico_previsao


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--recriar", action="store_true", help="apaga o histórico gravado antes de preencher")
    args = parser.parse_args()
    print(f"[semear_historico] banco: {engine.url.render_as_string(hide_password=True)}", flush=True)
    create_tables()
    with SessionLocal() as db:
        n = servico_previsao.semear_historico(db, recriar=args.recriar)
    print(f"[semear_historico] {n} dias gravados", flush=True)


if __name__ == "__main__":
    main()
