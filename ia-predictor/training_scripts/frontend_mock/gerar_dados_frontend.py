"""Gera os dados que o frontend (app-react) usa enquanto a API nao esta conectada.

Nada aqui e inventado: todo numero sai da base real pre-processada (`output/`) e do mesmo
SARIMAX do L1 usado nos treinos (`baseline/sarimax_itabirito_core.py`), rodado para as
duas unidades.

O que e gerado (um JSON so, `app-react/src/app/data/baseReal.json`):

  * historico diario (ultimas 8 semanas) e semanal (base inteira) por unidade e categoria;
  * previsao L1 de 14 dias por unidade — SARIMAX em log1p da venda total, d = 1, m = 7,
    exogenas de calendario; ponto = mediana (`expm1`), faixa = IC 95%;
  * desagregacao L2 em cascata: unidade -> categoria (participacao das ultimas 8 semanas
    por dia da semana) -> SKU (participacao do SKU na categoria nas ultimas 8 semanas);
  * walk-forward de validacao (26 rodadas, origem a cada 14 dias, h = 14) com MASE,
    erro relativo a naive sazonal, cobertura e largura do IC 95%;
  * amostra de registros reais (sem dados de cliente) e log de importacao das planilhas.

Categorias do painel (vocabulario da loja, a partir do `grupo` da Etapa 3):
    Grama               <- grupo "Grama"
    Plantas diversas    <- grupo "Plantas diversas" (todas as plantas, exceto flores de corte)
    Produtos de jardim  <- grupo "Insumos e acessorios" (substrato, adubo, vaso, insumo)
"Flores de corte" (~1,8% do volume) entra no total do L1 mas nao tem painel proprio: o
total exibido e a soma das tres categorias.

Uso (a partir de `ia-predictor/`, depois do pre-processamento):
    python -m training_scripts.frontend_mock.gerar_dados_frontend
"""
from __future__ import annotations

import itertools
import json
import os
import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

_AQUI = os.path.dirname(os.path.abspath(__file__))
_TRAINING_SCRIPTS = os.path.dirname(_AQUI)
_REPO = os.path.dirname(os.path.dirname(_TRAINING_SCRIPTS))
OUTPUT_DIR = os.path.join(_TRAINING_SCRIPTS, "output")
BASE = os.path.join(OUTPUT_DIR, "BaseClassificada03.csv")
CALENDARIO = os.path.join(OUTPUT_DIR, "calendario_diario.csv")
LOG_IMPORTACAO = os.path.join(OUTPUT_DIR, "processamento_log.json")
RELATORIO_PRE = os.path.join(OUTPUT_DIR, "preprocessamento_relatorio.json")
SAIDA = os.path.join(_REPO, "app-react", "src", "app", "data", "baseReal.json")

# Mesmos parametros do L1 (CLAUDE.md e sarimax_itabirito_core.py).
M = 7
D_REGULAR, D_SAZONAL = 1, 0
GRID_PQ, GRID_SPQ = range(0, 3), range(0, 2)
ALPHA = 0.05
MAXITER = 200
HORIZONTE = 14
PRIMEIRA_ORIGEM = pd.Timestamp("2025-03-02")
PASSO_ORIGEM = 14                 # 26 rodadas cobrindo um ano (protocolo do doc 04)
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CALENDARIO = ["loja_fechada", "abertura_excepcional"]
COLS_EXOG = [f"dia_{d}" for d in DIAS] + COLS_CALENDARIO

JANELA_SHARE_DIAS = 56            # participacao movel: ultimas 8 semanas
SKUS_POR_CATEGORIA = 10
MIN_DIAS_COM_VENDA, MIN_VENDAS = 28, 8   # abaixo disso: rateio uniforme da categoria

