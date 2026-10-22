"""Treina os modelos sobre as vendas do banco e grava a previsão (ou importa um
`baseReal.json` já gerado).

Grava `retrain_history`, `model_artifacts`, `backtest_points`, `forecast_runs` e
`forecasts_cache` no banco de `DATABASE_URL` (SQLite local ou Neon). Precisa da carga
inicial feita (`python -m backend.scripts.carga_inicial`).

O treino completo (2 lojas, 26 rodadas de validação, um SARIMAX por produto regular) leva
~40 min com 8 processos. `--de-json` grava em segundos o resultado de um treino já rodado
pelo gerador do frontend (mesmo código, sobre os CSV do pré-processamento).

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.gravar_previsao [--workers N] [--salvar-json saida.json]
    python -m backend.scripts.gravar_previsao --de-json [caminho/baseReal.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from sqlalchemy import func, select

from backend.infrastructure.database import RetrainHistory, Sale, SessionLocal, engine
from backend.services import treino_service

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE_REAL = os.path.join(_REPO, "ia-predictor", "training_scripts", "output", "baseReal.json")


def log(msg: str) -> None:
    print(f"[gravar_previsao] {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--de-json", nargs="?", const=BASE_REAL, metavar="CAMINHO",
                        help=f"importa a previsão de um baseReal.json (padrão: {BASE_REAL})")
    parser.add_argument("--workers", type=int, default=None,
                        help="processos no treino dos produtos (padrão: TRAINING_WORKERS do .env)")
    parser.add_argument("--salvar-json", metavar="CAMINHO",
                        help="grava também o resultado do treino por loja num JSON (conferência)")
    args = parser.parse_args()
    t0 = time.time()

    log(f"banco: {engine.url.render_as_string(hide_password=True)}")
    with SessionLocal() as db:
        if not db.scalar(select(func.count()).select_from(Sale)):
            sys.exit("A tabela sales está vazia. Rode antes: python -m backend.scripts.carga_inicial")
        fim_base = db.scalar(select(func.max(Sale.sale_date)))

    try:
        if args.de_json:
            with open(args.de_json, encoding="utf-8") as fh:
                painel = json.load(fh)
            if painel["base"]["fim"] != str(fim_base):
                log(f"aviso: o JSON vai até {painel['base']['fim']} e o banco até {fim_base}")
            retrain_id = treino_service.importar_painel(painel)
        else:
            resultado = {}

            def ao_terminar(u, dados):
                resultado[u["id"]] = dados
                log(f"{u['nome']}: modelo {dados['modelo']['status']}, "
                    f"{sum(p['regular'] for p in dados['produtos'])} produtos regulares · {time.time() - t0:.0f}s")

            retrain_id = treino_service.treinar("manual", workers=args.workers, ao_terminar_unidade=ao_terminar)
            if args.salvar_json:
                with open(args.salvar_json, "w", encoding="utf-8") as fh:
                    json.dump(resultado, fh, ensure_ascii=False, default=str)
                log(f"resultado por loja em {args.salvar_json}")
    except treino_service.TreinoEmAndamento:
        sys.exit("Já existe um treino em andamento. Espere terminar.")

    with SessionLocal() as db:
        r = db.get(RetrainHistory, retrain_id)
        log(f"retrain_history #{r.id} ({r.trigger}): {r.status} · {r.message} · dados até {r.data_until} "
            f"· total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
