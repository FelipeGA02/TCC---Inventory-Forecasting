"""Montagem do painel do frontend (formato `BaseReal` de `app-react/src/domain/types.ts`).

Lógica pura (pandas), sem banco nem HTTP: recebe as vendas, o calendário e os previsores
de um treino já lidos do banco e devolve o dicionário que a API entrega.

A parte descritiva (histórico, produtos, encomendas, contagens) é a de `gerar_unidade` em
`training_scripts/frontend_mock/gerar_dados_frontend.py`, calculada aqui a partir das
vendas até `retrain_history.data_until` — os resumos não são gravados no banco. A parte
de previsão (modelo da loja, desagregação por categoria, produtos regulares) vem pronta
do treino em `previsores`:

    previsores[loja] = {
        "loja": {"modelo": {...}, "backtest": [...], "previsao": [...]},
        "categorias": {categoria: {"status", "metricas", "backtest", "previsao"}},
        "produtos": {codigo: {"modelo": {...} | None, "backtest": [...], "previsao": [...]}},
    }

com cada ponto de `backtest` trazendo `origem` (início da rodada do walk-forward).
"""
from __future__ import annotations

import pandas as pd

DIA_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
JANELA_8_SEMANAS_DIAS = 56
IRREGULARES_POR_CATEGORIA = 8
ULTIMAS_ENCOMENDAS = 12


def r1(v) -> float:
    return round(float(v), 1)


def _sem_origem(pontos: list[dict]) -> list[dict]:
    return [{k: v for k, v in p.items() if k != "origem"} for p in pontos]


def _evento(dia) -> str | None:
    for nome in (dia["nome_feriado"], dia["data_comemorativa"]):
        if isinstance(nome, str) and nome:
            return nome
    return None


def rodadas(backtest: list[dict], fechados: set) -> list[dict]:
    """Erro de cada rodada do walk-forward (modelo e naïve) nos dias de loja aberta."""
    if not backtest:
        return []
    bt = pd.DataFrame(backtest)
    bt = bt[~pd.to_datetime(bt["data"]).isin(fechados)]
    return [{"origem": o, "erro_modelo": r1((g["previsto"] - g["real"]).abs().sum()),
             "erro_naive": r1((g["naive"] - g["real"]).abs().sum())}
            for o, g in bt.groupby("origem", sort=True)]


