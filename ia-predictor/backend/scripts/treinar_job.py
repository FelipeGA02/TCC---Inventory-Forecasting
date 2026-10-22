"""Entrada do Job de treino no Cloud Run (`TRAINING_RUNNER=cloud_run_job`).

Iniciado pela API (upload com venda nova ou botão "Atualizar os modelos") ou pelo Cloud
Scheduler (segunda 02:00). Assume o pedido `pending` mais antigo de `retrain_history`:

  * `upload`: espera `RETRAIN_AFTER_UPLOAD_MINUTES` sem planilha nova (várias planilhas
    seguidas geram um treino só) e treina, pulando se não houver venda nova;
  * `manual`: treina na hora;
  * sem pedido (Cloud Scheduler): treina só se houver venda nova.

Se chegar planilha durante o treino, a API não inicia outro Job (este está rodando):
ele treina de novo antes de terminar.

Uso (a partir de ia-predictor/): python -m backend.scripts.treinar_job
"""
from __future__ import annotations

import logging
import sys
from datetime import timedelta

from backend.config import settings
from backend.services import treino_service

log = logging.getLogger("treinar_job")
MAX_RODADAS = 3


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    espera = timedelta(minutes=settings.RETRAIN_AFTER_UPLOAD_MINUTES)
    pedido = treino_service.proximo_da_fila()
    if pedido is None:
        trigger, user_id, retrain_id = "scheduled", None, None
    else:
        retrain_id, trigger, user_id = pedido

    for rodada in range(1, MAX_RODADAS + 1):
        if trigger == "upload":
            log.info("esperando %s sem planilha nova", espera)
            treino_service.esperar_planilhas_paradas(espera)
        log.info("treino %s (rodada %d)", trigger, rodada)
        try:
            rid = treino_service.treinar(trigger, user_id=user_id, retrain_id=retrain_id,
                                         pular_sem_venda_nova=trigger != "manual")
        except treino_service.TreinoEmAndamento:
            log.info("já existe outro treino em andamento; nada a fazer")
            return 0
        log.info("treino concluído: retrain_history.id = %s", rid)
        if not treino_service.ha_planilha_pendente():
            return 0
        # planilha que chegou durante o treino: treina de novo, como após um upload
        trigger, user_id, retrain_id = "upload", None, None
    log.warning("ainda há planilha pendente após %d treinos; fica para o próximo", MAX_RODADAS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