UNIDADES = [
    {"id": "jardim-canada", "nome": "Jardim Canadá", "cidade": "Nova Lima"},
    {"id": "itabirito", "nome": "Itabirito", "cidade": "Itabirito"},
]
CATEGORIAS = [
    {"id": "grama", "nome": "Grama", "grupo": "Grama",
     "descricao": "Grama em placa, rolo e muda (esmeralda, amendoim, são carlos…)"},
    {"id": "plantas-diversas", "nome": "Plantas diversas", "grupo": "Plantas diversas",
     "descricao": "Todas as plantas, exceto flores de corte: mudas, forrações, plantas em vaso, "
                  "arbustos, hortaliças e ervas"},
    {"id": "produtos-de-jardim", "nome": "Produtos de jardim", "grupo": "Insumos e acessórios",
     "descricao": "Substratos, adubos, vasos, ferramentas e demais insumos de jardinagem"},
]
CAT_POR_GRUPO = {c["grupo"]: c["id"] for c in CATEGORIAS}
CAT_FORA = "flores-de-corte"
DIA_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
def carregar_base() -> pd.DataFrame:
    cols = ["doc_numero", "emissao", "cliente_nome", "produto_cod", "produto_nome", "qtdade",
            "vl_total", "unidade", "categoria_fina", "grupo"]
    df = pd.read_csv(BASE, sep=";", usecols=cols, dtype={"produto_cod": str, "doc_numero": str,
                                                         "cliente_nome": str})
    df = df[df["grupo"] != "Servico e taxa"].copy()
    df["emissao"] = pd.to_datetime(df["emissao"])
    df["cat"] = df["grupo"].map(CAT_POR_GRUPO).fillna(CAT_FORA)
    return df


def carregar_calendario() -> pd.DataFrame:
    cal = pd.read_csv(CALENDARIO, sep=";")
    cal["data"] = pd.to_datetime(cal["data"])
    return cal


def exogenas(cal: pd.DataFrame, unidade: str, idx: pd.DatetimeIndex) -> pd.DataFrame:
    c = cal[cal["unidade"] == unidade].set_index("data")[COLS_CALENDARIO].astype(float)
    X = pd.DataFrame(index=idx)
    for i, nome in enumerate(DIAS):
        X[f"dia_{nome}"] = (idx.weekday == i).astype(float)
    X[COLS_CALENDARIO] = c.reindex(idx)[COLS_CALENDARIO]
    if X.isna().any().any():
        raise ValueError(f"calendario de {unidade} nao cobre todo o periodo")
    return X[COLS_EXOG]


# --------------------------------------------------------------------------- #
# L1 — SARIMAX (mesma especificacao do treino)
# --------------------------------------------------------------------------- #
def ajustar(z, X, order, sorder):
    return SARIMAX(z, exog=X, order=order, seasonal_order=sorder, trend="n",
                   enforce_stationarity=False, enforce_invertibility=False
                   ).fit(disp=False, maxiter=MAXITER)


def selecionar_ordem(z, X) -> dict:
    melhor = None
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        try:
            res = ajustar(z, X, (p, D_REGULAR, q), (P, D_SAZONAL, Q, M))
        except Exception:  # noqa: BLE001
            continue
        if np.isfinite(res.aic) and (melhor is None or res.aic < melhor["aic"]):
            melhor = {"order": (p, D_REGULAR, q), "seasonal_order": (P, D_SAZONAL, Q, M),
                      "aic": float(res.aic)}
    return melhor


def prever(y, X, ordem, futuro):
    res = ajustar(np.log1p(y.clip(lower=0)), X.loc[y.index], ordem["order"],
                  ordem["seasonal_order"])
    fc = res.get_forecast(len(futuro), exog=X.loc[futuro])
    mu, ic = np.asarray(fc.predicted_mean), np.asarray(fc.conf_int(alpha=ALPHA))
    def volta(v):
        return np.clip(np.expm1(v), 0, None)
    return volta(mu), volta(ic[:, 0]), volta(ic[:, 1])


def walk_forward(y, X, ordem) -> tuple[pd.DataFrame, list[dict]]:
    ultima = y.index.max() - pd.Timedelta(days=HORIZONTE - 1)
    linhas, rodadas = [], []
    for origem in pd.date_range(PRIMEIRA_ORIGEM, ultima, freq=f"{PASSO_ORIGEM}D"):
        treino = y[y.index < origem]
        futuro = pd.date_range(origem, periods=HORIZONTE, freq="D")
        prev, lo, hi = prever(treino, X, ordem, futuro)
        ult7 = treino.values[-M:]
        naive = np.array([ult7[i % M] for i in range(HORIZONTE)])
        escala = float(np.mean(np.abs(treino.values[M:] - treino.values[:-M])))
        real = y.loc[futuro].values
        rodadas.append({"origem": str(origem.date()),
                        "erro_modelo": float(np.abs(real - prev).sum()),
                        "erro_naive": float(np.abs(real - naive).sum())})
        for h in range(HORIZONTE):
            linhas.append({"data": futuro[h], "previsto": prev[h], "ic_inf": lo[h],
                           "ic_sup": hi[h], "real": real[h], "naive": naive[h],
                           "escala": escala})
    return pd.DataFrame(linhas), rodadas


