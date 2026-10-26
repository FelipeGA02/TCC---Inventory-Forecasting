"""Serviço de previsão: treina as 4 categorias e todos os produtos de grama de cada loja.

É o treino da previsão do sistema (ADR-017): a previsão de 14 dias, o histórico e os
relatórios leem o último disparo concluído. Disparado pelo botão "Treinar previsões" (só
admin), roda em segundo plano numa thread da API; com `TRAINING_RUNNER=externo` (API no
Render) roda pelo script `backend/scripts/treinar_previsoes.py`, de outra máquina, com o
mesmo código (`treinar_agora`). Não há agendador: a loja envia as planilhas e treina. Grava
tudo no banco de `DATABASE_URL` (o Neon, em produção — ADR-014):

  * `forecast_jobs`: o disparo, com o andamento que a aba de notificações mostra;
  * `forecast_job_logs`: o log do treino, série a série;
  * `series_models` + `series_forecasts` + `series_backtest_points`: o resultado de cada
    série — ordem, AIC, métricas do walk-forward, previsão dos próximos 14 dias e os pontos
    do walk-forward;
  * `forecast_history`: o previsto de cada dia, congelado quando o dia passa — o histórico
    da previsão na tela (`domain.historico_previsao`);
  * `processing_log.forecast_job_id`: as planilhas que entraram pela primeira vez neste
    treino ("a previsão mudou por causa de qual envio?").

Ao concluir, apaga o walk-forward (`series_backtest_points`) dos treinos mais antigos que os
últimos `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` concluídos — é a tabela que mais cresce (~13
mil linhas por treino) e o que a tela usa dela já está congelado em `forecast_history`.
Modelos, métricas e previsões de todos os treinos ficam.

Histórico da previsão
---------------------
Gravado só quando o disparo termina `done`, na mesma transação que muda o status: previsão
de treino que falhou ou caiu no meio a loja nunca viu, então não pode congelar. Em cada loja
do treino, apaga os dias a partir do início da previsão nova (dia seguinte à última venda),
de todas as séries — inclusive a que desta vez ficou sem modelo, cujo número sai da tela —,
grava os 14 dias novos e preenche com o 1º dia das janelas do walk-forward só os dias
anteriores ainda vazios. `skipped` não muda nada.

Só treina se os dados mudaram
-----------------------------
Cada disparo calcula a impressão digital (SHA-256) das vendas, do calendário e do catálogo
— contagem, maior id, soma das quantidades, período, marcação de encomenda, última
alteração do calendário e dos produtos. Se ela é igual à do último treino concluído, o
disparo é registrado como `skipped` e nada é treinado. Treino que terminou em erro não
conta: o próximo disparo treina.

Modelo (fixo, decisão registrada na docstring de `domain/models/trainer.py`)
---------------------------------------------------------------------------
SARIMAX com m = 7, d = 0, D = 0 e constante; ordem (p, q)(P, Q) por AIC; exógenas de
calendário; série diária do **fluxo** — vendas sem as encomendas acima de 2.000 unidades
no documento (ADR-013), a mesma base dos experimentos que fixaram a receita. Walk-forward
com janela deslizante de `FORECAST_SERVICE_WINDOW_DAYS` dias e origem andando 1 dia por
`FORECAST_SERVICE_WF_ORIGINS` origens, cada uma prevendo `FORECAST_HORIZON_DAYS` dias.
Do ajuste final ficam os coeficientes (`series_models.params`) e o diagnóstico dos resíduos
(Ljung-Box e Shapiro-Wilk, em `metrics`, citado no log quando p ≤ 0,05 — não muda o
status). A configuração gravada no disparo leva a versão do código (`versao_codigo`).

Série que não tem dados para isso (histórico curto, produto que quase não vende) fica
registrada como `insufficient_data`, com o motivo, sem previsão — "todos os produtos de
grama" entram no log, mas só os que têm venda suficiente recebem modelo.

Paralelismo
-----------
Com `TRAINING_WORKERS > 1` cada série vai para um processo (`spawn`, seguro dentro de uma
API com threads). Se o pool quebrar — acontece em ambientes como o proot/Termux de
desenvolvimento —, o log registra e as séries que faltam seguem uma a uma, sem perder o
que já foi gravado.
"""
from __future__ import annotations

import hashlib
import json
import logging
import multiprocessing
import os
import subprocess
import threading
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.orm import Session

