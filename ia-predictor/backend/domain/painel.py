"""Montagem do painel do frontend (formato `BaseReal` de `app-react/src/domain/types.ts`).

Lógica pura (pandas), sem banco nem HTTP: recebe as vendas, o calendário e os previsores
do último treino concluído já lidos do banco e devolve o dicionário que a API entrega.

A parte descritiva (histórico, produtos, encomendas, contagens) é calculada das vendas até
`forecast_jobs.data_until` — os resumos não são gravados no banco. A parte de previsão vem
pronta do treino (ADR-017: SARIMAX direto em cada categoria e em cada produto de grama, por
loja) em `previsores`:

    previsores[loja] = {
        "categorias": {categoria: {"modelo": {...} | None, "previsao": [...], "backtest": [...]}},
        "produtos": {codigo: {"modelo": {...} | None, "previsao": [...]}},
    }

`modelo` = {ordem, ordem_sazonal, aic, status, metricas, mensagem} (sem previsão, só
`status` e `mensagem`); `backtest` = o 1º dia de cada janela do walk-forward (h = 1). A
previsão da loja é a soma das 4 categorias, dia a dia — inclusive os limites da faixa, o
que dá uma faixa conservadora (mais larga que a exata da soma).
"""
from __future__ import annotations

import pandas as pd

DIA_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
JANELA_8_SEMANAS_DIAS = 56
ULTIMAS_ENCOMENDAS = 12
_FAIXA = ("previsto", "inf", "sup")


def r1(v) -> float:
    return round(float(v), 1)


def metricas_da_tela(m: dict | None) -> dict | None:
    """Métricas do walk-forward (`series_models.metrics`) com os nomes do frontend
    (`MetricasModelo`): cada origem é uma previsão de 14 dias, a "rodada" da tela. Treino
    anterior à contagem de origens vencidas a calcula pela porcentagem."""
    if not m:
        return None
    rodadas = m.get("origens")
    vence = m.get("origens_vence_naive")
    if vence is None and rodadas and m.get("origens_vence_naive_pct") is not None:
        vence = round(m["origens_vence_naive_pct"] * rodadas / 100)
    return {"rodadas": rodadas, "rodadas_vence_naive": vence,
            **{k: m.get(k) for k in ("dias_avaliados", "mae", "mase", "erro_relativo_naive", "cobertura_ic95_pct",
                                     "largura_ic95", "venda_media_dia", "previsto_sobre_real_pct",
                                     "erro_total_14d_pct", "ljung_box_p", "shapiro_p")}}


def _evento(dia) -> str | None:
    for nome in (dia["nome_feriado"], dia["data_comemorativa"]):
        if isinstance(nome, str) and nome:
            return nome
    return None


def _previsao_da_loja(prev: dict, cal_u: pd.DataFrame, ids_cat: list[str]) -> list[dict]:
    """Os dias previstos das categorias, com loja fechada e evento do calendário; o total do
    dia é a soma das categorias (categoria sem previsão entra com zero)."""
    por_cat = {k: {d["data"]: d for d in (prev["categorias"].get(k) or {}).get("previsao", [])} for k in ids_cat}
    datas = sorted({d for dias in por_cat.values() for d in dias})
    previsao = []
    for data in datas:
        dia = pd.Timestamp(data)
        c = cal_u.loc[dia] if dia in cal_u.index else None
        cats = {k: {x: por_cat[k].get(data, {}).get(x, 0.0) for x in _FAIXA} for k in ids_cat}
        previsao.append({
            "data": data, "dia_semana": DIA_CURTO[dia.weekday()],
            "loja_fechada": bool(c["loja_fechada"]) if c is not None else dia.weekday() == 6,
            "evento": _evento(c) if c is not None else None,
            **{x: round(sum(cats[k][x] for k in ids_cat), 3) for x in _FAIXA},
            "categorias": cats,
        })
    return previsao


