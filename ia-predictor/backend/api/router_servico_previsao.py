"""Serviço de previsão (`/api/v1/servico-previsao/*`) — **só admin**, em todas as rotas.

  * `GET  /status`: treino em andamento (com o progresso), o último disparo e se os dados
    mudaram desde o último treino concluído. A aba de notificações consulta isto.
  * `POST /treinos`: dispara o treino em segundo plano (202). Sem dados novos, registra o
    disparo como `skipped` e responde 200 sem treinar. 409 se já houver treino rodando;
    503 se esta API não treina (`TRAINING_RUNNER=externo`).
  * `GET  /treinos/{id}`, `/treinos/{id}/logs` e `/treinos/{id}/series`: o disparo, o log
    do treino e o resultado de cada série com a previsão dos próximos dias.

O treino em si está em `backend/services/servico_previsao.py`.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_admin
from backend.infrastructure.database import (
    Category,
    ForecastJob,
    ForecastJobLog,
    Product,
    SeriesForecast,
    SeriesModel,
    Unit,
    User,
    get_db,
)
from backend.schemas.servico_previsao import (
    ConfigServico,
    DisparoResposta,
    LogTreino,
    PrevisaoDia,
    SerieTreinada,
    StatusServico,
    TreinoServico,
)
from backend.services import servico_previsao

router = APIRouter(prefix="/servico-previsao", dependencies=[Depends(require_admin)])

_MSG_EM_ANDAMENTO = "Já existe um treino em andamento. Acompanhe o progresso nas notificações."
_MSG_INICIADO = "Treino iniciado em segundo plano. Acompanhe o progresso nas notificações."
_MSG_FORA = ("Nesta instalação a previsão é atualizada pela equipe do projeto, fora do sistema. "
             "Avise a equipe quando enviar planilhas novas.")
_MSG_NAO_ENCONTRADO = "Treino não encontrado."


def _treino(job: ForecastJob | None) -> TreinoServico | None:
    if job is None:
        return None
    return TreinoServico(
        id=job.id, status=job.status, criado_em=job.created_at, iniciado_em=job.started_at,
        concluido_em=job.finished_at, dados_ate=job.data_until, total_series=job.total_series,
        series_concluidas=job.done_series, progresso_pct=job.progress_pct, serie_atual=job.current_series,
        series_treinadas=job.series_trained, series_baixa_confianca=job.series_low_confidence,
        series_dados_insuficientes=job.series_insufficient, series_com_erro=job.series_failed,
        mensagem=job.message)


def _config() -> ConfigServico:
    c = servico_previsao.config_treino()
    return ConfigServico(m=c.m, d=c.d, D=c.D, janela_dias=c.janela_dias, origens=c.origens, passo_dias=c.passo,
                         horizonte_dias=c.horizonte, base=servico_previsao.BASE_TREINO,
                         categoria_produtos=servico_previsao.CATEGORIA_PRODUTOS)


def _job_ou_404(db: Session, treino_id: int) -> ForecastJob:
    job = db.get(ForecastJob, treino_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_NAO_ENCONTRADO)
    return job


@router.get("/status", response_model=StatusServico)
def status_servico(db: Session = Depends(get_db)) -> StatusServico:
    andamento = servico_previsao.em_andamento(db)
    concluido = servico_previsao.ultimo_concluido(db)
    return StatusServico(
        treino_na_api=servico_previsao.na_api(),
        em_andamento=_treino(andamento),
        ultimo=_treino(servico_previsao.ultimo(db)),
        ultimo_concluido_em=concluido.finished_at if concluido else None,
        # a impressão digital lê agregados de `sales`: não roda a cada consulta do progresso
        dados_alterados=None if andamento else servico_previsao.dados_alterados(db),
        config=_config())


@router.post("/treinos", response_model=DisparoResposta, status_code=status.HTTP_202_ACCEPTED,
             responses={200: {"description": "Dados sem alteração: disparo registrado como `skipped`"}})
def disparar(response: Response, user: User = Depends(require_admin)) -> DisparoResposta:
    try:
        job, iniciou = servico_previsao.iniciar(user.id)
    except servico_previsao.TreinoForaDaApi:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_MSG_FORA)
    except servico_previsao.TreinoEmAndamento:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_EM_ANDAMENTO)
    if not iniciou:
        response.status_code = status.HTTP_200_OK
    return DisparoResposta(iniciado=iniciou, mensagem=_MSG_INICIADO if iniciou else job.message,
                           treino=_treino(job))


@router.get("/treinos/{treino_id}", response_model=TreinoServico)
def treino(treino_id: int, db: Session = Depends(get_db)) -> TreinoServico:
    return _treino(_job_ou_404(db, treino_id))


@router.get("/treinos/{treino_id}/logs", response_model=list[LogTreino])
def logs(treino_id: int, apos_id: int = Query(0, ge=0, description="Só linhas com id maior (leitura incremental)"),
         limite: int = Query(500, ge=1, le=2000), db: Session = Depends(get_db)) -> list[LogTreino]:
    _job_ou_404(db, treino_id)
    linhas = db.scalars(select(ForecastJobLog)
                        .where(ForecastJobLog.job_id == treino_id, ForecastJobLog.id > apos_id)
                        .order_by(ForecastJobLog.id).limit(limite))
    return [LogTreino(id=l.id, registrado_em=l.logged_at, nivel=l.level, serie=l.series_key, mensagem=l.message)
            for l in linhas]


@router.get("/treinos/{treino_id}/series", response_model=list[SerieTreinada])
def series(treino_id: int, db: Session = Depends(get_db)) -> list[SerieTreinada]:
    _job_ou_404(db, treino_id)
    linhas = db.execute(
        select(SeriesModel, Unit.name, Category.name, Product.name)
        .join(Unit, Unit.id == SeriesModel.unit_id)
        .outerjoin(Category, Category.id == SeriesModel.category_id)
        .outerjoin(Product, Product.code == SeriesModel.product_code)
        .where(SeriesModel.job_id == treino_id)
        .order_by(SeriesModel.unit_id, SeriesModel.level, SeriesModel.id)).all()
    previsoes: dict[int, list[PrevisaoDia]] = defaultdict(list)
    ids = [m.id for m, *_ in linhas]
    if ids:
        for p in db.scalars(select(SeriesForecast).where(SeriesForecast.model_id.in_(ids))
                            .order_by(SeriesForecast.model_id, SeriesForecast.forecast_date)):
            previsoes[p.model_id].append(PrevisaoDia(data=p.forecast_date, previsto=p.predicted,
                                                     inf_95=p.lower_95, sup_95=p.upper_95))
    return [SerieTreinada(
        id=m.id, loja=m.unit_id, loja_nome=loja, nivel=m.level, categoria=m.category_id,
        produto_codigo=m.product_code, nome=(produto if m.level == "product" else categoria) or m.series_key,
        status=m.status, ordem=m.sarimax_order, ordem_sazonal=m.seasonal_order, aic=m.aic, mase=m.mase,
        cobertura_ic95_pct=m.ci95_coverage_pct, metricas=m.metrics, mensagem=m.message,
        previsao=previsoes.get(m.id, [])) for m, loja, categoria, produto in linhas]