from backend.config import settings
from backend.domain import historico_previsao
from backend.domain.features.exogenous import matriz_exogena
from backend.domain.features.time_series import serie_diaria
from backend.domain.models import evaluator
from backend.domain.models.trainer import (
    NIVEL_CATEGORIA,
    NIVEL_PRODUTO,
    ConfigTreino,
    ResultadoSerie,
    motivo_inelegivel,
    treinar_serie,
    treinar_serie_tarefa,
)
from backend.infrastructure.database import (
    CalendarDay,
    Category,
    ForecastHistory,
    ForecastJob,
    ForecastJobLog,
    ProcessingLog,
    Product,
    Sale,
    SeriesBacktestPoint,
    SeriesForecast,
    SeriesModel,
    SessionLocal,
)
from backend.services import base_vendas

log = logging.getLogger(__name__)

D_REGULAR = 0          # séries estacionárias (ADF em 12 de 12): diferenciar seria má especificação
D_SAZONAL = 0          # o ciclo semanal entra pelas dummies de dia da semana
CATEGORIA_PRODUTOS = "grama"   # produtos treinados um a um: todos os desta categoria
BASE_TREINO = "fluxo diário (sem encomendas acima de 2.000 un. no documento, ADR-013)"

_EM_CURSO = ("pending", "running")
# Enquanto o treino roda, uma thread grava `heartbeat_at` a cada `_BATIMENTO_S`. Sem sinal
# por `_SEM_SINAL_APOS`, o processo caiu (reinício, falta de memória, o pool que derruba a API
# no proot) e o disparo vira `error` — o admin não fica bloqueado esperando um treino morto.
_BATIMENTO_S = 30
_SEM_SINAL_APOS = timedelta(minutes=3)
_INTERVALO_PROGRESSO_S = 2.0              # no modo sequencial, grava o andamento no máximo a cada 2 s

# Um treino por vez neste processo. Adquirida no disparo e liberada ao fim de `_executar`.
_TRAVA = threading.Lock()


class TreinoEmAndamento(Exception):
    """Já existe um treino rodando."""


class TreinoForaDaApi(Exception):
    """`TRAINING_RUNNER=externo`: esta API não treina."""


# --------------------------------------------------------------------------- #
# Configuração e impressão digital dos dados
# --------------------------------------------------------------------------- #
def config_treino() -> ConfigTreino:
    return ConfigTreino(
        m=settings.SEASONAL_PERIOD, d=D_REGULAR, D=D_SAZONAL,
        horizonte=settings.FORECAST_HORIZON_DAYS,
        janela_dias=settings.FORECAST_SERVICE_WINDOW_DAYS,
        origens=settings.FORECAST_SERVICE_WF_ORIGINS, passo=1,
        min_historico_dias=settings.MIN_OBSERVATIONS_DAYS,
        min_dias_com_venda=settings.FORECAST_SERVICE_MIN_SALE_DAYS,
    )


