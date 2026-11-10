"""Dados das telas do frontend, montados a partir do banco.

  * `painel()`: formato `BaseReal` (previsão das categorias e dos produtos de grama de cada
    loja — todos os dias que o treino gravou, até 91; a tela escolhe quantos mostrar, ADR-021 —,
    histórico, encomendas grandes, planilhas carregadas);
  * `historico()`: vendido × previsto congelado de uma categoria ou produto
    (`forecast_history`), para a tela de histórico da previsão;
  * `analises()`: análises descritivas por loja;
  * `contexto()`: o pouco que o layout precisa logo depois do login (lojas, categorias,
    data da última venda, status dos previsores) — só consultas pequenas, sem ler `sales`
    inteira. As telas pedem o resto ao abrir.

A previsão vem do último treino concluído (`forecast_jobs` `done`, ADR-017); a base linha a
linha (tela "Conferir Dados") é paginada no banco (`registros_service`).

Tudo sai de `sales` (até o último dia com venda do treino, no painel) e das tabelas do
treino; nada é gravado. Os resultados ficam em cache até os dados mudarem
(`cache.versao_dados`). Nenhum dado pessoal sai: o cliente vira só "consumidor" ou
"cadastrado".
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.domain import historico_previsao
from backend.domain import painel as montagem
from backend.infrastructure.database import (
    Category,
    ForecastHistory,
    ForecastJob,
    ProcessingLog,
    Product,
    Sale,
    SeriesBacktestPoint,
    SeriesForecast,
    SeriesModel,
)
from backend.services import base_vendas, cache
from backend.services.base_vendas import KIND_RECLASSIFICACAO
from training_scripts.frontend_mock.gerar_analises_frontend import analisar_unidade
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA as LIMIAR_ADR013


class PrevisaoIndisponivel(Exception):
    """Ainda não há treino concluído da previsão no banco."""


class ItemSemHistorico(Exception):
    """Categoria do painel ou produto sem venda na loja."""


# --------------------------------------------------------------------------- #
# Leituras compartilhadas
# --------------------------------------------------------------------------- #
def _vendas(db: Session, versao: tuple) -> pd.DataFrame:
    return cache.obter("vendas", versao, lambda: base_vendas.carregar_vendas(db))


def _categorias(db: Session) -> list[dict]:
    return [{"id": c.id, "nome": c.name, "grupo": c.source_category, "descricao": c.description}
            for c in db.scalars(select(Category).where(Category.show_on_dashboard.is_(True))
                                .order_by(Category.sort_order))]


def _fechados(cal: pd.DataFrame, unit_id: str) -> set:
    return set(cal.loc[(cal["unit_id"] == unit_id) & (cal["loja_fechada"] == 1), "data"])


def ultimo_treino(db: Session) -> ForecastJob | None:
    """O último treino concluído da previsão — o que as telas mostram."""
    return db.scalar(select(ForecastJob).where(ForecastJob.status == "done").order_by(ForecastJob.id.desc()))


# --------------------------------------------------------------------------- #
# Painel
# --------------------------------------------------------------------------- #
def _modelo(m: SeriesModel) -> dict:
    """Modelo de uma série no formato da tela; sem previsão (`insufficient_data`,
    `error`), só o status e o motivo."""
    return {"ordem": m.sarimax_order, "ordem_sazonal": m.seasonal_order, "aic": m.aic, "status": m.status,
            "metricas": montagem.metricas_da_tela(m.metrics), "mensagem": m.message}


def _previsores(db: Session, job: ForecastJob) -> dict:
    """Previsores do treino no formato que `domain.painel` espera: categorias (com o 1º
    dia de cada janela do walk-forward) e produtos de grama, por loja."""
    modelos = list(db.scalars(select(SeriesModel).where(SeriesModel.job_id == job.id)))
    ids = [m.id for m in modelos]
    previsao, backtest = defaultdict(list), defaultdict(list)
    for p in db.scalars(select(SeriesForecast).where(SeriesForecast.model_id.in_(ids))
                        .order_by(SeriesForecast.model_id, SeriesForecast.forecast_date)):
        previsao[p.model_id].append({"data": str(p.forecast_date), "previsto": p.predicted,
                                     "inf": p.lower_95, "sup": p.upper_95})
    categorias = [m.id for m in modelos if m.level == "category"]
    for p in db.scalars(select(SeriesBacktestPoint).where(SeriesBacktestPoint.model_id.in_(categorias),
                                                          SeriesBacktestPoint.horizon == 1)
                        .order_by(SeriesBacktestPoint.model_id, SeriesBacktestPoint.day)):
        backtest[p.model_id].append({"data": str(p.day), "previsto": p.predicted, "inf": p.lower_95,
                                     "sup": p.upper_95, "real": p.actual, "naive": p.naive})
    out: dict = {}
    for m in modelos:
        u = out.setdefault(m.unit_id, {"categorias": {}, "produtos": {}})
        if m.level == "category":
            u["categorias"][m.category_id] = {"modelo": _modelo(m), "previsao": previsao[m.id],
                                              "backtest": backtest[m.id]}
        else:
            u["produtos"][m.product_code] = {"modelo": _modelo(m), "previsao": previsao[m.id]}
    return out


def _horizontes(cfg: dict) -> dict:
    """Horizonte do teste (walk-forward) e dias previstos pelo treino. Treino anterior ao
    ADR-021 previa só o horizonte do teste."""
    if not cfg:  # sem treino: os da configuração atual
        return {"horizonte_dias": settings.FORECAST_HORIZON_DAYS,
                "horizonte_previsao_dias": settings.FORECAST_MAX_HORIZON_DAYS}
    teste = cfg.get("horizonte", settings.FORECAST_HORIZON_DAYS)
    return {"horizonte_dias": teste, "horizonte_previsao_dias": max(cfg.get("horizonte_previsao") or teste, teste)}


def _configuracao(job: ForecastJob, lojas: list[dict]) -> dict:
    cfg = job.config or {}
    return {**_horizontes(cfg), "m": cfg.get("m"),
            "d": cfg.get("d"), "d_candidatos": cfg.get("d_candidatos") or [cfg.get("d")], "D": cfg.get("D"), "alpha_ic": cfg.get("alpha"), "janela_dias": cfg.get("janela_dias"),
            "origens": cfg.get("origens"), "passo_origem_dias": cfg.get("passo"),
            "limiares_encomenda_un": {u["id"]: (cfg.get("limiares_encomenda_un") or {}).get(u["id"], LIMIAR_ADR013)
                                      for u in lojas},
            "base": cfg.get("base"),
            "categoria_produtos": cfg.get("categoria_produtos"), "versao_codigo": cfg.get("versao_codigo"),
            "dados_ate": str(job.data_until)}


def importacao(db: Session) -> dict:
    """Planilhas carregadas (`processing_log` concluído) e o resumo da qualidade."""
    logs = list(db.scalars(select(ProcessingLog).where(ProcessingLog.status == "done",
                                                       ProcessingLog.kind != KIND_RECLASSIFICACAO)
                           .order_by(ProcessingLog.reference_month, ProcessingLog.id)))

    def periodo(p: ProcessingLog) -> list:
        return (p.quality or {}).get("periodo") or [None, None]

    return {
        "arquivos": [{"arquivo": p.filename, "competencia": p.reference_month or "",
                      "inicio": periodo(p)[0], "fim": periodo(p)[1],
                      "registros": p.rows_added, "duplicatas": p.rows_duplicate, "hash": p.file_sha256,
                      "processado_em": (p.finished_at or p.started_at).isoformat(timespec="seconds")}
                     for p in logs],
        "qualidade": {
            "linhas_lidas": sum(p.rows_read for p in logs),
            "linhas_removidas": sum(p.rows_skipped for p in logs),
            "clientes_sem_nome_corrigidos": sum((p.quality or {}).get("clientes_sem_nome_corrigidos", 0)
                                                for p in logs),
            "duplicatas": sum(p.rows_duplicate for p in logs),
        },
    }


def painel(db: Session) -> dict:
    versao = cache.versao_dados(db)

    def construir() -> dict:
        job = ultimo_treino(db)
        if job is None:
            raise PrevisaoIndisponivel()
        df = _vendas(db, versao)
        df = df[df["emissao"] <= pd.Timestamp(job.data_until)]
        cal = base_vendas.carregar_calendario(db)
        lojas = base_vendas.carregar_lojas(db)
        entradas = (lojas, _categorias(db), _previsores(db, job), _configuracao(job, lojas),
                    (job.finished_at or job.created_at).isoformat(timespec="seconds"), importacao(db))
        db.commit()  # solta a conexão antes do cálculo (o Neon derruba transação ociosa)
        return montagem.montar_painel(df, cal, *entradas)

    return cache.obter("painel", versao, construir)


def _avaliacao(db: Session, unidade: str, level: str, item: str) -> dict | None:
    """Métricas do walk-forward da série no último treino concluído que a avaliou (o mais
    recente com métricas): se o último treino a recusou, vale o anterior."""
    filtro = SeriesModel.category_id == item if level == "category" else SeriesModel.product_code == item
    linha = db.execute(
        select(SeriesModel, ForecastJob)
        .join(ForecastJob, ForecastJob.id == SeriesModel.job_id)
        .where(ForecastJob.status == "done", SeriesModel.unit_id == unidade, SeriesModel.level == level,
               filtro, SeriesModel.metrics.isnot(None))
        .order_by(ForecastJob.id.desc()).limit(1)).first()
    if linha is None:
        return None
    modelo, job = linha
    return montagem.avaliacao_do_historico(
        modelo.metrics, modelo.status, (job.finished_at or job.created_at).isoformat(timespec="seconds"),
        str(job.data_until) if job.data_until else None)


def historico(db: Session, unidade: str, nivel: str, item: str) -> dict:
    """Histórico da previsão de uma categoria (`nivel="categoria"`) ou produto da loja:
    `serie` = o vendido de cada dia (sem encomendas grandes), do começo da base ao último dia
    com venda do último treino concluído, com o previsto gravado em `forecast_history` — vazio
    antes do 1º treino; `avaliacao` = as métricas do último treino que avaliou a série
    (`_avaliacao`), ou None."""
    versao = cache.versao_dados(db)
    treino = ultimo_treino(db)
    if treino is None:
        raise PrevisaoIndisponivel()
    fim = pd.Timestamp(treino.data_until)
    level, coluna = ("category", "cat") if nivel == "categoria" else ("product", "produto_cod")
    df = _vendas(db, versao)
    real = montagem.venda_diaria(df[df["unit_id"] == unidade], coluna, item, fim)
    if real is None:
        raise ItemSemHistorico()
    previstos = {p.day: (p.predicted, p.lower_95, p.upper_95, p.source, p.origin_date, p.store_closed)
                 for p in db.scalars(select(ForecastHistory).where(
                     ForecastHistory.unit_id == unidade, ForecastHistory.level == level,
                     ForecastHistory.item == item, ForecastHistory.day <= fim.date()))}
    avaliacao = _avaliacao(db, unidade, level, item)
    db.commit()
    return {"serie": historico_previsao.serie_com_previsto(real, previstos), "avaliacao": avaliacao}


# --------------------------------------------------------------------------- #
# Contexto do layout
# --------------------------------------------------------------------------- #
def contexto(db: Session) -> dict:
    """Lojas, categorias, período da base, status dos previsores e planilhas carregadas.
    Tudo por consultas agregadas (sem ler as vendas), para o layout abrir logo após o login."""
    nao_servico = (select(Sale.sale_date, Sale.product_code)
                   .join(Product, Product.code == Sale.product_code)
                   .join(Category, Category.id == Product.category_id)
                   .where(Category.show_on_dashboard.is_(True)).subquery())
    inicio, fim, linhas, skus = db.execute(
        select(func.min(nao_servico.c.sale_date), func.max(nao_servico.c.sale_date), func.count(),
               func.count(func.distinct(nao_servico.c.product_code)))).one()

    previsao = None
    treino = ultimo_treino(db)
    if treino is not None:
        modelos = db.execute(
            select(SeriesModel, Product.name)
            .outerjoin(Product, Product.code == SeriesModel.product_code)
            .where(SeriesModel.job_id == treino.id)
            .order_by(SeriesModel.unit_id, SeriesModel.level, SeriesModel.id)
        ).all()
        previsao = {
            "gerada_em": (treino.finished_at or treino.created_at).isoformat(timespec="seconds"),
            "dados_ate": str(treino.data_until),
            "categorias": [{"loja": m.unit_id, "categoria": m.category_id, "status": m.status}
                           for m, _ in modelos if m.level == "category"],
            "produtos": [{"loja": m.unit_id, "codigo": m.product_code, "nome": nome, "status": m.status}
                         for m, nome in modelos if m.level == "product"],
        }
    config = (treino.config or {}) if treino else {}
    return {
        "lojas": base_vendas.carregar_lojas(db),
        "categorias": _categorias(db),
        "configuracao": {**_horizontes(config),
                         "limiares_encomenda_un": base_vendas.limiares_encomenda_atuais(db),
                         # falso no Render: o front não oferece "Treinar previsões"
                         "treino_na_api": settings.TRAINING_RUNNER == "local"},
        "base": {"inicio": str(inicio) if inicio else None, "fim": str(fim) if fim else None,
                 "linhas": int(linhas), "skus": int(skus)},
        "previsao": previsao,
        "importacao": importacao(db),
    }


# --------------------------------------------------------------------------- #
# Análises descritivas
# --------------------------------------------------------------------------- #
def _base_analise(df: pd.DataFrame) -> pd.DataFrame:
    """Colunas extras de `gerar_analises_frontend.carregar()`."""
    return df.assign(
        pagamento=df["pagamento"].str.strip().replace("", "NÃO INFORMADO"),
        nota=df["emissao"].dt.strftime("%Y%m%d") + "-" + df["doc_numero"],
    )


def analises(db: Session) -> dict:
    versao = cache.versao_dados(db)

    def construir() -> dict:
        df = _base_analise(_vendas(db, versao))
        cal = base_vendas.carregar_calendario(db)
        lojas = base_vendas.carregar_lojas(db)
        limiares = base_vendas.limiares_encomenda_atuais(db)
        db.commit()  # solta a conexão antes do cálculo
        saida = {"gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
                 "limiares_encomenda_un": limiares, "unidades": {}}
        for u in lojas:
            v = df[df["unit_id"] == u["id"]]
            if len(v):
                saida["unidades"][u["id"]] = analisar_unidade(v, _fechados(cal, u["id"]))
        return saida

    return cache.obter("analises", versao, construir)
