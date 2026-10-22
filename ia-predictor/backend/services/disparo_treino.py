"""Onde o treino roda, conforme `TRAINING_RUNNER`.

  * `local` (padrão: desenvolvimento ou servidor com memória sobrando): numa thread da
    própria API. Após o upload, o agendador (`scheduler`) espera
    `RETRAIN_AFTER_UPLOAD_MINUTES`.
  * `externo` (API no Render grátis, ADR-015): a API não treina, porque não tem memória nem
    CPU para isso. A previsão é atualizada pelo script `backend/scripts/gravar_previsao.py`,
    rodado de outra máquina sobre o mesmo banco.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from backend.config import settings
from backend.infrastructure import scheduler
from backend.services import treino_service

log = logging.getLogger(__name__)


class TreinoForaDaApi(Exception):
    """`TRAINING_RUNNER=externo`: o treino não roda nesta API."""


def na_api() -> bool:
    return settings.TRAINING_RUNNER == "local"


def apos_upload() -> datetime | None:
    """Agenda o treino após uma planilha com venda nova. Devolve quando ele começa; None
    se esta API não treina (ou o agendador não está rodando)."""
    return scheduler.agendar_treino_pos_upload() if na_api() else None


def _treinar(user_id: int) -> None:
    try:
        treino_service.treinar("manual", user_id=user_id)
    except treino_service.TreinoEmAndamento:
        log.info("treino manual não iniciado: já existe um em andamento")
    except Exception:
        log.exception("treino manual falhou (registrado em retrain_history)")


def manual(user_id: int) -> None:
    """Treino pedido pelo botão "Atualizar os modelos", em segundo plano."""
    if not na_api():
        raise TreinoForaDaApi()
    threading.Thread(target=_treinar, args=(user_id,), daemon=True, name="treino-manual").start()