def impressao_digital(db: Session) -> str:
    """SHA-256 do estado dos dados de que o treino depende. Muda com venda nova, venda
    apagada ou alterada (soma das quantidades), mudança na marcação de encomenda, no
    calendário ou no catálogo (produto que troca de categoria muda as séries)."""
    vendas = db.execute(select(
        func.count(Sale.id), func.max(Sale.id), func.sum(Sale.quantity),
        func.min(Sale.sale_date), func.max(Sale.sale_date),
        func.sum(case((Sale.is_bulk_order.is_(True), Sale.quantity), else_=0.0)),
    )).one()
    calendario = db.execute(select(func.count(), func.max(CalendarDay.updated_at)).select_from(CalendarDay)).one()
    produtos = db.execute(select(func.count(), func.max(Product.updated_at)).select_from(Product)).one()
    categorias = db.execute(select(Category.id, Category.show_on_dashboard).order_by(Category.id)).all()
    estado = {
        "vendas": [vendas[0], vendas[1], round(float(vendas[2] or 0), 4), str(vendas[3]), str(vendas[4]),
                   round(float(vendas[5] or 0), 4)],
        "calendario": [calendario[0], str(calendario[1])],
        "produtos": [produtos[0], str(produtos[1])],
        "categorias": [[c, bool(v)] for c, v in categorias],
    }
    return hashlib.sha256(json.dumps(estado, sort_keys=True, default=str).encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Estado dos disparos
# --------------------------------------------------------------------------- #
def _marcar_parados(db: Session, trava_e_minha: bool = False) -> None:
    """`pending`/`running` sem sinal há mais de `_SEM_SINAL_APOS` é de um processo que caiu
    (servidor reiniciado no meio do treino). Não toca no treino desta própria API: com a
    trava ocupada por uma thread de treino, não limpa. `trava_e_minha` = quem chama acabou de
    adquirir a trava (o disparo), então nenhum treino deste processo está rodando."""
    if _TRAVA.locked() and not trava_e_minha:
        return
    limite = datetime.now() - _SEM_SINAL_APOS
    parados = db.scalars(select(ForecastJob).where(
        ForecastJob.status.in_(_EM_CURSO),
        func.coalesce(ForecastJob.heartbeat_at, ForecastJob.created_at) < limite)).all()
    for job in parados:
        job.status, job.finished_at = "error", datetime.now()
        job.message = "O treino foi interrompido (o servidor reiniciou ou o processo parou). Dispare de novo."
        db.add(ForecastJobLog(job_id=job.id, level="error", message=job.message))
    if parados:
        db.commit()


def em_andamento(db: Session) -> ForecastJob | None:
    _marcar_parados(db)
    return db.scalar(select(ForecastJob).where(ForecastJob.status.in_(_EM_CURSO))
                     .order_by(ForecastJob.id.desc()))


def ultimo(db: Session) -> ForecastJob | None:
    return db.scalar(select(ForecastJob).order_by(ForecastJob.id.desc()))


def ultimo_concluido(db: Session) -> ForecastJob | None:
    return db.scalar(select(ForecastJob).where(ForecastJob.status == "done").order_by(ForecastJob.id.desc()))


def dados_alterados(db: Session) -> bool:
    """Se um disparo agora treinaria (dados diferentes do último treino concluído)."""
    concluido = ultimo_concluido(db)
    return concluido is None or concluido.data_fingerprint != impressao_digital(db)


def na_api() -> bool:
    return settings.TRAINING_RUNNER == "local"


# --------------------------------------------------------------------------- #
# Disparo
# --------------------------------------------------------------------------- #
def _abrir(user_id: int | None, trigger: str, cfg: ConfigTreino) -> tuple[ForecastJob, bool]:
    """Registra o disparo (com a trava já adquirida). Devolve (disparo, vai treinar): sem
    dados novos desde o último treino concluído, o disparo fica `skipped`."""
    with SessionLocal() as db:
        _marcar_parados(db, trava_e_minha=True)
        if em_andamento(db) is not None:
            raise TreinoEmAndamento()
        digital = impressao_digital(db)
        concluido = ultimo_concluido(db)
        if concluido is not None and concluido.data_fingerprint == digital:
            agora = datetime.now()
            job = ForecastJob(user_id=user_id, trigger=trigger, status="skipped", created_at=agora,
                              finished_at=agora, data_fingerprint=digital, data_until=concluido.data_until,
                              config=concluido.config, progress_pct=100.0,
                              message=("Os dados não mudaram desde o último treino "
                                       f"({concluido.finished_at:%d/%m/%Y %H:%M}). Nada a treinar."))
            db.add(job)
            db.flush()
            db.add(ForecastJobLog(job_id=job.id, message=job.message))
            db.commit()
            db.refresh(job)
            return job, False

        job = ForecastJob(user_id=user_id, trigger=trigger, status="pending", heartbeat_at=datetime.now(),
                          config=_config_registrada(cfg), message="Na fila: o treino começa em instantes.")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job, True


def iniciar(user_id: int | None) -> tuple[ForecastJob, bool]:
    """Dispara o treino em segundo plano (botão "Treinar previsões"). Devolve (disparo,
    iniciou): `iniciou = False` quando os dados não mudaram — o disparo fica `skipped`."""
    if not na_api():
        raise TreinoForaDaApi()
    if not _TRAVA.acquire(blocking=False):
        raise TreinoEmAndamento()
    iniciou = False
    try:
        cfg = config_treino()
        job, treinar = _abrir(user_id, "manual", cfg)
        if treinar:
            threading.Thread(target=_executar, args=(job.id, cfg), daemon=True,
                             name=f"servico-previsao-{job.id}").start()
            iniciou = True
        return job, iniciou
    finally:
        if not iniciou:  # quando inicia, quem libera é a thread do treino
            _TRAVA.release()


def treinar_agora(user_id: int | None = None, trigger: str = "script", cfg: ConfigTreino | None = None) -> ForecastJob:
    """Treina neste processo e só volta no fim — o script `treinar_previsoes` (API que não
    treina, `TRAINING_RUNNER=externo`). Devolve o disparo como terminou (`done`, `error` ou
    `skipped`)."""
    if not _TRAVA.acquire(blocking=False):
        raise TreinoEmAndamento()
    executou = False
    try:
        cfg = cfg or config_treino()
        job, treinar = _abrir(user_id, trigger, cfg)
        if treinar:
            executou = True
            _executar(job.id, cfg)  # libera a trava ao terminar
    finally:
        if not executou:
            _TRAVA.release()
    with SessionLocal() as db:
        return db.get(ForecastJob, job.id)


def versao_codigo() -> str | None:
    """Commit do código que treinou, para saber com qual versão cada previsão do histórico
    foi feita: `RENDER_GIT_COMMIT` no Render, senão o `git` da pasta do projeto."""
    commit = os.environ.get("RENDER_GIT_COMMIT")
    if commit:
        return commit[:12]
    try:
        r = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True,
                           timeout=5, cwd=Path(__file__).resolve().parent)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def _config_registrada(cfg: ConfigTreino) -> dict:
    return {**cfg.como_dict(), "base": BASE_TREINO, "categoria_produtos": CATEGORIA_PRODUTOS,
            "workers": max(1, settings.TRAINING_WORKERS), "versao_codigo": versao_codigo()}


