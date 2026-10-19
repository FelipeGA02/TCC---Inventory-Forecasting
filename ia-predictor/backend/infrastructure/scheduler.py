"""Agendamento do retreino + previsao semanal (APScheduler).

Roda no dia da carga do cliente (`RETRAIN_DAY_OF_WEEK`, terca) as `RETRAIN_HOUR` (23:00).
Se a base em `data/processed/` nao mudou desde a ultima execucao concluida (hash do
manifesto), a rotina so registra no log e sai — pode ser disparada de novo sem custo.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings

_log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def job_previsao_semanal() -> None:
    from backend.services.forecast_service import executar_previsao_semanal
    try:
        executar_previsao_semanal(gatilho="scheduled")
    except Exception:  # noqa: BLE001 — a falha ja fica em results/logs; o scheduler segue
        _log.exception("Previsão semanal agendada falhou")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(job_previsao_semanal, CronTrigger(
            day_of_week=settings.RETRAIN_DAY_OF_WEEK, hour=settings.RETRAIN_HOUR, minute=0),
            id="previsao_semanal", replace_existing=True, max_instances=1, coalesce=True)
        _scheduler.start()
    return _scheduler
