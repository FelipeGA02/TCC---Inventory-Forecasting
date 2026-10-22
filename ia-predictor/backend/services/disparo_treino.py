"""Onde o treino roda, conforme `TRAINING_RUNNER`.

  * `local` (padrão, desenvolvimento ou servidor sempre ligado): numa thread da própria API.
    Após o upload, o agendador (`scheduler`) espera `RETRAIN_AFTER_UPLOAD_MINUTES`.
  * `cloud_run_job` (Cloud Run): a API só registra o pedido (`pending` em `retrain_history`)
    e inicia o Job de treino (`backend/scripts/treinar_job.py`), que faz a espera após o
    upload e o treino. No Cloud Run a API só tem CPU durante as requisições, então não
    pode treinar nem esperar em segundo plano.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from backend.config import settings
from backend.infrastructure import cloud_run_job, scheduler
from backend.services import treino_service

log = logging.getLogger(__name__)


def no_job() -> bool:
    return settings.TRAINING_RUNNER == "cloud_run_job"


def _pedir_ao_job(trigger: str, user_id: int | None) -> None:
    pedido = treino_service.enfileirar(trigger, user_id)
    if pedido is None:
        return  # já há treino na fila ou rodando: ele inclui esta planilha
    try:
        cloud_run_job.executar(settings.CLOUD_RUN_JOB)
    except Exception as erro:
        treino_service.marcar_erro(pedido, erro)
        raise


def apos_upload(user_id: int | None) -> datetime | None:
    """Pede o treino após uma planilha com venda nova. Devolve quando ele deve começar; None
    se não foi possível pedir (fica para o treino semanal ou o botão "Atualizar")."""
    if not no_job():
        return scheduler.agendar_treino_pos_upload()
    try:
        _pedir_ao_job("upload", user_id)
    except Exception:
        log.exception("não foi possível iniciar o Job de treino após o upload")
        return None
    return datetime.now() + timedelta(minutes=settings.RETRAIN_AFTER_UPLOAD_MINUTES)


def _treinar_na_api(user_id: int) -> None:
    try:
        treino_service.treinar("manual", user_id=user_id)
    except treino_service.TreinoEmAndamento:
        log.info("treino manual não iniciado: já existe um em andamento")
    except Exception:
        log.exception("treino manual falhou (registrado em retrain_history)")


def manual(user_id: int) -> None:
    """Treino pedido pelo botão "Atualizar os modelos" (quem chama já conferiu que não há
    outro em andamento)."""
    if no_job():
        _pedir_ao_job("manual", user_id)
    else:
        threading.Thread(target=_treinar_na_api, args=(user_id,), daemon=True, name="treino-manual").start()