def metricas(d: pd.DataFrame, rodadas: list[dict]) -> dict:
    erro = (d["real"] - d["previsto"]).abs()
    erro_naive = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    aberto = d["real"] > 0
    return {
        "rodadas": len(rodadas),
        "rodadas_vence_naive": int(sum(r["erro_modelo"] < r["erro_naive"] for r in rodadas)),
        "dias_avaliados": int(len(d)),
        "mae": round(float(erro.mean()), 1),
        "mase": round(float((erro / d["escala"]).mean()), 3),
        "erro_relativo_naive": round(float(erro.sum() / erro_naive.sum()), 3),
        "cobertura_ic95_pct": round(float(dentro.mean() * 100), 1),
        "largura_ic95": round(float((d["ic_sup"] - d["ic_inf"]).mean()), 1),
        "previsto_sobre_real_pct": round(float(d["previsto"].sum() / d["real"].sum() * 100), 1),
        "mape_dias_abertos_pct": round(float((erro[aberto] / d.loc[aberto, "real"]).mean() * 100), 1),
    }


def status_modelo(m: dict) -> str:
    ok = m["mase"] < 1.0 and 90 <= m["cobertura_ic95_pct"] <= 98
    return "trained" if ok else "low_confidence"


# --------------------------------------------------------------------------- #
# L2 — desagregacao em cascata
# --------------------------------------------------------------------------- #
def shares_por_dia_semana(vendas: pd.DataFrame, fim: pd.Timestamp) -> dict[str, list[float]]:
    """Participacao de cada categoria por dia da semana nas ultimas 8 semanas."""
    ini = fim - pd.Timedelta(days=JANELA_SHARE_DIAS - 1)
    j = vendas[(vendas["emissao"] >= ini) & (vendas["emissao"] <= fim)]
    tab = j.groupby([j["emissao"].dt.weekday, "cat"])["qtdade"].sum().unstack(fill_value=0)
    geral = j.groupby("cat")["qtdade"].sum()
    geral = geral / geral.sum()
    cats = [c["id"] for c in CATEGORIAS] + [CAT_FORA]
    out = {c: [] for c in cats}
    for w in range(7):
        linha = tab.loc[w] if w in tab.index else None
        tot = float(linha.sum()) if linha is not None else 0.0
        for c in cats:
            if tot > 0:
                out[c].append(float(linha.get(c, 0.0)) / tot)
            else:                          # domingo (loja fechada): participacao geral
                out[c].append(float(geral.get(c, 0.0)))
    return out


def r1(v) -> float:
    return round(float(v), 1)