def montar_unidade(v: pd.DataFrame, cal_u: pd.DataFrame, loja: dict, ids_cat: list[str],
                   prev: dict) -> dict:
    """Uma loja do painel. `v`: vendas da loja (sem serviços) até o fim do treino;
    `cal_u`: calendário da loja indexado por data."""
    fluxo = v[~v["encomenda"]]
    enc = v[v["encomenda"]]
    ini, fim = v["emissao"].min(), v["emissao"].max()
    idx = pd.date_range(ini, fim, freq="D")
    fechados = set(cal_u.index[cal_u["loja_fechada"] == 1])

    # ---- Histórico (venda sem encomendas por categoria + encomendas à parte)
    painel = fluxo[fluxo["cat"].isin(ids_cat)]
    diario = (painel.groupby(["emissao", "cat"])["qtdade"].sum().unstack(fill_value=0)
              .reindex(index=idx, columns=ids_cat, fill_value=0))
    enc_dia = enc[enc["cat"].isin(ids_cat)].groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    ini8 = fim - pd.Timedelta(days=JANELA_8_SEMANAS_DIAS - 1)
    historico_diario = [
        {"data": str(d.date()), "dia_semana": DIA_CURTO[d.weekday()], "total": r1(row.sum()),
         "encomendas": r1(enc_dia.loc[d]), "categorias": {k: r1(row.get(k, 0)) for k in ids_cat}}
        for d, row in diario.loc[ini8:fim].iterrows()]
    sem = diario.resample("W-SUN", label="left", closed="left").sum()
    sem_enc = enc_dia.resample("W-SUN", label="left", closed="left").sum()
    historico_semanal = [
        {"semana": str((d + pd.Timedelta(days=1)).date()), "total": r1(row.sum()),
         "encomendas": r1(sem_enc.loc[d]), "categorias": {k: r1(row.get(k, 0)) for k in ids_cat}}
        for d, row in sem.iterrows()]

    # ---- Produtos de grama do treino (com ou sem modelo), na ordem da previsão de 14 dias
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    cat_sku = v.groupby("produto_cod")["cat"].agg(lambda x: x.mode().iloc[0])
    j8 = painel[painel["emissao"] >= ini8]
    vend8 = j8.groupby("produto_cod")["qtdade"].sum()
    nomes = v.groupby("produto_cod")["produto_nome"].last()
    subcats = v.groupby("produto_cod")["categoria_fina"].agg(lambda x: x.mode().iloc[0])
    vendido_total = fluxo.groupby("produto_cod")["qtdade"].sum()
    vendido_enc = enc.groupby("produto_cod")["qtdade"].sum()
    produtos = []
    for s, p in prev["produtos"].items():
        if s not in nomes.index:
            continue  # produto do treino sem venda na loja até o fim do treino
        d = matriz[s] if s in matriz else pd.Series(0.0, index=idx)
        desde_1a = d[d.index >= d[d > 0].index.min()] if (d > 0).any() else d
        aberto = desde_1a[~desde_1a.index.isin(fechados)]
        sem8 = (desde_1a.reindex(pd.date_range(ini8, fim), fill_value=0)
                .resample("W-SUN", label="left", closed="left").sum())
        previsao_p = p["previsao"]  # vazia quando o produto ficou sem modelo neste treino
        produtos.append({
            "codigo": s, "nome": nomes[s], "categoria": cat_sku[s], "subcategoria": subcats[s],
            "dias_com_venda": int((desde_1a > 0).sum()),
            "pct_dias_abertos_com_venda": r1((aberto > 0).mean() * 100) if len(aberto) else 0.0,
            "media_dia_aberto": r1(aberto.mean()) if len(aberto) else 0.0,
            "vendido_8_semanas": r1(vend8.get(s, 0.0)),
            "vendido_total": r1(vendido_total.get(s, 0.0)),
            "vendido_em_encomendas": r1(vendido_enc.get(s, 0.0)),
            "historico_semanal": [r1(x) for x in sem8.values],
            "historico_diario": [{"data": str(dt.date()), "vendido": r1(x)}
                                 for dt, x in d.loc[fim - pd.Timedelta(days=27):fim].items()],
            "modelo": p["modelo"],
            "previsao": previsao_p,
            "previsao_14d": r1(sum(x["previsto"] for x in previsao_p)) if previsao_p else None,
        })
    produtos.sort(key=lambda x: (x["previsao_14d"] is None, -(x["previsao_14d"] or x["vendido_8_semanas"])))

    # ---- Encomendas: resumo e últimas
    if len(enc):
        docs = (enc.groupby(["emissao", "doc_numero"])
                .apply(lambda g: pd.Series({"volume": g["qtdade"].sum(),
                                            "produtos": list(g.groupby("produto_nome")["qtdade"].sum()
                                                             .sort_values(ascending=False).head(3).index)}))
                .reset_index().sort_values("emissao"))
        ultimas = [{"data": str(r.emissao.date()), "volume": r1(r.volume), "produtos": r.produtos}
                   for r in docs.tail(ULTIMAS_ENCOMENDAS).iloc[::-1].itertuples()]
    else:
        docs, ultimas = [], []
    encomendas = {
        "vendas": int(len(docs)), "dias": int(enc["emissao"].nunique()),
        "volume": r1(enc["qtdade"].sum()),
        "pct_volume": r1(enc["qtdade"].sum() / v["qtdade"].sum() * 100) if v["qtdade"].sum() else 0.0,
        "ultimas": ultimas,
    }

    return {
        **loja,
        "periodo": {"inicio": str(ini.date()), "fim": str(fim.date()), "dias": len(idx)},
        "linhas": int(len(v)), "skus_vendidos": int(v["produto_cod"].nunique()),
        "volume_total": r1(painel["qtdade"].sum()),
        "volume_flores_de_corte": r1(fluxo.loc[fluxo["cat"] == "flores-de-corte", "qtdade"].sum()),
        "volume_por_categoria": {k: r1(painel.loc[painel["cat"] == k, "qtdade"].sum()) for k in ids_cat},
        "skus_por_categoria": {k: int(painel.loc[painel["cat"] == k, "produto_cod"].nunique()) for k in ids_cat},
        "encomendas": encomendas,
        "categorias_modelo": {k: (prev["categorias"].get(k) or {}).get("modelo") for k in ids_cat},
        "previsao": _previsao_da_loja(prev, cal_u, ids_cat),
        "historico_diario": historico_diario,
        "historico_semanal": historico_semanal,
        "produtos": produtos,
        "backtest_categorias": {k: (prev["categorias"].get(k) or {}).get("backtest", []) for k in ids_cat},
    }