# --------------------------------------------------------------------------- #
# Execução (thread)
# --------------------------------------------------------------------------- #
@dataclass
class _Serie:
    chave: str
    rotulo: str
    unit_id: str
    nivel: str
    category_id: str | None
    product_code: str | None
    y: pd.Series
    X: pd.DataFrame
    aberta: pd.Series


def _registrar(job_id: int, mensagem: str, nivel: str = "info", serie: str | None = None,
               db: Session | None = None) -> None:
    getattr(log, {"info": "info", "warning": "warning", "error": "error"}[nivel])(
        "[servico-previsao %s]%s %s", job_id, f" [{serie}]" if serie else "", mensagem)
    linha = ForecastJobLog(job_id=job_id, level=nivel, series_key=serie, message=mensagem[:2000])
    if db is not None:
        db.add(linha)
        return
    with SessionLocal() as s:
        s.add(linha)
        s.commit()


def _atualizar_job(job_id: int, **campos) -> None:
    with SessionLocal() as db:
        job = db.get(ForecastJob, job_id)
        for k, v in campos.items():
            setattr(job, k, v)
        job.heartbeat_at = datetime.now()
        db.commit()


def _montar_series(db: Session, cfg: ConfigTreino, job_id: int) -> tuple[list[_Serie], date]:
    """As séries de cada loja: as 4 categorias e cada produto de grama que vendeu nela."""
    df = base_vendas.carregar_vendas(db)
    if df.empty:
        raise ValueError("Não há vendas na base para treinar.")
    cal = base_vendas.carregar_calendario(db)
    lojas = base_vendas.carregar_lojas(db)
    categorias = list(db.execute(select(Category.id, Category.name).where(Category.show_on_dashboard.is_(True))
                                 .order_by(Category.sort_order)).all())
    data_until = df["emissao"].max()
    fim_previsao = data_until + pd.Timedelta(days=cfg.horizonte)

    series: list[_Serie] = []
    for loja in lojas:
        vendas = df[df["unit_id"] == loja["id"]]
        if vendas.empty:
            _registrar(job_id, f"{loja['nome']}: sem vendas na base, loja fora do treino.", "warning")
            continue
        fluxo = vendas[~vendas["encomenda"]]
        inicio = vendas["emissao"].min()
        cal_loja = cal[cal["unit_id"] == loja["id"]].set_index("data")[["loja_fechada", "abertura_excepcional"]]
        X, faltando = matriz_exogena(pd.date_range(inicio, fim_previsao, freq="D"), cal_loja)
        if faltando:
            _registrar(job_id, f"{loja['nome']}: o calendário não cobre {len(faltando)} dia(s) "
                               f"({faltando[0]:%d/%m/%Y} a {faltando[-1]:%d/%m/%Y}); usei o padrão da loja "
                               "(fechada no domingo, sem abertura excepcional).", "warning")
        aberta = X["loja_fechada"] == 0

        for cat_id, cat_nome in categorias:
            y = serie_diaria(fluxo[fluxo["cat"] == cat_id], data_until, inicio=inicio)
            series.append(_Serie(f"{loja['id']}:{NIVEL_CATEGORIA}:{cat_id}", f"{loja['nome']} · {cat_nome}",
                                 loja["id"], NIVEL_CATEGORIA, cat_id, None, y, X, aberta))

        grama = vendas[vendas["cat"] == CATEGORIA_PRODUTOS]
        ordem = grama.groupby("produto_cod")["qtdade"].sum().sort_values(ascending=False).index
        nomes = grama.sort_values("emissao").groupby("produto_cod")["produto_nome"].last()
        for cod in ordem:
            ini_prod = grama.loc[grama["produto_cod"] == cod, "emissao"].min()
            y = serie_diaria(fluxo[fluxo["produto_cod"] == cod], data_until, inicio=ini_prod)
            series.append(_Serie(f"{loja['id']}:{NIVEL_PRODUTO}:{cod}", f"{loja['nome']} · {nomes[cod]}",
                                 loja["id"], NIVEL_PRODUTO, CATEGORIA_PRODUTOS, str(cod), y,
                                 X.loc[ini_prod:], aberta.loc[ini_prod:]))
    return series, data_until.date()


