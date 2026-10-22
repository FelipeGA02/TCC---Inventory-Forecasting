"""Status dos modelos (`GET /models/status`) e treino manual (`POST /models/retrain`, admin).

O treino roda numa thread da API e leva dezenas de minutos (2 lojas, 26 rodadas de
validação, um SARIMAX por produto regular). O andamento fica em `retrain_history`.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_admin
from backend.infrastructure import scheduler
from backend.infrastructure.database import ForecastCache, ModelArtifact, RetrainHistory, Unit, User, get_db
from backend.schemas.models import ModelMetrics, ModelStatusResponse, RetrainResponse, UnitModelStatus
from backend.services import painel_service, treino_service

log = logging.getLogger(__name__)
router = APIRouter()

_MSG_TREINO_EM_ANDAMENTO = "Atualização já em andamento. Tente novamente em alguns minutos."
_MSG_TREINO_INICIADO = "Atualização dos modelos iniciada em segundo plano. Leva cerca de 40 minutos."


def _ordem(valores: list | None) -> str | None:
    return None if valores is None else "(" + ",".join(str(v) for v in valores) + ")"


def _metricas(m: ModelArtifact) -> ModelMetrics:
    met = m.metrics or {}
    relativo = met.get("relative_error_naive")
    rotulo = None
    if relativo is not None:
        ganho = round((1 - relativo) * 100)
        rotulo = (f"Erra {ganho}% menos que repetir a semana anterior" if ganho >= 0
                  else f"Erra {-ganho}% mais que repetir a semana anterior")
    return ModelMetrics(MASE=m.mase, IC_coverage_pct=m.ci95_coverage_pct, MAE=met.get("mae"),
                        accuracy_label=rotulo)


@router.get("/models/status", response_model=ModelStatusResponse)
def models_status(db: Session = Depends(get_db)) -> ModelStatusResponse:
    resposta = ModelStatusResponse(next_retrain_at=scheduler.proximo_treino(),
                                   is_training=treino_service.ha_treino_rodando(db))
    ultimo = db.scalar(select(RetrainHistory).where(RetrainHistory.status.in_(["done", "skipped", "error"]))
                       .order_by(RetrainHistory.id.desc()))
    if ultimo is not None:
        resposta.last_retrain_summary = ultimo.message

    geracao = painel_service.ultima_geracao(db)
    if geracao is None:
        return resposta
    run, retrain = geracao
    resposta.last_retrain_at = retrain.finished_at
    resposta.last_forecast_generation_at = run.finished_at
    resposta.forecast_until = db.scalar(select(func.max(ForecastCache.forecast_date))
                                        .where(ForecastCache.run_id == run.id))
    resposta.skus_covered = run.products_served

    nomes = {u.id: u.name for u in db.scalars(select(Unit))}
    lojas = list(db.scalars(select(ModelArtifact).where(ModelArtifact.retrain_id == retrain.id,
                                                        ModelArtifact.level == "unit")
                            .order_by(ModelArtifact.unit_id)))
    resposta.total_models = len(lojas)
    resposta.trained_models = sum(m.status == "trained" for m in lojas)
    resposta.low_confidence_models = sum(m.status == "low_confidence" for m in lojas)
    resposta.failed_models = sum(m.status == "error" for m in lojas)
    resposta.insufficient_data_models = sum(m.status == "insufficient_data" for m in lojas)
    resposta.units = [UnitModelStatus(unidade=nomes.get(m.unit_id, m.unit_id), status=m.status,
                                      sarimax_order=_ordem(m.sarimax_order),
                                      seasonal_order=_ordem(m.seasonal_order),
                                      metrics=_metricas(m), trained_at=m.trained_at)
                      for m in lojas]
    return resposta


def _treinar_em_segundo_plano(user_id: int) -> None:
    try:
        treino_service.treinar("manual", user_id=user_id)
    except treino_service.TreinoEmAndamento:
        log.info("treino manual não iniciado: já existe um em andamento")
    except Exception:
        log.exception("treino manual falhou (registrado em retrain_history)")


@router.post("/models/retrain", response_model=RetrainResponse, status_code=status.HTTP_202_ACCEPTED)
def retrain(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> RetrainResponse:
    if treino_service.ha_treino_rodando(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_TREINO_EM_ANDAMENTO)
    threading.Thread(target=_treinar_em_segundo_plano, args=(user.id,), daemon=True,
                     name="treino-manual").start()
    return RetrainResponse(message=_MSG_TREINO_INICIADO, started_at=datetime.now())