def montar_unidade(v: pd.DataFrame, cal_u: pd.DataFrame, loja: dict, ids_cat: list[str],
                   prev: dict) -> dict:
    """Uma loja do painel. `v`: vendas da loja (sem serviços) até o fim do treino;
    `cal_u`: calendário da loja indexado por data."""
    fluxo = v[~v["encomenda"]]
    enc = v[v["encomenda"]]
    ini, fim = v["emissao"].min(), v["emissao"].max()
    idx = pd.date_range(ini, fim, freq="D")
    fechados = set(cal_u.index[cal_u["loja_fechada"] == 1])

    # ---- Previsão (loja + categorias), com loja fechada e evento do calendário
    por_cat = {k: {d["data"]: d for d in prev["categorias"].get(k, {}).get("previsao", [])} for k in ids_cat}
    previsao = []
    for d in prev["loja"]["previsao"]:
        dia = pd.Timestamp(d["data"])
        c = cal_u.loc[dia] if dia in cal_u.index else None
        previsao.append({
            "data": d["data"], "dia_semana": DIA_CURTO[dia.weekday()],
            "loja_fechada": bool(c["loja_fechada"]) if c is not None else False,
            "evento": _evento(c) if c is not None else None,
            "previsto": d["previsto"], "inf": d["inf"], "sup": d["sup"],
            "categorias": {k: {x: por_cat[k].get(d["data"], {}).get(x, 0.0) for x in ("previsto", "inf", "sup")}
                           for k in ids_cat},
        })

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

    # ---- Produtos: regulares (com previsor no treino) + principais irregulares
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    cat_sku = fluxo.groupby("produto_cod")["cat"].agg(lambda x: x.mode().iloc[0])
    regulares = sorted(s for s in prev["produtos"] if cat_sku.get(s) in ids_cat)
    j8 = painel[painel["emissao"] >= ini8]
    vend8 = j8.groupby("produto_cod")["qtdade"].sum()
    irregulares = []
    for k in ids_cat:
        cand = vend8[[s for s in vend8.index if cat_sku.get(s) == k and s not in prev["produtos"]]]
        irregulares += list(cand.sort_values(ascending=False).head(IRREGULARES_POR_CATEGORIA).index)

    nomes = v.groupby("produto_cod")["produto_nome"].last()
    subcats = v.groupby("produto_cod")["categoria_fina"].agg(lambda x: x.mode().iloc[0])
    vendido_total = fluxo.groupby("produto_cod")["qtdade"].sum()
    vendido_enc = enc.groupby("produto_cod")["qtdade"].sum()
    produtos = []
    for s in regulares + irregulares:
        d = matriz[s] if s in matriz else pd.Series(0.0, index=idx)
        desde_1a = d[d.index >= d[d > 0].index.min()] if (d > 0).any() else d
        aberto = desde_1a[~desde_1a.index.isin(fechados)]
        sem8 = (desde_1a.reindex(pd.date_range(ini8, fim), fill_value=0)
                .resample("W-SUN", label="left", closed="left").sum())
        p = prev["produtos"].get(s)
        mod = p["modelo"] if p else None
        previsao_p = p["previsao"] if p and mod else []
        produtos.append({
            "codigo": s, "nome": nomes[s], "categoria": cat_sku[s], "subcategoria": subcats[s],
            "regular": s in prev["produtos"],
            "dias_com_venda": int((desde_1a > 0).sum()),
            "pct_dias_abertos_com_venda": r1((aberto > 0).mean() * 100) if len(aberto) else 0.0,
            "media_dia_aberto": r1(aberto.mean()) if len(aberto) else 0.0,
            "vendido_8_semanas": r1(vend8.get(s, 0.0)),
            "vendido_total": r1(vendido_total.get(s, 0.0)),
            "vendido_em_encomendas": r1(vendido_enc.get(s, 0.0)),
            "historico_semanal": [r1(x) for x in sem8.values],
            "historico_diario": [{"data": str(dt.date()), "vendido": r1(x)}
                                 for dt, x in d.loc[fim - pd.Timedelta(days=27):fim].items()],
            "modelo": mod,
            "previsao": previsao_p,
            "previsao_14d": r1(sum(x["previsto"] for x in previsao_p)) if mod else None,
            "backtest": _sem_origem(p["backtest"]) if p and mod else [],
        })

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

    modelo = {**prev["loja"]["modelo"], "rodadas": rodadas(prev["loja"]["backtest"], fechados)}
    return {
        **loja,
        "periodo": {"inicio": str(ini.date()), "fim": str(fim.date()), "dias": len(idx)},
        "linhas": int(len(v)), "skus_vendidos": int(v["produto_cod"].nunique()),
        "volume_total": r1(painel["qtdade"].sum()),
        "volume_flores_de_corte": r1(fluxo.loc[fluxo["cat"] == "flores-de-corte", "qtdade"].sum()),
        "volume_por_categoria": {k: r1(painel.loc[painel["cat"] == k, "qtdade"].sum()) for k in ids_cat},
        "skus_por_categoria": {k: int(painel.loc[painel["cat"] == k, "produto_cod"].nunique()) for k in ids_cat},
        "regulares_por_categoria": {k: sum(1 for s in regulares if cat_sku[s] == k) for k in ids_cat},
        "volume_regulares_8_semanas_pct": {
            k: r1(sum(vend8.get(s, 0) for s in regulares if cat_sku[s] == k)
                  / max(1.0, float(j8.loc[j8["cat"] == k, "qtdade"].sum())) * 100) for k in ids_cat},
        # Flores de corte é categoria do painel desde a taxonomia de 4 categorias
        "flores_regulares_fora_do_painel": 0,
        "encomendas": encomendas,
        "modelo": modelo,
        "desagregacao": {k: {"metricas": c["metricas"], "status": c["status"], "backtest": _sem_origem(c["backtest"])}
                         for k in ids_cat if (c := prev["categorias"].get(k))},
        "previsao": previsao,
        "historico_diario": historico_diario,
        "historico_semanal": historico_semanal,
        "produtos": produtos,
        "backtest": _sem_origem(prev["loja"]["backtest"]),
    }


def amostra_registros(df: pd.DataFrame, lojas: list[dict]) -> list[dict]:
    """Últimos 2 dias com venda de cada loja — o cliente vira só o tipo."""
    linhas = []
    for u in lojas:
        v = df[df["unit_id"] == u["id"]]
        dias = sorted(v["emissao"].unique())[-2:]
        for r in v[v["emissao"].isin(dias)].sort_values(["emissao", "doc_numero"]).itertuples():
            linhas.append({
                "data": str(pd.Timestamp(r.emissao).date()), "documento": r.doc_numero,
                "codigo": r.produto_cod, "produto": r.produto_nome, "unidade": u["id"],
                "categoria": r.cat, "quantidade": r1(r.qtdade), "valor": round(float(r.vl_total), 2),
                "tipo_cliente": "Cadastrado" if r.cadastrado else "Consumidor",
                "encomenda": bool(r.encomenda),
            })
    return linhas


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
        "fonte": "banco de dados (vendas, calendário e o último treino concluído)",
        "base": {
            "inicio": str(df["emissao"].min().date()), "fim": str(df["emissao"].max().date()),
            "linhas": int(len(df)), "skus": int(df["produto_cod"].nunique()),
            "skus_por_categoria": {k: int(prods.get(k, 0)) for k in ids_cat},
        },
        "configuracao": configuracao,
        "categorias": categorias,
        "unidades": unidades,
        "registros_amostra": amostra_registros(df, lojas),
        "importacao": importacao,
    }