def _texto_resultado(r: ResultadoSerie) -> tuple[str, str]:
    """(nível do log, mensagem) para o resultado de uma série."""
    if r.status == evaluator.STATUS_DADOS_INSUFICIENTES:
        return "info", f"Sem dados suficientes para treinar: {r.motivo}."
    if r.status == evaluator.STATUS_ERRO:
        return "error", f"Falhou: {r.motivo}"
    m = r.metricas or {}
    ordem = f"({','.join(map(str, r.ordem))})({','.join(map(str, r.ordem_sazonal))})"
    relativo = m.get("erro_relativo_naive")
    comparacao = ("" if relativo is None else
                  f", erro {abs(round((1 - relativo) * 100))}% {'menor' if relativo <= 1 else 'maior'} que repetir a semana anterior")
    status = "confiável" if r.status == evaluator.STATUS_TREINADO else "usar com cautela"
    return "info", (f"SARIMAX{ordem}, AIC {r.aic:.1f}. Walk-forward com {m.get('origens')} origens: "
                    f"MASE {m.get('mase')}{comparacao}, faixa de 95% acertou {m.get('cobertura_ic95_pct')}% "
                    f"dos dias. Previsão de {len(r.previsao)} dias gravada — {status}.{_texto_residuos(r.diagnostico)}")


def _texto_residuos(diagnostico: dict | None) -> str:
    """Aviso do diagnóstico dos resíduos (CLAUDE.md: registrado, não bloqueia)."""
    d, partes = diagnostico or {}, []
    if (lb := d.get("ljung_box_p")) is not None and lb <= evaluator.P_DIAGNOSTICO:
        partes.append(f"ainda correlacionados até {evaluator.LJUNG_BOX_LAG} dias (Ljung-Box p = {lb})")
    if (sw := d.get("shapiro_p")) is not None and sw <= evaluator.P_DIAGNOSTICO:
        partes.append(f"fora da distribuição normal (Shapiro-Wilk p = {sw})")
    return f" Resíduos {' e '.join(partes)}." if partes else ""


def _gravar_serie(job_id: int, s: _Serie, r: ResultadoSerie, cfg: ConfigTreino, contadores: dict,
                  total: int, historico: dict | None = None, treinada: bool = True) -> None:
    """Grava o resultado de uma série, o log e o andamento numa transação só, e guarda em
    `historico[loja]` os pontos dela para o histórico da previsão, gravado no fim do disparo.

    O andamento conta só as séries treinadas (`treinada`): a recusada por falta de dados é
    instantânea e, se contasse, a barra pularia no início e ficaria parada no treino de verdade.
    """
    if historico is not None and r.previsao is not None:
        wf, prev = historico_previsao.pontos_da_serie(s.nivel, s.product_code or s.category_id, r.backtest,
                                                      r.complemento, r.previsao, fechada=~s.aberta)
        historico[s.unit_id][0].extend(wf)
        historico[s.unit_id][1].extend(prev)
    if treinada:
        contadores["concluidas"] += 1
    contadores[r.status] = contadores.get(r.status, 0) + 1
    nivel_log, texto = _texto_resultado(r)
    with SessionLocal() as db:
        modelo = SeriesModel(
            job_id=job_id, unit_id=s.unit_id, level=s.nivel, category_id=s.category_id,
            product_code=s.product_code, series_key=s.chave, status=r.status,
            sarimax_order=list(r.ordem) if r.ordem else None,
            seasonal_order=list(r.ordem_sazonal) if r.ordem_sazonal else None,
            aic=r.aic, mase=(r.metricas or {}).get("mase"),
            ci95_coverage_pct=(r.metricas or {}).get("cobertura_ic95_pct"),
            metrics=None if r.metricas is None else {**r.metricas, **(r.diagnostico or {})},
            params={"trend": "c" if cfg.d == 0 else "n", "transformation": "nenhuma", "training_base": BASE_TREINO,
                    "window_days": cfg.janela_dias, "ordens_convergidas": r.ordens_convergidas,
                    "dias_historico": r.dias_historico, "dias_com_venda_janela": r.dias_com_venda_janela,
                    "coeficientes": r.coeficientes},
            train_start=r.treino_inicio.date() if r.treino_inicio is not None else None,
            train_end=r.treino_fim.date() if r.treino_fim is not None else None,
            message=r.motivo)
        db.add(modelo)
        db.flush()
        if r.previsao is not None:
            db.execute(insert(SeriesForecast), [
                {"model_id": modelo.id, "forecast_date": p.data.date(), "predicted": round(float(p.previsto), 3),
                 "lower_95": round(float(p.ic_inf), 3), "upper_95": round(float(p.ic_sup), 3)}
                for p in r.previsao.itertuples()])
        if r.backtest is not None:
            db.execute(insert(SeriesBacktestPoint), [
                {"model_id": modelo.id, "origin_date": p.origem.date(), "day": p.data.date(), "horizon": int(p.horizonte),
                 "predicted": round(float(p.previsto), 3), "lower_95": round(float(p.ic_inf), 3),
                 "upper_95": round(float(p.ic_sup), 3), "actual": float(p.real), "naive": float(p.naive)}
                for p in r.backtest.itertuples()])
        _registrar(job_id, texto, nivel_log, s.chave, db=db)
        job = db.get(ForecastJob, job_id)
        job.done_series = contadores["concluidas"]
        job.progress_pct = round(contadores["concluidas"] / total * 100, 1) if total else 0.0
        job.series_trained = contadores.get(evaluator.STATUS_TREINADO, 0)
        job.series_low_confidence = contadores.get(evaluator.STATUS_BAIXA_CONFIANCA, 0)
        job.series_insufficient = contadores.get(evaluator.STATUS_DADOS_INSUFICIENTES, 0)
        job.series_failed = contadores.get(evaluator.STATUS_ERRO, 0)
        job.heartbeat_at = datetime.now()
        db.commit()


