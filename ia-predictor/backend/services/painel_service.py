"""Dados das telas do frontend, montados a partir do banco.

  * `painel()`: formato `BaseReal` (previsão, histórico, produtos, encomendas, planilhas
    carregadas) — o que antes vinha de `baseReal.json`;
  * `analises()`: análises descritivas por loja — antes `analises.json`;
  * `contexto()`: o pouco que o layout precisa logo depois do login (lojas, categorias,
    data da última venda, status dos previsores) — só consultas pequenas, sem ler `sales`
    inteira. As telas pedem o resto ao abrir.

A base linha a linha (tela "Conferir Dados") é paginada no banco: `registros_service`.

Tudo sai de `sales` (até o fim do último treino, no painel) e das tabelas do treino; nada
é gravado. Os resultados ficam em cache até os dados mudarem (`cache.versao_dados`).
Nenhum dado pessoal sai: o cliente vira só "consumidor" ou "cadastrado".
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
    BacktestPoint,
    Category,
    ForecastCache,
    ForecastHistory,
    ForecastRun,
    ModelArtifact,
    ProcessingLog,
    Product,
    RetrainHistory,
    Sale,
)
from backend.services import base_vendas, cache
from backend.services.treino_service import METRICAS_EN, PARAMS_EN
from training_scripts.frontend_mock.gerar_analises_frontend import analisar_unidade
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA


class PrevisaoIndisponivel(Exception):
    """Ainda não há treino concluído no banco."""


class ProdutoInexistente(Exception):
    """Produto sem previsor próprio na loja, no último treino."""


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


# --------------------------------------------------------------------------- #
# Painel
# --------------------------------------------------------------------------- #
def ultima_geracao(db: Session) -> tuple[ForecastRun, RetrainHistory] | None:
    linha = db.execute(
        select(ForecastRun, RetrainHistory)
        .join(RetrainHistory, RetrainHistory.id == ForecastRun.retrain_id)
        .where(ForecastRun.status == "done", RetrainHistory.status == "done")
        .order_by(ForecastRun.id.desc())
        .limit(1)
    ).first()
    return None if linha is None else (linha[0], linha[1])


def _metricas_pt(m: ModelArtifact) -> dict | None:
    if m.metrics is None:
        return None
    pt = {p: m.metrics.get(en) for p, en in METRICAS_EN.items()}
    pt["mase"] = m.mase
    pt["cobertura_ic95_pct"] = m.ci95_coverage_pct
    ordem = ["rodadas", "rodadas_vence_naive", "dias_avaliados", "mae", "mase", "erro_relativo_naive",
             "cobertura_ic95_pct", "largura_ic95", "venda_media_dia", "previsto_sobre_real_pct",
             "erro_total_14d_pct"]
    return {k: pt[k] for k in ordem}


def _previsores(db: Session, run: ForecastRun, retrain: RetrainHistory) -> dict:
    """Previsores do treino no formato que `domain.painel` espera."""
    modelos = list(db.scalars(select(ModelArtifact).where(ModelArtifact.retrain_id == retrain.id)))
    ids = [m.id for m in modelos]
    backtest, previsao = defaultdict(list), defaultdict(list)
    for p in db.scalars(select(BacktestPoint).where(BacktestPoint.model_id.in_(ids))
                        .order_by(BacktestPoint.model_id, BacktestPoint.day)):
        backtest[p.model_id].append({"data": str(p.day), "previsto": p.predicted, "inf": p.lower_95,
                                     "sup": p.upper_95, "real": p.actual, "naive": p.naive,
                                     "origem": str(p.origin_date)})
    for p in db.scalars(select(ForecastCache).where(ForecastCache.run_id == run.id)
                        .order_by(ForecastCache.model_id, ForecastCache.forecast_date)):
        previsao[p.model_id].append({"data": str(p.forecast_date), "previsto": p.predicted,
                                     "inf": p.lower_95, "sup": p.upper_95})

    out: dict = {}
    for m in modelos:
        u = out.setdefault(m.unit_id, {"loja": None, "categorias": {}, "produtos": {}})
        if m.level == "unit":
            params = m.params or {}
            u["loja"] = {
                "modelo": {"ordem": m.sarimax_order, "ordem_sazonal": m.seasonal_order,
                           **{pt: params.get(en) for pt, en in PARAMS_EN.items()},
                           "status": m.status, "metricas": _metricas_pt(m)},
                "backtest": backtest[m.id], "previsao": previsao[m.id]}
        elif m.level == "category":
            u["categorias"][m.category_id] = {"status": m.status, "metricas": _metricas_pt(m),
                                              "backtest": backtest[m.id], "previsao": previsao[m.id]}
        else:
            modelo = None if m.sarimax_order is None else {
                "ordem": m.sarimax_order, "ordem_sazonal": m.seasonal_order,
                "metricas": _metricas_pt(m), "status": m.status}
            u["produtos"][m.product_code] = {"modelo": modelo, "backtest": backtest[m.id],
                                             "previsao": previsao[m.id]}
    return {k: v for k, v in out.items() if v["loja"] is not None}


def importacao(db: Session) -> dict:
    """Planilhas carregadas (`processing_log` concluído) e o resumo da qualidade."""
    logs = list(db.scalars(select(ProcessingLog).where(ProcessingLog.status == "done")
                           .order_by(ProcessingLog.reference_month, ProcessingLog.id)))
    return {
        "arquivos": [{"arquivo": p.filename, "competencia": p.reference_month or "",
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
        geracao = ultima_geracao(db)
        if geracao is None:
            raise PrevisaoIndisponivel()
        run, retrain = geracao
        df = _vendas(db, versao)
        df = df[df["emissao"] <= pd.Timestamp(retrain.data_until)]
        cal = base_vendas.carregar_calendario(db)
        entradas = (base_vendas.carregar_lojas(db), _categorias(db), _previsores(db, run, retrain),
                    retrain.config or {}, (run.finished_at or run.started_at).isoformat(timespec="seconds"),
                    importacao(db))
        db.commit()  # solta a conexão antes do cálculo (o Neon derruba transação ociosa)
        return montagem.montar_painel(df, cal, *entradas)

    return cache.obter("painel", versao, construir)


def painel_leve(db: Session) -> dict:
    """O painel sem o que a tela só usa sob demanda: o teste de acerto de cada produto (70%
    do JSON, pedido por `backtest_produto` quando o produto é aberto) e a amostra de
    registros (a tela "Conferir Dados" consulta a base paginada)."""
    versao = cache.versao_dados(db)

    def construir() -> dict:
        completo = painel(db)
        unidades = [{**u, "produtos": [{k: v for k, v in p.items() if k != "backtest"} for p in u["produtos"]]}
                    for u in completo["unidades"]]
        return {**{k: v for k, v in completo.items() if k != "registros_amostra"}, "unidades": unidades}

    return cache.obter("painel_leve", versao, construir)


class ItemSemHistorico(Exception):
    """Categoria do painel ou produto sem venda na loja."""


def historico(db: Session, unidade: str, nivel: str, item: str) -> list[dict]:
    """Histórico da previsão de uma categoria (`nivel="categoria"`) ou produto da loja: o
    vendido de cada dia (sem encomendas grandes), do começo da base ao fim do último treino,
    com o previsto gravado em `forecast_history` — vazio antes da data fixa de treino."""
    versao = cache.versao_dados(db)
    geracao = ultima_geracao(db)
    if geracao is None:
        raise PrevisaoIndisponivel()
    fim = pd.Timestamp(geracao[1].data_until)
    level, coluna = ("category", "cat") if nivel == "categoria" else ("product", "produto_cod")
    df = _vendas(db, versao)
    real = montagem.venda_diaria(df[df["unit_id"] == unidade], coluna, item, fim)
    if real is None:
        raise ItemSemHistorico()
    previstos = {p.day: (p.predicted, p.lower_95, p.upper_95) for p in db.scalars(
        select(ForecastHistory).where(ForecastHistory.unit_id == unidade, ForecastHistory.level == level,
                                      ForecastHistory.item == item, ForecastHistory.day <= fim.date()))}
    db.commit()
    return historico_previsao.serie_com_previsto(real, previstos)


def backtest_produto(db: Session, unidade: str, codigo: str) -> list[dict]:
    loja = next((u for u in painel(db)["unidades"] if u["id"] == unidade), None)
    produto = next((p for p in (loja or {}).get("produtos", []) if p["codigo"] == codigo), None)
    if produto is None or not produto.get("backtest"):
        raise ProdutoInexistente()
    return produto["backtest"]


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
    geracao = ultima_geracao(db)
    if geracao is not None:
        run, retrain = geracao
        modelos = db.execute(
            select(ModelArtifact, Product.name)
            .outerjoin(Product, Product.code == ModelArtifact.product_code)
            .where(ModelArtifact.retrain_id == retrain.id, ModelArtifact.level.in_(("unit", "product")))
        ).all()
        previsao = {
            "gerada_em": (run.finished_at or run.started_at).isoformat(timespec="seconds"),
            "dados_ate": str(retrain.data_until),
            "lojas": [{"id": m.unit_id, "status": m.status} for m, _ in modelos if m.level == "unit"],
            "produtos": [{"loja": m.unit_id, "codigo": m.product_code, "nome": nome,
                          "status": m.status if m.sarimax_order is not None else None}
                         for m, nome in modelos if m.level == "product"],
        }
    config = (geracao[1].config or {}) if geracao else {}
    return {
        "lojas": base_vendas.carregar_lojas(db),
        "categorias": _categorias(db),
        "configuracao": {"horizonte_dias": config.get("horizonte_dias", 14),
                         "limiar_encomenda_un": config.get("limiar_encomenda_un", LIMIAR_QTD_VENDA),
                         # falso no Render: o front não oferece "Atualizar os modelos"
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
        db.commit()  # solta a conexão antes do cálculo
        saida = {"gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
                 "limiar_encomenda_un": LIMIAR_QTD_VENDA, "unidades": {}}
        for u in lojas:
            v = df[df["unit_id"] == u["id"]]
            if len(v):
                saida["unidades"][u["id"]] = analisar_unidade(v, _fechados(cal, u["id"]))
        return saida

    return cache.obter("analises", versao, construir)