# --------------------------------------------------------------------------- #
# Montagem por unidade
# --------------------------------------------------------------------------- #
def gerar_unidade(df: pd.DataFrame, cal: pd.DataFrame, u: dict) -> dict:
    t0 = time.time()
    v = df[df["unidade"] == u["nome"]]
    ini, fim = v["emissao"].min(), v["emissao"].max()
    idx = pd.date_range(ini, fim, freq="D")
    y = v.groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=HORIZONTE, freq="D")
    X = exogenas(cal, u["nome"], idx.append(futuro))

    pre = y[y.index < PRIMEIRA_ORIGEM]
    ordem = selecionar_ordem(np.log1p(pre), X.loc[pre.index])
    print(f"[{u['nome']}] ordem {ordem['order']}{ordem['seasonal_order']} AIC {ordem['aic']:.1f}",
          flush=True)
    bt, rodadas = walk_forward(y, X, ordem)
    met = metricas(bt, rodadas)
    print(f"[{u['nome']}] walk-forward: MASE {met['mase']} · vs naive "
          f"{met['erro_relativo_naive']} · IC95 {met['cobertura_ic95_pct']}%", flush=True)
    prev, lo, hi = prever(y, X, ordem, futuro)

    # ---- L2: unidade -> categoria
    shares = shares_por_dia_semana(v, fim)
    cal_u = cal[cal["unidade"] == u["nome"]].set_index("data")
    previsao = []
    for i, data in enumerate(futuro):
        w = data.weekday()
        c = cal_u.loc[data]
        evento = c["nome_feriado"] if isinstance(c["nome_feriado"], str) else (
            c["data_comemorativa"] if isinstance(c["data_comemorativa"], str) else None)
        por_cat = {}
        for cat in CATEGORIAS:
            s = shares[cat["id"]][w]
            por_cat[cat["id"]] = {"previsto": r1(prev[i] * s), "inf": r1(lo[i] * s),
                                  "sup": r1(hi[i] * s)}
        s3 = sum(shares[cat["id"]][w] for cat in CATEGORIAS)
        previsao.append({
            "data": str(data.date()), "dia_semana": DIA_CURTO[w],
            "loja_fechada": bool(c["loja_fechada"]), "evento": evento,
            "previsto": r1(prev[i] * s3), "inf": r1(lo[i] * s3), "sup": r1(hi[i] * s3),
            "categorias": por_cat,
        })

    # ---- historico diario (8 semanas) e semanal (base inteira), so as 3 categorias
    painel = v[v["cat"] != CAT_FORA]
    diario_cat = painel.groupby(["emissao", "cat"])["qtdade"].sum().unstack(fill_value=0)
    diario_cat = diario_cat.reindex(idx, fill_value=0)
    ini8 = fim - pd.Timedelta(days=JANELA_SHARE_DIAS - 1)
    historico_diario = [
        {"data": str(d.date()), "dia_semana": DIA_CURTO[d.weekday()],
         "total": r1(row.sum()), "categorias": {c["id"]: r1(row.get(c["id"], 0)) for c in CATEGORIAS}}
        for d, row in diario_cat.loc[ini8:fim].iterrows()
    ]
    semanal = diario_cat.resample("W-SUN", label="left", closed="left").sum()
    semanal.index = semanal.index + pd.Timedelta(days=1)       # rotulo = segunda-feira
    historico_semanal = [
        {"semana": str(d.date()), "total": r1(row.sum()),
         "categorias": {c["id"]: r1(row.get(c["id"], 0)) for c in CATEGORIAS}}
        for d, row in semanal.iterrows()
    ]

    # ---- L2: categoria -> SKU
    prods_janela = painel[painel["emissao"] >= ini8]
    produtos = []
    for cat in CATEGORIAS:
        pc = prods_janela[prods_janela["cat"] == cat["id"]]
        tot_cat = float(pc["qtdade"].sum())
        ranking = pc.groupby("produto_cod")["qtdade"].sum().sort_values(ascending=False)
        detalhados = 0
        for cod, qtd8 in ranking.items():
            if detalhados == SKUS_POR_CATEGORIA or qtd8 <= 0:
                break
            hist = v[v["produto_cod"] == cod]
            dias_venda = int(hist["emissao"].nunique())
            n_vendas = int(hist["doc_numero"].nunique())
            # SKU com historico curto fica no rateio uniforme da categoria e nao ganha
            # previsao propria no painel (CLAUDE.md, L2 — fallback).
            if dias_venda < MIN_DIAS_COM_VENDA and n_vendas < MIN_VENDAS:
                continue
            detalhados += 1
            share = float(qtd8) / tot_cat
            nome = hist.sort_values("emissao")["produto_nome"].iloc[-1]
            sem = (hist[hist["emissao"] >= ini8].groupby("emissao")["qtdade"].sum()
                   .reindex(pd.date_range(ini8, fim), fill_value=0)
                   .resample("W-SUN", label="left", closed="left").sum())
            dias = [{"data": p["data"],
                     "previsto": round(p["categorias"][cat["id"]]["previsto"] * share, 1),
                     "inf": round(p["categorias"][cat["id"]]["inf"] * share, 1),
                     "sup": round(p["categorias"][cat["id"]]["sup"] * share, 1)}
                    for p in previsao]
            produtos.append({
                "codigo": cod, "nome": nome, "categoria": cat["id"],
                "subcategoria": hist["categoria_fina"].mode().iloc[0],
                "vendido_8_semanas": r1(qtd8),
                "vendido_total": r1(hist["qtdade"].sum()),
                "dias_com_venda": dias_venda, "vendas": n_vendas,
                "participacao_categoria": round(share, 4),
                "historico_semanal": [r1(x) for x in sem.values],
                "previsao_14d": r1(sum(d["previsto"] for d in dias)),
                "previsao": dias,
            })

    backtest = [{"data": str(r.data.date()), "previsto": r1(r.previsto), "inf": r1(r.ic_inf),
                 "sup": r1(r.ic_sup), "real": r1(r.real), "naive": r1(r.naive)}
                for r in bt.itertuples()]

    cat_totais = {c["id"]: r1(painel.loc[painel["cat"] == c["id"], "qtdade"].sum())
                  for c in CATEGORIAS}
    print(f"[{u['nome']}] pronto em {time.time() - t0:.0f}s", flush=True)
    return {
        **u,
        "periodo": {"inicio": str(ini.date()), "fim": str(fim.date()), "dias": len(idx)},
        "linhas": int(len(v)),
        "skus_vendidos": int(v["produto_cod"].nunique()),
        "volume_total": r1(painel["qtdade"].sum()),
        "volume_flores_de_corte": r1(v.loc[v["cat"] == CAT_FORA, "qtdade"].sum()),
        "volume_por_categoria": cat_totais,
        "skus_por_categoria": {c["id"]: int(painel.loc[painel["cat"] == c["id"], "produto_cod"].nunique())
                               for c in CATEGORIAS},
        "participacao_dia_semana": {c["id"]: [round(s, 4) for s in shares[c["id"]]] for c in CATEGORIAS},
        "modelo": {
            "ordem": list(ordem["order"]), "ordem_sazonal": list(ordem["seasonal_order"]),
            "aic": round(ordem["aic"], 1), "transformacao": "log1p",
            "exogenas": COLS_EXOG, "status": status_modelo(met), "metricas": met,
            "rodadas": rodadas,
        },
        "previsao": previsao,
        "historico_diario": historico_diario,
        "historico_semanal": historico_semanal,
        "produtos": produtos,
        "backtest": backtest,
    }