def _treinar_sequencial(job_id: int, series: list[_Serie], cfg: ConfigTreino, contadores: dict, total: int,
                        historico: dict) -> None:
    ultimo_envio = 0.0
    for s in series:
        base = contadores["concluidas"]
        _atualizar_job(job_id, current_series=s.rotulo)

        def progresso(feitos: int, total_ajustes: int, base=base, rotulo=s.rotulo) -> None:
            nonlocal ultimo_envio
            agora = time.monotonic()
            if agora - ultimo_envio >= _INTERVALO_PROGRESSO_S:
                ultimo_envio = agora
                _atualizar_job(job_id, current_series=rotulo,
                               progress_pct=round((base + feitos / total_ajustes) / total * 100, 1))

        _gravar_serie(job_id, s, treinar_serie(s.y, s.X, s.aberta, cfg, s.nivel, ao_progredir=progresso),
                      cfg, contadores, total, historico)


def _treinar_em_paralelo(job_id: int, series: list[_Serie], cfg: ConfigTreino, contadores: dict, total: int,
                         historico: dict, workers: int) -> list[_Serie]:
    """Uma série por processo. Devolve as séries que ficaram sem resultado se o pool quebrar."""
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(var, "1")  # herdado pelos processos: um núcleo por série
    pendentes = {s.chave: s for s in series}
    try:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            futuros = [pool.submit(treinar_serie_tarefa, (s.chave, s.y, s.X, s.aberta, cfg, s.nivel)) for s in series]
            _atualizar_job(job_id, current_series=f"{len(series)} séries em {workers} processos")
            for futuro in as_completed(futuros):
                chave, resultado = futuro.result()
                s = pendentes.pop(chave)
                _gravar_serie(job_id, s, resultado, cfg, contadores, total, historico)
                _atualizar_job(job_id, current_series=f"{len(pendentes)} série(s) restante(s)")
    except BrokenProcessPool as erro:
        _registrar(job_id, f"Os processos paralelos pararam ({erro}); as {len(pendentes)} séries restantes "
                           "seguem uma a uma.", "warning")
    return list(pendentes.values())


def _batimento(job_id: int, parar: threading.Event) -> None:
    """Grava `heartbeat_at` a cada `_BATIMENTO_S` até o treino terminar. Independe do
    andamento: no modo paralelo uma série pode levar minutos sem gravar nada."""
    while not parar.wait(_BATIMENTO_S):
        try:
            _atualizar_job(job_id)
        except Exception:  # noqa: BLE001 — banco fora do ar por um instante: tenta no próximo
            log.warning("serviço de previsão: batimento do treino %s falhou", job_id, exc_info=True)


