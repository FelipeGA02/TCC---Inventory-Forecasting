"""Analises descritivas da base de vendas para o painel inicial do frontend.

So estatistica descritiva, sem modelo: roda em segundos e grava
`app-react/src/app/data/analises.json`, separado de `baseReal.json` (que tem as previsoes e
leva ~40 min para gerar).

Por unidade:
  * resumo: notas, linhas, volume, faturamento liquido, produtos, encomendas;
  * mes a mes: notas, volume e faturamento (com e sem encomendas) e volume por categoria;
  * dia da semana: media por dia de loja aberta no ultimo ano (sem encomendas);
  * consumidor x cliente cadastrado (so agregados — nenhum dado pessoal);
  * forma de pagamento (faturamento e notas);
  * produtos mais vendidos no ultimo ano, por volume e por faturamento.

Faturamento = soma de `tot_liq` (valor liquido da linha, ja com desconto; devolucoes entram
negativas). Encomenda = nota com mais de 2.000 un. (ADR-013), como no resto do sistema.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.frontend_mock.gerar_analises_frontend
"""
from __future__ import annotations

import json
import os

import pandas as pd

from training_scripts.frontend_mock.gerar_dados_frontend import (
    BASE, CALENDARIO, CAT_FORA, CAT_POR_GRUPO, DIA_CURTO, IDS_CAT, UNIDADES, r1,
)
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA, marcar_encomendas

_AQUI = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
SAIDA = os.path.join(_REPO, "app-react", "src", "app", "data", "analises.json")

CATS_ANALISE = IDS_CAT + [CAT_FORA]          # no painel descritivo, flores de corte aparecem
TOP_PRODUTOS = 10
TOP_PAGAMENTOS = 6


def carregar() -> pd.DataFrame:
    cols = ["doc_numero", "emissao", "pagamento", "cliente_nome", "produto_cod", "produto_nome",
            "qtdade", "tot_liq", "unidade", "categoria", "grupo"]
    df = pd.read_csv(BASE, sep=";", usecols=cols, dtype={"produto_cod": str, "doc_numero": str,
                                                         "cliente_nome": str, "pagamento": str})
    df = df[df["grupo"] != "Servico e taxa"].copy()
    df["emissao"] = pd.to_datetime(df["emissao"])
    df["cat"] = df["grupo"].map(CAT_POR_GRUPO).fillna(CAT_FORA)
    df["encomenda"] = marcar_encomendas(df, LIMIAR_QTD_VENDA)
    df["cadastrado"] = df["cliente_nome"].fillna("").str.strip().str.upper() != "CONSUMIDOR"
    df["pagamento"] = df["pagamento"].fillna("").str.strip().replace("", "NÃO INFORMADO")
    df["nota"] = df["emissao"].dt.strftime("%Y%m%d") + "-" + df["doc_numero"]
    return df


def _agregado(d: pd.DataFrame) -> dict:
    return {"notas": int(d["nota"].nunique()), "volume": r1(d["qtdade"].sum()),
            "faturamento": round(float(d["tot_liq"].sum()), 2)}


