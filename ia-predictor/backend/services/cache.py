"""Cache em memória das leituras pesadas (base de vendas, painel, análises).

Cada valor fica guardado com a "versão" dos dados de que depende — o último id de venda,
de planilha, de treino concluído da previsão e a última alteração do calendário. Carga de
planilha, treino ou mudança no calendário mudam a versão, e a próxima leitura recalcula. Só a versão
mais recente de cada nome fica na memória.
"""
from __future__ import annotations

import threading
from typing import Callable, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.infrastructure.database import CalendarDay, ForecastJob, ProcessingLog, Sale

T = TypeVar("T")

_valores: dict[str, tuple[tuple, object]] = {}
_travas: dict[str, threading.Lock] = {}
_trava_geral = threading.Lock()


def versao_dados(db: Session) -> tuple:
    return (
        db.scalar(select(func.max(Sale.id))),
        db.scalar(select(func.count()).select_from(Sale)),
        db.scalar(select(func.max(ProcessingLog.id))),
        db.scalar(select(func.max(ForecastJob.id)).where(ForecastJob.status == "done")),
        str(db.scalar(select(func.max(CalendarDay.updated_at)))),
    )


def obter(nome: str, versao: tuple, construir: Callable[[], T]) -> T:
    """Valor de `nome` na `versao`; calcula com `construir()` se mudou. Requisições
    simultâneas esperam o primeiro cálculo em vez de repetir."""
    with _trava_geral:
        trava = _travas.setdefault(nome, threading.Lock())
    with trava:
        guardado = _valores.get(nome)
        if guardado is not None and guardado[0] == versao:
            return guardado[1]  # type: ignore[return-value]
        valor = construir()
        _valores[nome] = (versao, valor)
        return valor


def limpar() -> None:
    _valores.clear()