def _executar(job_id: int, cfg: ConfigTreino) -> None:
    parar = threading.Event()
    threading.Thread(target=_batimento, args=(job_id, parar), daemon=True,
                     name=f"servico-previsao-{job_id}-batimento").start()
    try:
        _atualizar_job(job_id, status="running", started_at=datetime.now(),
                       message="Lendo as vendas e o calendário da base...")
        with SessionLocal() as db:
            digital = impressao_digital(db)  # do momento da leitura, não do clique
            # as planilhas que já estavam carregadas quando o treino leu as vendas
            ultima_planilha = db.scalar(select(func.max(ProcessingLog.id)).where(ProcessingLog.status == "done"))
            series, data_until = _montar_series(db, cfg, job_id)

        inelegiveis, treinaveis = [], []
        for s in series:
            motivo = motivo_inelegivel(s.y, cfg, s.nivel)
            (inelegiveis if motivo else treinaveis).append((s, motivo))
        n_cat = sum(s.nivel == NIVEL_CATEGORIA for s in series)
        n_prod = len(series) - n_cat
        _atualizar_job(job_id, data_fingerprint=digital, data_until=data_until, total_series=len(treinaveis),
                       message=f"Treinando {len(treinaveis)} séries...")
        _registrar(job_id, (
            f"Treino iniciado com vendas até {data_until:%d/%m/%Y}: {n_cat} séries de categoria e {n_prod} "
            f"produtos de grama, {len(treinaveis)} com dados suficientes. SARIMAX m={cfg.m}, d={cfg.d}, D={cfg.D} "
            f"com constante; janela deslizante de {cfg.janela_dias} dias; walk-forward com {cfg.origens} origens "
            f"de 1 em 1 dia, prevendo {cfg.horizonte} dias. Base: {BASE_TREINO}."))

        contadores, total = {"concluidas": 0}, len(treinaveis)
        for s, motivo in inelegiveis:
            _gravar_serie(job_id, s, ResultadoSerie(status=evaluator.STATUS_DADOS_INSUFICIENTES, motivo=motivo,
                                                    dias_historico=len(s.y),
                                                    dias_com_venda_janela=int((s.y.iloc[-cfg.janela_dias:] > 0).sum())),
                          cfg, contadores, total, treinada=False)

        historico = defaultdict(lambda: ([], []))  # loja → (walk-forward, previsão)
        restantes = [s for s, _ in treinaveis]
        workers = min(max(1, settings.TRAINING_WORKERS), len(restantes)) if restantes else 1
        if workers > 1:
            restantes = _treinar_em_paralelo(job_id, restantes, cfg, contadores, total, historico, workers)
        _treinar_sequencial(job_id, restantes, cfg, contadores, total, historico)

        boas = contadores.get(evaluator.STATUS_TREINADO, 0)
        cautela = contadores.get(evaluator.STATUS_BAIXA_CONFIANCA, 0)
        falhas = contadores.get(evaluator.STATUS_ERRO, 0)
        sem_dados = contadores.get(evaluator.STATUS_DADOS_INSUFICIENTES, 0)
        partes = [f"{boas + cautela} séries com previsão ({boas} confiáveis, {cautela} para usar com cautela)"]
        if sem_dados:
            partes.append(f"{sem_dados} sem vendas suficientes")
        if falhas:
            partes.append(f"{falhas} com falha")
        mensagem = "Treino concluído: " + "; ".join(partes) + "."
        _concluir(job_id, mensagem, data_until + timedelta(days=1), {s.unit_id for s in series}, historico,
                  ultima_planilha)
    except Exception as erro:  # noqa: BLE001 — o erro vai para o disparo e para o log
        log.exception("serviço de previsão: treino %s falhou", job_id)
        mensagem = f"O treino falhou: {type(erro).__name__}: {erro}"[:500]
        try:
            _atualizar_job(job_id, status="error", finished_at=datetime.now(), current_series=None, message=mensagem)
            _registrar(job_id, mensagem, "error")
        except Exception:  # noqa: BLE001 — banco fora do ar: fica só no log do processo
            log.exception("serviço de previsão: não consegui registrar a falha do treino %s", job_id)
    finally:
        parar.set()
        _TRAVA.release()


# --------------------------------------------------------------------------- #
# Histórico da previsão
# --------------------------------------------------------------------------- #
def gravar_historico(db: Session, unit_id: str, inicio: date, walk_forward: list[dict], previsao: list[dict],
                     job_id: int | None) -> int:
    """Atualiza `forecast_history` de uma loja (sem commit): a previsão que começa em
    `inicio` troca os dias de `inicio` em diante, de todas as séries da loja; o walk-forward
    só preenche dia anterior ainda vazio. Devolve quantos dias gravou."""
    db.execute(delete(ForecastHistory).where(ForecastHistory.unit_id == unit_id, ForecastHistory.day >= inicio))
    gravados = {tuple(c) for c in db.execute(select(ForecastHistory.level, ForecastHistory.item, ForecastHistory.day)
                                             .where(ForecastHistory.unit_id == unit_id))}
    novos = historico_previsao.pontos_a_gravar(gravados, walk_forward, previsao, inicio)
    if novos:
        db.execute(insert(ForecastHistory), [{**p, "unit_id": unit_id, "job_id": job_id} for p in novos])
    return len(novos)