def amostra_registros(df: pd.DataFrame) -> list[dict]:
    """Ultimos 2 dias com venda de cada unidade — o cliente vira so o tipo (consumidor ou cadastrado)."""
    linhas = []
    for u in UNIDADES:
        v = df[df["unidade"] == u["nome"]]
        dias = sorted(v["emissao"].unique())[-2:]
        a = v[v["emissao"].isin(dias)].sort_values(["emissao", "doc_numero"])
        for r in a.itertuples():
            linhas.append({
                "data": str(pd.Timestamp(r.emissao).date()), "documento": r.doc_numero,
                "codigo": r.produto_cod, "produto": r.produto_nome, "unidade": u["id"],
                "categoria": r.cat, "quantidade": r1(r.qtdade), "valor": round(float(r.vl_total), 2),
                "tipo_cliente": "Consumidor" if str(r.cliente_nome).strip().upper() == "CONSUMIDOR" else "Cadastrado",
            })
    return linhas


def log_importacao() -> dict:
    with open(LOG_IMPORTACAO, encoding="utf-8") as fh:
        log = json.load(fh)["arquivos_processados"]
    with open(RELATORIO_PRE, encoding="utf-8") as fh:
        rel = json.load(fh)["etapas"]
    meses = {"jan": 1, "fev": 2, "mar": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
             "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
    arquivos = []
    for nome, info in log.items():
        mes, ano = nome.replace(".xlsx", "").split()
        arquivos.append({"arquivo": nome, "competencia": f"20{ano}-{meses[mes]:02d}",
                         "registros": info["registros_adicionados"],
                         "duplicatas": info["duplicatas_encontradas"],
                         "hash": info["hash"], "processado_em": info["processado_em"][:19]})
    arquivos.sort(key=lambda a: a["competencia"])
    t = rel["2_tratamento_de_dados02"]
    return {"arquivos": arquivos, "qualidade": {
        "linhas_lidas": t["linhas_lidas"],
        "linhas_removidas": sum(t["linhas_removidas"].values()),
        "clientes_sem_nome_corrigidos": t["clientes_sem_nome_corrigidos"],
        "duplicatas": rel["1_extrair_base01"]["duplicatas_ignoradas"],
    }}


def main():
    df = carregar_base()
    cal = carregar_calendario()
    prods = df.groupby("cat")["produto_cod"].nunique()
    unidades = [gerar_unidade(df, cal, u) for u in UNIDADES]
    saida = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "fonte": "training_scripts/output/BaseClassificada03.csv + calendario_diario.csv",
        "base": {
            "inicio": str(df["emissao"].min().date()), "fim": str(df["emissao"].max().date()),
            "linhas": int(len(df)), "skus": int(df["produto_cod"].nunique()),
            "skus_por_categoria": {c["id"]: int(prods.get(c["id"], 0)) for c in CATEGORIAS},
        },
        "configuracao": {"horizonte_dias": HORIZONTE, "m": M, "alpha_ic": ALPHA,
                         "janela_participacao_dias": JANELA_SHARE_DIAS,
                         "primeira_origem_validacao": str(PRIMEIRA_ORIGEM.date()),
                         "passo_origem_dias": PASSO_ORIGEM},
        "categorias": CATEGORIAS,
        "unidades": unidades,
        "registros_amostra": amostra_registros(df),
        "importacao": log_importacao(),
    }
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"[ok] {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
