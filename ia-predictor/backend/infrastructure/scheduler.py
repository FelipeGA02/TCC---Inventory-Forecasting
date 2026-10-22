"""Agendador do treino semanal (APScheduler, dentro do processo da API).

Segunda às `RETRAIN_HOUR` (padrão 02:00) o treino roda sobre as vendas do banco e é
registrado como `skipped` em `retrain_history` quando não há venda nova desde o último
treino concluído (`treino_service.treinar(pular_sem_venda_nova=True)`).

A conferência diária do calendário (`DAILY_FORECAST_HOUR`, gerar de novo a previsão só se
`calendar_days` mudou) depende dos modelos ajustados em joblib, que o treino ainda não
grava (`model_artifacts.artifact_path` nulo); fica de fora até lá.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings

log = logging.getLogger(__name__)

_JOB_TREINO = "treino_semanal"
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