def _concluir(job_id: int, mensagem: str, inicio: date, lojas: set[str], historico: dict,
              ultima_planilha: int | None) -> None:
    """Numa transação só: grava o histórico da previsão de cada loja do treino, liga a este
    treino as planilhas que entraram nele pela primeira vez, marca o disparo como `done` e
    apaga o walk-forward dos treinos antigos."""
    with SessionLocal() as db:
        dias = sum(gravar_historico(db, loja, inicio, *historico[loja], job_id) for loja in sorted(lojas))
        _registrar(job_id, f"Histórico da previsão atualizado: {dias} dia(s) gravados, com a previsão "
                           f"a partir de {inicio:%d/%m/%Y}.", db=db)
        _registrar(job_id, _ligar_planilhas(db, job_id, ultima_planilha), db=db)
        job = db.get(ForecastJob, job_id)
        job.status, job.finished_at, job.progress_pct, job.current_series = "done", datetime.now(), 100.0, None
        job.message, job.heartbeat_at = mensagem, datetime.now()
        db.flush()
        if apagados := _apagar_backtest_antigo(db):
            _registrar(job_id, f"Walk-forward de treinos antigos apagado: {apagados} ponto(s) (ficam os "
                               f"{settings.FORECAST_SERVICE_KEEP_BACKTEST_JOBS} últimos treinos).", db=db)
        _registrar(job_id, mensagem, db=db)
        db.commit()


def _ligar_planilhas(db: Session, job_id: int, ultima_planilha: int | None) -> str:
    """Liga ao treino as planilhas gravadas até a leitura das vendas que nenhum treino
    concluído usou ainda. Devolve a linha do log."""
    if ultima_planilha is None:
        return "Nenhuma planilha carregada."
    novas = list(db.scalars(select(ProcessingLog).where(
        ProcessingLog.status == "done", ProcessingLog.forecast_job_id.is_(None), ProcessingLog.id <= ultima_planilha)
        .order_by(ProcessingLog.id)))
    if not novas:
        return "Nenhuma planilha nova desde o último treino (mudou o calendário ou o catálogo)."
    db.execute(update(ProcessingLog).where(ProcessingLog.id.in_([p.id for p in novas])).values(forecast_job_id=job_id))
    nomes = ", ".join(p.filename for p in novas[:5]) + (f" e mais {len(novas) - 5}" if len(novas) > 5 else "")
    return f"{len(novas)} planilha(s) nova(s) neste treino: {nomes}."


def _apagar_backtest_antigo(db: Session) -> int:
    """Apaga `series_backtest_points` dos treinos que não estão entre os últimos
    `FORECAST_SERVICE_KEEP_BACKTEST_JOBS` concluídos (os em andamento ficam)."""
    manter = (select(ForecastJob.id).where(ForecastJob.status == "done").order_by(ForecastJob.id.desc())
              .limit(max(1, settings.FORECAST_SERVICE_KEEP_BACKTEST_JOBS)))
    antigos = select(SeriesModel.id).join(ForecastJob, ForecastJob.id == SeriesModel.job_id).where(
        ForecastJob.status.not_in(_EM_CURSO), SeriesModel.job_id.not_in(list(db.scalars(manter))))
    return db.execute(delete(SeriesBacktestPoint).where(SeriesBacktestPoint.model_id.in_(antigos))).rowcount or 0


def semear_historico(db: Session, recriar: bool = False) -> int:
    """Preenche `forecast_history` a partir do último disparo concluído (bancos com treino
    anterior à gravação do histórico): o 1º dia das janelas do walk-forward e a previsão.
    Sem o complemento, que esse treino não gravou — o próximo completa esses dias.
    `recriar` apaga o histórico antes (o que veio do treino antigo do painel). Devolve os
    dias gravados."""
    if recriar:
        db.execute(delete(ForecastHistory))
    job = ultimo_concluido(db)
    if job is None:
        db.commit()
        return 0
    modelos = {m.id: m for m in db.scalars(select(SeriesModel).where(SeriesModel.job_id == job.id))}
    pontos = defaultdict(lambda: ([], []))
    for p in db.scalars(select(SeriesBacktestPoint).where(SeriesBacktestPoint.model_id.in_(list(modelos)),
                                                          SeriesBacktestPoint.horizon == 1)):
        m = modelos[p.model_id]
        pontos[m.unit_id][0].append({"level": m.level, "item": m.product_code or m.category_id, "day": p.day,
                                     "predicted": p.predicted, "lower_95": p.lower_95, "upper_95": p.upper_95,
                                     "source": "walk_forward", "origin_date": p.origin_date})
    inicio = job.data_until + timedelta(days=1)
    for p in db.scalars(select(SeriesForecast).where(SeriesForecast.model_id.in_(list(modelos)))):
        m = modelos[p.model_id]
        pontos[m.unit_id][1].append({"level": m.level, "item": m.product_code or m.category_id,
                                     "day": p.forecast_date, "predicted": p.predicted, "lower_95": p.lower_95,
                                     "upper_95": p.upper_95, "source": "forecast", "origin_date": inicio})
    total = sum(gravar_historico(db, loja, inicio, *pontos[loja], job.id)
                for loja in sorted({m.unit_id for m in modelos.values()}))
    db.commit()
    return total