def analisar_unidade(v: pd.DataFrame, fechados: set) -> dict:
    fim = v["emissao"].max()
    ini12 = (fim - pd.DateOffset(years=1)) + pd.Timedelta(days=1)
    ult = v[v["emissao"] >= ini12]
    fluxo = v[~v["encomenda"]]
    enc = v[v["encomenda"]]

    # ---- mes a mes
    v = v.assign(mes=v["emissao"].dt.strftime("%Y-%m"))
    mensal = []
    for mes, g in v.groupby("mes"):
        f, e = g[~g["encomenda"]], g[g["encomenda"]]
        mensal.append({
            "mes": mes, **_agregado(g),
            "volume_encomendas": r1(e["qtdade"].sum()),
            "faturamento_encomendas": round(float(e["tot_liq"].sum()), 2),
            "categorias": {c: r1(f.loc[f["cat"] == c, "qtdade"].sum()) for c in CATS_ANALISE},
        })

    # ---- dia da semana (ultimo ano, sem encomendas, dias de loja aberta)
    f12 = fluxo[fluxo["emissao"] >= ini12]
    dias = pd.date_range(ini12, fim, freq="D")
    abertos = [d for d in dias if d not in fechados]
    por_dia = f12.groupby("emissao").agg(volume=("qtdade", "sum"), faturamento=("tot_liq", "sum"),
                                         notas=("nota", "nunique")).reindex(abertos, fill_value=0)
    dia_semana = []
    for w in range(7):
        g = por_dia[por_dia.index.weekday == w]
        # Domingo: a loja so abre em datas excepcionais (Dia das Maes, Finados). Media de 1 ou
        # 2 dias nao representa o dia da semana — marca como fechado.
        if len(g) < 4:
            dia_semana.append({"dia": DIA_CURTO[w], "dias_abertos": int(len(g)), "fechado": True,
                               "volume_medio": 0.0, "faturamento_medio": 0.0, "notas_medias": 0.0})
            continue
        dia_semana.append({"dia": DIA_CURTO[w], "dias_abertos": int(len(g)), "fechado": False,
                           "volume_medio": r1(g["volume"].mean()) if len(g) else 0.0,
                           "faturamento_medio": round(float(g["faturamento"].mean()), 2) if len(g) else 0.0,
                           "notas_medias": r1(g["notas"].mean()) if len(g) else 0.0})

    # ---- consumidor x cadastrado, forma de pagamento
    tipo_cliente = {"consumidor": _agregado(v[~v["cadastrado"]]), "cadastrado": _agregado(v[v["cadastrado"]])}
    pag = (v.groupby("pagamento").agg(faturamento=("tot_liq", "sum"), notas=("nota", "nunique"))
           .sort_values("faturamento", ascending=False))
    principais = pag.head(TOP_PAGAMENTOS)
    resto = pag.iloc[TOP_PAGAMENTOS:]
    pagamento = [{"forma": f.title(), "faturamento": round(float(r.faturamento), 2), "notas": int(r.notas)}
                 for f, r in principais.iterrows()]
    if len(resto):
        pagamento.append({"forma": "Outras", "faturamento": round(float(resto["faturamento"].sum()), 2),
                          "notas": int(resto["notas"].sum())})

    # ---- produtos mais vendidos no ultimo ano
    prod = ult.groupby("produto_cod").agg(volume=("qtdade", "sum"), faturamento=("tot_liq", "sum"),
                                          notas=("nota", "nunique"),
                                          cat=("cat", lambda x: x.mode().iloc[0]))
    nomes = ult.sort_values("emissao").groupby("produto_cod")["produto_nome"].last()

    def top(col):
        return [{"codigo": c, "nome": nomes[c], "categoria": r["cat"], "volume": r1(r["volume"]),
                 "faturamento": round(float(r["faturamento"]), 2), "notas": int(r["notas"])}
                for c, r in prod.sort_values(col, ascending=False).head(TOP_PRODUTOS).iterrows()]

    return {
        "periodo": {"inicio": str(v["emissao"].min().date()), "fim": str(fim.date()),
                    "inicio_ultimo_ano": str(ini12.date())},
        "resumo": {**_agregado(v), "linhas": int(len(v)), "produtos": int(v["produto_cod"].nunique()),
                   "encomendas": _agregado(enc), "sem_encomendas": _agregado(fluxo)},
        "categorias": {c: {**_agregado(v[v["cat"] == c]), "produtos": int(v.loc[v["cat"] == c, "produto_cod"].nunique())}
                       for c in CATS_ANALISE},
        "mensal": mensal,
        "dia_semana": dia_semana,
        "tipo_cliente": tipo_cliente,
        "pagamento": pagamento,
        "top_volume": top("volume"),
        "top_faturamento": top("faturamento"),
    }


def main():
    df = carregar()
    cal = pd.read_csv(CALENDARIO, sep=";", parse_dates=["data"])
    saida = {"gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
             "limiar_encomenda_un": LIMIAR_QTD_VENDA, "unidades": {}}
    for u in UNIDADES:
        fech = set(cal.loc[(cal["unidade"] == u["nome"]) & (cal["loja_fechada"] == 1), "data"])
        saida["unidades"][u["id"]] = analisar_unidade(df[df["unidade"] == u["nome"]], fech)
        r = saida["unidades"][u["id"]]["resumo"]
        print(f"[{u['nome']}] {r['notas']:,} notas · {r['volume']:,.0f} un. · R$ {r['faturamento']:,.0f}")
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"[ok] {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