def venda_diaria(v: pd.DataFrame, coluna: str, item: str, fim: pd.Timestamp) -> pd.Series | None:
    """Venda diária sem encomendas grandes de uma categoria (`coluna="cat"`) ou produto
    (`"produto_cod"`) da loja `v`: da 1ª venda da loja (categoria) ou do produto até `fim`.
    `None` se o item não vendeu na loja."""
    fluxo = v[~v["encomenda"] & (v["emissao"] <= fim)]
    do_item = fluxo[fluxo[coluna] == item]
    if do_item.empty:
        return None
    ini = (fluxo if coluna == "cat" else do_item)["emissao"].min()
    return do_item.groupby("emissao")["qtdade"].sum().reindex(pd.date_range(ini, fim, freq="D"), fill_value=0.0)


def montar_painel(df: pd.DataFrame, cal: pd.DataFrame, lojas: list[dict], categorias: list[dict],
                  previsores: dict, configuracao: dict, gerado_em: str, importacao: dict) -> dict:
    """Painel completo. `df`: vendas (sem serviços) até o fim do treino; `cal`: calendário
    com a coluna `unit_id`; `categorias`: as do painel, na ordem das telas."""
    ids_cat = [c["id"] for c in categorias]
    prods = df.groupby("cat")["produto_cod"].nunique()
    unidades = []
    for u in lojas:
        if u["id"] not in previsores:
            continue
        cal_u = cal[cal["unit_id"] == u["id"]].set_index("data")
        unidades.append(montar_unidade(df[df["unit_id"] == u["id"]], cal_u, u, ids_cat, previsores[u["id"]]))
    return {
        "gerado_em": gerado_em,
        "fonte": "banco de dados (vendas, calendário e o último treino concluído da previsão)",
        "base": {
            "inicio": str(df["emissao"].min().date()), "fim": str(df["emissao"].max().date()),
            "linhas": int(len(df)), "skus": int(df["produto_cod"].nunique()),
            "skus_por_categoria": {k: int(prods.get(k, 0)) for k in ids_cat},
        },
        "configuracao": configuracao,
        "categorias": categorias,
        "unidades": unidades,
        "importacao": importacao,
    }
