"""Treina a previsão (as 4 categorias e cada produto de grama, por loja) neste computador e
grava no banco de `DATABASE_URL` — o mesmo treino do botão "Treinar previsões".

Para a API que não treina (`TRAINING_RUNNER=externo`, Render grátis — ADR-015): a equipe
roda o script de uma máquina com memória e CPU, apontando para o mesmo banco (Neon). O
disparo fica em `forecast_jobs` com `trigger = script`, com o log de cada série, e é pulado
(`skipped`) se os dados não mudaram desde o último treino concluído. Não roda junto com um
treino em andamento.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.treinar_previsoes [--workers N]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from backend.config import settings
from backend.infrastructure.database import SessionLocal, create_tables, engine
from backend.services import servico_previsao


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workers", type=int, default=settings.TRAINING_WORKERS,
                        help=f"processos no treino (padrão TRAINING_WORKERS = {settings.TRAINING_WORKERS}; "
                             "proot/Termux: 1)")
    args = parser.parse_args()
    settings.TRAINING_WORKERS = max(1, args.workers)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    print(f"[treinar_previsoes] banco: {engine.url.render_as_string(hide_password=True)}", flush=True)
    create_tables()
    with SessionLocal() as db:
        if not servico_previsao.dados_alterados(db):
            print("[treinar_previsoes] os dados não mudaram desde o último treino: nada a treinar", flush=True)
    t0 = time.time()
    try:
        job = servico_previsao.treinar_agora(trigger="script")
    except servico_previsao.TreinoEmAndamento:
        print("[treinar_previsoes] já existe um treino em andamento", flush=True)
        return 1
    print(f"[treinar_previsoes] treino {job.id}: {job.status} em {time.time() - t0:.0f} s — {job.message}", flush=True)
    return 1 if job.status == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
