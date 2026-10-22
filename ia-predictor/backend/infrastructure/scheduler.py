"""Agendador do treino (APScheduler, dentro do processo da API).

Dois gatilhos, ambos registrados como `skipped` em `retrain_history` quando não há venda
nova desde o último treino concluído (`treino_service.treinar(pular_sem_venda_nova=True)`):

  * **após o upload**: planilha com venda nova agenda um treino para daqui a
    `RETRAIN_AFTER_UPLOAD_MINUTES` (padrão 10 min). Outra planilha nesse intervalo adia o
    treino, então várias planilhas seguidas geram um treino só. Se já houver treino
    rodando, tenta de novo 30 min depois;
  * **semanal**: segunda às `RETRAIN_HOUR` (padrão 02:00), rede de segurança para o caso
    de a API estar desligada na hora do treino após o upload.

A conferência diária do calendário (`DAILY_FORECAST_HOUR`, gerar de novo a previsão só se
`calendar_days` mudou) depende dos modelos ajustados em joblib, que o treino ainda não
grava (`model_artifacts.artifact_path` nulo); fica de fora até lá.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from backend.config import settings

log = logging.getLogger(__name__)

_JOB_TREINO = "treino_semanal"
_JOB_POS_UPLOAD = "treino_pos_upload"
_REPETIR_SE_OCUPADO = timedelta(minutes=30)
_scheduler: BackgroundScheduler | None = None


def _treino_agendado() -> None:
    # import tardio: o treino puxa statsmodels e os scripts de treino só quando roda
    from backend.services import treino_service

    try:
        treino_service.treinar("scheduled", pular_sem_venda_nova=True)
    except treino_service.TreinoEmAndamento:
        log.info("treino agendado pulado: já existe um treino em andamento")
    except Exception:
        log.exception("treino agendado falhou (registrado em retrain_history)")


def _treino_pos_upload() -> None:
    from backend.services import treino_service

    try:
        treino_service.treinar("upload", pular_sem_venda_nova=True)
    except treino_service.TreinoEmAndamento:
        # o treino em andamento pode ter lido as vendas antes da planilha: tenta de novo
        # (é pulado se aquele treino já as cobriu)
        log.info("treino após upload adiado: já existe um treino em andamento")
        _agendar_pos_upload(datetime.now(_scheduler.timezone) + _REPETIR_SE_OCUPADO)
    except Exception:
        log.exception("treino após upload falhou (registrado em retrain_history)")


def _agendar_pos_upload(quando: datetime) -> datetime | None:
    if _scheduler is None:
        return None
    job = _scheduler.add_job(_treino_pos_upload, DateTrigger(run_date=quando), id=_JOB_POS_UPLOAD,
                             replace_existing=True, max_instances=1, misfire_grace_time=None)
    return job.next_run_time


def agendar_treino_pos_upload() -> datetime | None:
    """Agenda (ou adia) o treino após um upload com venda nova. Devolve quando ele começa;
    None se o agendador não está rodando (fica para o treino semanal)."""
    if _scheduler is None:
        return None
    espera = timedelta(minutes=settings.RETRAIN_AFTER_UPLOAD_MINUTES)
    return _agendar_pos_upload(datetime.now(_scheduler.timezone) + espera)


def treino_pos_upload_agendado() -> datetime | None:
    if _scheduler is None:
        return None
    job = _scheduler.get_job(_JOB_POS_UPLOAD)
    return None if job is None else job.next_run_time


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(
        _treino_agendado,
        CronTrigger(day_of_week=settings.RETRAIN_DAY_OF_WEEK, hour=settings.RETRAIN_HOUR, minute=0),
        id=_JOB_TREINO,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def proximo_treino() -> datetime | None:
    """Data e hora do próximo treino agendado (None se o agendador não está rodando)."""
    if _scheduler is None:
        return None
    job = _scheduler.get_job(_JOB_TREINO)
    return None if job is None else job.next_run_time


def esta_rodando() -> bool:
    return _scheduler is not None and _scheduler.running
