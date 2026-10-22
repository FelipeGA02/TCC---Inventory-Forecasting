"""Treino dos modelos e gravação da previsão no banco.

O treino é o de `training_scripts/frontend_mock/gerar_dados_frontend.py` (`gerar_unidade`:
SARIMAX da loja, desagregação loja → categoria e SARIMAX por produto regular, com o
walk-forward de 26 rodadas), rodado sobre as vendas e o calendário do banco. O resultado
de cada loja vai para:

  * `retrain_history`: a execução (trigger, período, configuração, contagens);
  * `model_artifacts`: um previsor por loja, por categoria e por produto regular;
  * `backtest_points`: previsto × real × naïve de cada dia do walk-forward;
  * `forecast_runs` + `forecasts_cache`: a previsão dos próximos dias.

`importar_painel()` grava as mesmas tabelas a partir de um `baseReal.json` já gerado — o
treino completo leva ~40 min, e o JSON é o resultado do mesmo código.

Com `TRAINING_RUNNER=externo` (API no Render, ADR-015) a API não treina: o treino é o script
`backend/scripts/gravar_previsao.py`, rodado de outra máquina sobre o mesmo banco.

Os modelos ajustados não são guardados em joblib (`artifact_path` fica nulo): o gerador
não devolve o objeto ajustado. Uma nova previsão exige treinar de novo.
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from backend.config import settings
from backend.infrastructure.database import (
    BacktestPoint,
    Category,
    ForecastCache,
    ForecastRun,
    ModelArtifact,
    ProcessingLog,
    RetrainHistory,
    SessionLocal,
    Unit,
)
from backend.services import base_vendas
from training_scripts.frontend_mock import gerar_dados_frontend as gerador
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA

# Chaves das métricas do walk-forward: painel (PT-BR, `MetricasModelo` do front) ↔ banco
# (`model_artifacts.metrics`, inglês). `mase` e `cobertura_ic95_pct` são colunas.
METRICAS_EN = {
    "rodadas": "folds",
    "rodadas_vence_naive": "folds_beating_naive",
    "dias_avaliados": "days_evaluated",
    "mae": "mae",
    "erro_relativo_naive": "relative_error_naive",
    "largura_ic95": "ci95_width",
    "venda_media_dia": "mean_daily_sales",
    "previsto_sobre_real_pct": "forecast_to_actual_pct",
    "erro_total_14d_pct": "total_error_14d_pct",
}
PARAMS_EN = {
    "aic": "aic",
    "transformacao": "transformation",
    "janela": "window_type",
    "janela_dias": "window_days",
    "base": "training_base",
    "exogenas": "exog_features",
}

# Um treino por vez neste processo; um `running` com mais de 3 h é de um processo que caiu.
_TRAVA = threading.Lock()
_TREINO_TRAVADO_APOS = timedelta(hours=3)

# Planilha com venda nova que ainda não entrou em nenhum treino concluído.
_PLANILHA_NAO_USADA = (ProcessingLog.status == "done", ProcessingLog.rows_added > 0,
                       ProcessingLog.retrain_id.is_(None))


class TreinoEmAndamento(Exception):
    """Já existe um treino rodando."""


def configuracao() -> dict:
    """Configuração do treino, no formato de `BaseReal.configuracao` do front. Fica em
    `retrain_history.config`: o treino agendado é pulado se ela e as vendas não mudaram."""
    return {
        "horizonte_dias": gerador.HORIZONTE, "m": gerador.M, "alpha_ic": gerador.ALPHA,
        "janela_participacao_dias": gerador.JANELA_SHARE_DIAS,
        "primeira_origem_validacao": str(gerador.PRIMEIRA_ORIGEM.date()),
        "passo_origem_dias": gerador.PASSO_ORIGEM,
        "limiar_encomenda_un": LIMIAR_QTD_VENDA,
        "criterio_regular": {"adi_corte": gerador.ADI_CORTE, "min_span_dias": gerador.MIN_SPAN_DIAS,
                             "fonte": "Syntetos, Boylan & Croston (2005)"},
        "modelo_loja": "SARIMAX, base sem encomendas, sem log1p, d = 1, janela deslizante",
        "modelo_produto": "SARIMAX por produto regular, base sem encomendas, sem log1p, d = 0",
    }


def treino_em_andamento(db: Session) -> RetrainHistory | None:
    limite = datetime.now() - _TREINO_TRAVADO_APOS
    return db.scalar(
        select(RetrainHistory)
        .where(RetrainHistory.status == "running", RetrainHistory.started_at >= limite)
        .order_by(RetrainHistory.id.desc())
    )


def ha_treino_rodando(db: Session) -> bool:
    """Treino em andamento neste processo ou registrado por outro (`running` recente)."""
    return _TRAVA.locked() or treino_em_andamento(db) is not None


# --------------------------------------------------------------------------- #
# Gravação
# --------------------------------------------------------------------------- #
def origem_da_rodada(dia: date, primeira: date, passo: int) -> date:
    """Rodadas a cada `passo` dias com horizonte `passo`: cada dia tem uma só origem."""
    return primeira + timedelta(days=((dia - primeira).days // passo) * passo)


def _metricas_en(m: dict | None) -> dict | None:
    return None if m is None else {en: m.get(pt) for pt, en in METRICAS_EN.items()}


def _novo_modelo(db: Session, retrain_id: int, unit_id: str, level: str, status: str, *,
                 category_id=None, product_code=None, ordem=None, ordem_sazonal=None,
                 metricas=None, params=None) -> int:
    modelo = ModelArtifact(
        retrain_id=retrain_id, unit_id=unit_id, category_id=category_id, product_code=product_code,
        level=level, status=status, sarimax_order=ordem, seasonal_order=ordem_sazonal,
        mase=None if metricas is None else metricas["mase"],
        ci95_coverage_pct=None if metricas is None else metricas["cobertura_ic95_pct"],
        params=params, metrics=_metricas_en(metricas),
    )
    db.add(modelo)
    db.flush()
    return modelo.id


def _pontos_backtest(model_id: int, backtest: list[dict], primeira: date, passo: int) -> list[dict]:
    pontos = []
    for p in backtest:
        dia = date.fromisoformat(p["data"])
        pontos.append({"model_id": model_id, "origin_date": origem_da_rodada(dia, primeira, passo), "day": dia,
                       "predicted": p["previsto"], "lower_95": p["inf"], "upper_95": p["sup"],
                       "actual": p["real"], "naive": p["naive"]})
    return pontos


def _pontos_previsao(run_id: int, model_id: int, level: str, previsao: list[dict]) -> list[dict]:
    return [{"run_id": run_id, "model_id": model_id, "level": level,
             "forecast_date": date.fromisoformat(d["data"]), "predicted": d["previsto"],
             "lower_95": d["inf"], "upper_95": d["sup"]} for d in previsao]


def gravar_unidade(db: Session, retrain_id: int, run_id: int, unidade: dict, config: dict) -> int:
    """Grava os previsores de uma loja (formato `UnidadeDados` do painel) e devolve quantos
    produtos têm previsão."""
    primeira = date.fromisoformat(config["primeira_origem_validacao"])
    passo = int(config["passo_origem_dias"])
    uid = unidade["id"]
    backtest, previsao = [], []

    m = unidade["modelo"]
    loja = _novo_modelo(db, retrain_id, uid, "unit", m["status"], ordem=m["ordem"],
                        ordem_sazonal=m["ordem_sazonal"], metricas=m["metricas"],
                        params={en: m[pt] for pt, en in PARAMS_EN.items()})
    backtest += _pontos_backtest(loja, unidade["backtest"], primeira, passo)
    previsao += _pontos_previsao(run_id, loja, "unit", unidade["previsao"])

    semanas = int(config["janela_participacao_dias"]) // 7
    for cat, d in unidade["desagregacao"].items():
        mid = _novo_modelo(db, retrain_id, uid, "category", d["status"], category_id=cat,
                           metricas=d["metricas"], params={"share_window_weeks": semanas})
        backtest += _pontos_backtest(mid, d["backtest"], primeira, passo)
        previsao += _pontos_previsao(run_id, mid, "category", [
            {"data": dia["data"], **dia["categorias"][cat]} for dia in unidade["previsao"]])

    com_previsao = 0
    for p in unidade["produtos"]:
        if not p["regular"]:
            continue  # produto irregular: só histórico, calculado de `sales`
        mod = p["modelo"]
        if mod is None:  # nenhuma ordem convergiu
            _novo_modelo(db, retrain_id, uid, "product", "insufficient_data", product_code=p["codigo"])
            continue
        mid = _novo_modelo(db, retrain_id, uid, "product", mod["status"], product_code=p["codigo"],
                           ordem=mod["ordem"], ordem_sazonal=mod["ordem_sazonal"], metricas=mod["metricas"],
                           params={"transformation": "nenhuma", "training_base": unidade["modelo"]["base"]})
        backtest += _pontos_backtest(mid, p.get("backtest") or [], primeira, passo)
        previsao += _pontos_previsao(run_id, mid, "product", p["previsao"])
        com_previsao += bool(p["previsao"])

    if backtest:
        db.execute(insert(BacktestPoint), backtest)
    if previsao:
        db.execute(insert(ForecastCache), previsao)
    return com_previsao


def _abrir_execucao(trigger: str, user_id: int | None, config: dict) -> int:
    with SessionLocal() as db:
        if treino_em_andamento(db) is not None:
            raise TreinoEmAndamento()
        r = RetrainHistory(trigger=trigger, status="running", user_id=user_id, config=config)
        db.add(r)
        db.commit()
        return r.id


def _gravar_resultado(retrain_id: int, trigger_run: str, unidades: list[dict], data_until: date) -> int:
    """Grava os previsores e a geração da previsão; devolve o id da `forecast_runs`."""
    with SessionLocal() as db:
        retrain = db.get(RetrainHistory, retrain_id)
        datas = [date.fromisoformat(d["data"]) for u in unidades for d in u["previsao"]]
        run = ForecastRun(retrain_id=retrain_id, trigger=trigger_run, status="running",
                          start_date=min(datas), end_date=max(datas))
        db.add(run)
        db.flush()
        produtos = sum(gravar_unidade(db, retrain_id, run.id, u, retrain.config) for u in unidades)
        agora = datetime.now()
        run.status, run.finished_at = "done", agora
        run.units_served, run.products_served = len(unidades), produtos
        retrain.status, retrain.finished_at, retrain.data_until = "done", agora, data_until
        retrain.units_trained = len(unidades)
        retrain.products_modeled = sum(1 for u in unidades for p in u["produtos"] if p["regular"])
        retrain.message = f"{len(unidades)} lojas e {retrain.products_modeled} produtos regulares"
        # planilhas já carregadas quando o treino começou entram nele (as que chegaram
        # durante o treino ficam para o próximo)
        db.execute(update(ProcessingLog)
                   .where(*_PLANILHA_NAO_USADA, ProcessingLog.finished_at <= retrain.started_at)
                   .values(retrain_id=retrain_id))
        db.commit()
        return run.id


def _marcar_erro(retrain_id: int, erro: Exception) -> None:
    with SessionLocal() as db:
        r = db.get(RetrainHistory, retrain_id)
        r.status, r.finished_at = "error", datetime.now()
        r.message = f"{type(erro).__name__}: {erro}"[:500]
        db.commit()


# --------------------------------------------------------------------------- #
# Casos de uso
# --------------------------------------------------------------------------- #
def treinar(trigger: str = "manual", user_id: int | None = None, workers: int | None = None,
            pular_sem_venda_nova: bool = False, ao_terminar_unidade=None) -> int:
    """Treina as lojas sobre o banco e grava tudo. Devolve o id de `retrain_history`.

    Com `pular_sem_venda_nova` (treino agendado ou após upload), registra `skipped` se o
    último treino `done` usou as mesmas vendas — mesmo `data_until` e nenhuma planilha com
    venda nova ainda não usada (`processing_log.retrain_id` nulo) — e a mesma configuração.
    """
    workers = workers or settings.TRAINING_WORKERS
    if not _TRAVA.acquire(blocking=False):
        raise TreinoEmAndamento()
    try:
        config = configuracao()
        retrain_id = _abrir_execucao(trigger, user_id, config)
        try:
            with SessionLocal() as db:
                df = base_vendas.carregar_vendas(db)
                cal = base_vendas.carregar_calendario(db)
                unidades = base_vendas.carregar_lojas(db)
                ultimo = db.scalar(select(RetrainHistory).where(RetrainHistory.status == "done")
                                   .order_by(RetrainHistory.id.desc()))
                pendentes = db.scalar(select(func.count()).select_from(ProcessingLog)
                                      .where(*_PLANILHA_NAO_USADA))
            data_until = df["emissao"].max().date()
            if pular_sem_venda_nova and ultimo is not None and ultimo.data_until == data_until \
                    and not pendentes and ultimo.config == config:
                with SessionLocal() as db:
                    r = db.get(RetrainHistory, retrain_id)
                    r.status, r.finished_at, r.data_until = "skipped", datetime.now(), data_until
                    r.message = "Sem venda nova desde o último treino."
                    db.commit()
                return retrain_id

            resultado = []
            for u in unidades:
                resultado.append(gerador.gerar_unidade(df, cal, u, workers))
                if ao_terminar_unidade:
                    ao_terminar_unidade(u, resultado[-1])
            _gravar_resultado(retrain_id, "retrain", resultado, data_until)
            return retrain_id
        except Exception as erro:
            _marcar_erro(retrain_id, erro)
            raise
    finally:
        _TRAVA.release()


def importar_painel(painel: dict, user_id: int | None = None) -> int:
    """Grava a previsão de um `baseReal.json` (saída de `gerar_dados_frontend`) como uma
    execução `trigger = import`. As vendas precisam já estar no banco (carga inicial)."""
    if not _TRAVA.acquire(blocking=False):
        raise TreinoEmAndamento()
    try:
        config = {**configuracao(), **painel.get("configuracao", {})}
        retrain_id = _abrir_execucao("import", user_id, config)
        try:
            with SessionLocal() as db:
                cats = set(db.scalars(select(Category.id)))
                lojas = set(db.scalars(select(Unit.id)))
            for u in painel["unidades"]:
                if u["id"] not in lojas or not set(u["desagregacao"]) <= cats:
                    raise ValueError(f"loja ou categoria do JSON sem cadastro no banco: {u['id']}")
            data_until = pd.Timestamp(painel["base"]["fim"]).date()
            _gravar_resultado(retrain_id, "retrain", painel["unidades"], data_until)
            return retrain_id
        except Exception as erro:
            _marcar_erro(retrain_id, erro)
            raise
    finally:
        _TRAVA.release()
