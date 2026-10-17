"""Gera os dados que o frontend (app-react) usa enquanto a API nao esta conectada.

Nada aqui e inventado: todo numero sai da base real pre-processada (`output/`) e dos
modelos escolhidos na etapa de testes (branch `feat/desagregacao-l2`, e-mail ao orientador):

  * Encomendas: venda com mais de 2.000 un. no documento (ADR-013). Ficam FORA da
    previsao e aparecem a parte (historico e lista das ultimas).
  * Loja (L1): SARIMAX na venda SEM encomendas, SEM log1p, d = 1, m = 7, exogenas de
    calendario, janela DESLIZANTE do tamanho do treino da 1a origem (treino C deslizante).
  * Categoria (L2, desagregacao loja -> categoria): previsao da loja x participacao da
    categoria no mesmo dia da semana nas ultimas 8 semanas (participacao movel x perfil de
    dia da semana, CLAUDE.md L2). Testada nas mesmas rodadas da loja, com a participacao
    calculada so com as 8 semanas antes de cada origem.
  * Produto regular (ADI < 1,32 em dias de loja aberta e >= 180 dias de historico —
    Syntetos, Boylan & Croston, 2005): SARIMAX no proprio produto, d = 0 com constante,
    SEM log1p (sem vies, faixa calibrada no teste de ajuste). Ordem por AIC.
  * Demais produtos: so historico, sem previsao diaria (venda irregular).

Validacao (as duas lojas): walk-forward com 26 rodadas a cada 14 dias desde 2025-03-02,
h = 14; metricas nos dias de loja aberta.

Categorias: as 4 da coluna `categoria` da Etapa 3 (Grama, Plantas diversas — todas as
plantas exceto flores de corte —, Produtos de jardim — substrato, adubo, vaso, insumo — e
Flores de corte, ~1,8% do volume).

Uso (a partir de `ia-predictor/`, depois do pre-processamento):
    python -m training_scripts.frontend_mock.gerar_dados_frontend
"""
from __future__ import annotations

import itertools
import json
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import time  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: E402

from training_scripts.preprocessing.remove_encomendas_06 import (  # noqa: E402
    LIMIAR_QTD_VENDA, marcar_encomendas,
)

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

M = 7
GRID_PQ, GRID_SPQ = range(0, 3), range(0, 2)
ALPHA = 0.05
MAXITER = 200
HORIZONTE = 14
PRIMEIRA_ORIGEM = pd.Timestamp("2025-03-02")
PASSO_ORIGEM = 14
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CALENDARIO = ["loja_fechada", "abertura_excepcional"]
COLS_EXOG = [f"dia_{d}" for d in DIAS] + COLS_CALENDARIO

D_LOJA = 1                 # loja: acompanha o nivel recente (doc 04)
D_PRODUTO = 0              # produto: volta a media (teste de ajuste)
JANELA_SHARE_DIAS = 56     # participacao movel da categoria: ultimas 8 semanas
ADI_CORTE = 1.32           # Syntetos, Boylan & Croston (2005)
MIN_SPAN_DIAS = 180        # MIN_OBSERVATIONS_DAYS do L1
IRREGULARES_POR_CATEGORIA = 8

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
    {"id": "produtos-de-jardim", "nome": "Produtos de jardim", "grupo": "Produtos de jardim",
     "descricao": "Substratos, adubos, vasos, ferramentas e demais insumos de jardinagem"},
    {"id": "flores-de-corte", "nome": "Flores de corte", "grupo": "Flores de corte",
     "descricao": "Flores de corte (rosas, girassóis, crisântemos…)"},
]
# `grupo` = rotulo da coluna `categoria` da BaseClassificada03 (nome mantido no JSON do front)
CAT_POR_GRUPO = {c["grupo"]: c["id"] for c in CATEGORIAS}
CAT_FORA = "outros"        # grupo sem categoria (nao ocorre depois de tirar servicos e taxas)
IDS_CAT = [c["id"] for c in CATEGORIAS]
DIA_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def r1(v) -> float:
    return round(float(v), 1)


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
def carregar_base() -> pd.DataFrame:
    cols = ["doc_numero", "emissao", "cliente_nome", "produto_cod", "produto_nome", "qtdade",
            "vl_total", "unidade", "categoria", "categoria_fina"]
    df = pd.read_csv(BASE, sep=";", usecols=cols, dtype={"produto_cod": str, "doc_numero": str,
                                                         "cliente_nome": str})
    df = df[df["categoria"] != "Servico e taxa"].copy()
    df["emissao"] = pd.to_datetime(df["emissao"])
    df["cat"] = df["categoria"].map(CAT_POR_GRUPO).fillna(CAT_FORA)
    df["encomenda"] = marcar_encomendas(df, LIMIAR_QTD_VENDA)
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
# SARIMAX
# --------------------------------------------------------------------------- #
def ajustar(z, X, order, sorder):
    return SARIMAX(z, exog=X, order=order, seasonal_order=sorder,
                   trend="c" if order[1] == 0 else "n",
                   enforce_stationarity=False, enforce_invertibility=False
                   ).fit(disp=False, maxiter=MAXITER)


def selecionar_ordem(y: pd.Series, X: pd.DataFrame, d: int) -> dict | None:
    melhor = None
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        try:
            res = ajustar(y, X.loc[y.index], (p, d, q), (P, 0, Q, M))
        except Exception:  # noqa: BLE001
            continue
        if np.isfinite(res.aic) and (melhor is None or res.aic < melhor["aic"]):
            melhor = {"order": (p, d, q), "seasonal_order": (P, 0, Q, M), "aic": float(res.aic)}
    return melhor


def prever(y, X, ordem, futuro):
    res = ajustar(y, X.loc[y.index], ordem["order"], ordem["seasonal_order"])
    fc = res.get_forecast(len(futuro), exog=X.loc[futuro])
    mu, ic = np.asarray(fc.predicted_mean), np.asarray(fc.conf_int(alpha=ALPHA))
    return np.clip(mu, 0, None), np.clip(ic[:, 0], 0, None), np.clip(ic[:, 1], 0, None)


def metricas(linhas: list[dict], fechados: set) -> dict:
    d = pd.DataFrame(linhas)
    d = d[~d["data"].isin(fechados)]
    ae = (d["real"] - d["previsto"]).abs()
    ae_n = (d["real"] - d["naive"]).abs()
    ok = d["escala"] > 0
    q = d.assign(ae=ae, ae_n=ae_n).groupby("origem").agg(
        prev=("previsto", "sum"), real=("real", "sum"), ae=("ae", "sum"), ae_n=("ae_n", "sum"))
    cob = float(((d["real"] >= d["inf"]) & (d["real"] <= d["sup"])).mean() * 100)
    mase = float((ae[ok] / d.loc[ok, "escala"]).mean())
    return {
        "rodadas": int(d["origem"].nunique()),
        "rodadas_vence_naive": int((q["ae"] < q["ae_n"]).sum()),
        "dias_avaliados": int(len(d)),
        "mae": r1(ae.mean()),
        "mase": round(mase, 3),
        "erro_relativo_naive": round(float(ae.sum() / ae_n.sum()), 3) if ae_n.sum() else None,
        "cobertura_ic95_pct": r1(cob),
        "largura_ic95": r1((d["sup"] - d["inf"]).mean()),
        "venda_media_dia": r1(d["real"].mean()),
        "previsto_sobre_real_pct": r1(d["previsto"].sum() / d["real"].sum() * 100) if d["real"].sum() else None,
        "erro_total_14d_pct": r1((q["prev"] - q["real"]).abs().sum() / q["real"].sum() * 100) if q["real"].sum() else None,
    }


def status(m: dict) -> str:
    return "trained" if m["mase"] < 1.0 and 90 <= m["cobertura_ic95_pct"] <= 98 else "low_confidence"


def linhas_rodada(origem, futuro, real, prev, lo, hi, treino):
    ult7 = treino.values[-M:]
    naive = np.array([ult7[i % M] for i in range(HORIZONTE)])
    escala = float(np.mean(np.abs(treino.values[M:] - treino.values[:-M])))
    return [{"origem": origem, "data": futuro[h], "previsto": prev[h], "inf": lo[h], "sup": hi[h],
             "real": real[h], "naive": naive[h], "escala": escala} for h in range(HORIZONTE)]


# --------------------------------------------------------------------------- #
# Produtos regulares
# --------------------------------------------------------------------------- #
def regulares_na_origem(matriz: pd.DataFrame, aberta: pd.Series, origem: pd.Timestamp) -> set:
    """ADI < 1,32 (dias de loja aberta, da 1a venda ate a vespera) e span >= 180 dias."""
    treino = matriz[matriz.index < origem]
    vendeu = treino > 0
    dias = vendeu.sum()
    tem = dias >= 2
    if not tem.any():
        return set()
    primeira = vendeu.idxmax()[tem]
    span = ((origem - pd.Timedelta(days=1)) - primeira).dt.days + 1
    acum = aberta[aberta.index < origem].cumsum()
    abertos = acum.iloc[-1] - acum.reindex(primeira.values).values + aberta.reindex(primeira.values).values
    adi = pd.Series(abertos, index=primeira.index) / dias[tem]
    ok = (adi < ADI_CORTE) & (span >= MIN_SPAN_DIAS)
    return set(ok[ok].index)


_G: dict = {}


def _init(matriz, X, fechados):
    _G.update(m=matriz, X=X, fech=fechados)


def _serie(sku, ate):
    s = _G["m"][sku]
    s = s[s.index < ate]
    return s[s.index >= s[s > 0].index.min()]


def _modelo_produto(args):
    """Ordem por AIC, validacao (rodadas em que o SKU e regular) e previsao final."""
    sku, origens_sku, fim = args
    X, m = _G["X"], _G["m"]
    corte = origens_sku[0] if origens_sku else fim + pd.Timedelta(days=1)
    ordem = selecionar_ordem(_serie(sku, corte), X, D_PRODUTO)
    if ordem is None:
        return sku, None
    linhas = []
    for o in origens_sku:
        s = _serie(sku, o)
        fut = pd.date_range(o, periods=HORIZONTE, freq="D")
        try:
            p, lo, hi = prever(s, X, ordem, fut)
        except Exception:  # noqa: BLE001
            continue
        linhas += linhas_rodada(o, fut, m.loc[fut, sku].values, p, lo, hi, s)
    futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=HORIZONTE, freq="D")
    p, lo, hi = prever(_serie(sku, futuro[0]), X, ordem, futuro)
    met = metricas(linhas, _G["fech"]) if linhas else None
    return sku, {
        "ordem": list(ordem["order"]), "ordem_sazonal": list(ordem["seasonal_order"]),
        "metricas": met, "status": status(met) if met else "insufficient_data",
        "previsao": [{"data": str(futuro[i].date()), "previsto": r1(p[i]), "inf": r1(lo[i]),
                      "sup": r1(hi[i])} for i in range(HORIZONTE)],
        # Teste dia a dia (rodadas de 14 dias sem sobreposicao) para o historico da tela
        "backtest": [{"data": str(r["data"].date()), "previsto": r1(r["previsto"]), "inf": r1(r["inf"]),
                      "sup": r1(r["sup"]), "real": r1(r["real"]), "naive": r1(r["naive"])} for r in linhas],
    }


# --------------------------------------------------------------------------- #
# Montagem por unidade
# --------------------------------------------------------------------------- #
def shares_por_dia_semana(fluxo: pd.DataFrame, fim: pd.Timestamp) -> dict[str, list[float]]:
    ini = fim - pd.Timedelta(days=JANELA_SHARE_DIAS - 1)
    j = fluxo[(fluxo["emissao"] >= ini) & (fluxo["emissao"] <= fim)]
    tab = j.groupby([j["emissao"].dt.weekday, "cat"])["qtdade"].sum().unstack(fill_value=0)
    geral = j.groupby("cat")["qtdade"].sum()
    geral = geral / geral.sum()
    out = {c: [] for c in IDS_CAT + [CAT_FORA]}
    for w in range(7):
        linha = tab.loc[w] if w in tab.index else None
        tot = float(linha.sum()) if linha is not None else 0.0
        for c in out:
            out[c].append(float(linha.get(c, 0.0)) / tot if tot > 0 else float(geral.get(c, 0.0)))
    return out


def gerar_unidade(df: pd.DataFrame, cal: pd.DataFrame, u: dict, workers: int) -> dict:
    t0 = time.time()
    v = df[df["unidade"] == u["nome"]]
    fluxo = v[~v["encomenda"]]
    enc = v[v["encomenda"]]
    ini, fim = v["emissao"].min(), v["emissao"].max()
    idx = pd.date_range(ini, fim, freq="D")
    futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=HORIZONTE, freq="D")
    X = exogenas(cal, u["nome"], idx.append(futuro))
    cal_u = cal[cal["unidade"] == u["nome"]].set_index("data")
    fechados = set(cal_u.index[cal_u["loja_fechada"] == 1])
    aberta = (X.loc[idx, "loja_fechada"] == 0).astype(int)
    origens = list(pd.date_range(PRIMEIRA_ORIGEM, fim - pd.Timedelta(days=HORIZONTE - 1),
                                 freq=f"{PASSO_ORIGEM}D"))

    # ---- Loja: fluxo sem encomendas, sem log1p, janela deslizante
    y = fluxo.groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    janela = int((idx < PRIMEIRA_ORIGEM).sum())
    pre = y[y.index < PRIMEIRA_ORIGEM]
    ordem = selecionar_ordem(pre, X, D_LOJA)
    linhas = []
    for o in origens:
        treino = y[y.index < o].iloc[-janela:]
        fut = pd.date_range(o, periods=HORIZONTE, freq="D")
        p, lo, hi = prever(treino, X, ordem, fut)
        linhas += linhas_rodada(o, fut, y.loc[fut].values, p, lo, hi, treino)
    met = metricas(linhas, fechados)
    bt = pd.DataFrame(linhas)
    rodadas = [{"origem": str(o.date()), "erro_modelo": r1(g.loc[~g.data.isin(fechados), "previsto"].sub(g.real).abs().sum()),
                "erro_naive": r1(g.loc[~g.data.isin(fechados), "naive"].sub(g.real).abs().sum())}
               for o, g in bt.groupby("origem")]
    prev, lo, hi = prever(y.iloc[-janela:], X, ordem, futuro)

    # ---- Desagregacao loja -> categoria, testada nas mesmas rodadas
    cat_dia = (fluxo.groupby(["emissao", "cat"])["qtdade"].sum().unstack(fill_value=0.0)
               .reindex(index=idx, columns=IDS_CAT, fill_value=0.0))
    desagregacao = {}
    for k in IDS_CAT:
        linhas_k = []
        for o, g in bt.groupby("origem"):
            sh = shares_por_dia_semana(fluxo, o - pd.Timedelta(days=1))[k]
            fut = pd.DatetimeIndex(g["data"])
            f = np.array([sh[d.weekday()] for d in fut])
            treino_k = cat_dia.loc[cat_dia.index < o, k].iloc[-janela:]
            linhas_k += linhas_rodada(o, fut, cat_dia.loc[fut, k].values, g["previsto"].values * f,
                                      g["inf"].values * f, g["sup"].values * f, treino_k)
        met_k = metricas(linhas_k, fechados)
        desagregacao[k] = {
            "metricas": met_k, "status": status(met_k),
            "backtest": [{"data": str(r["data"].date()), "previsto": r1(r["previsto"]), "inf": r1(r["inf"]),
                          "sup": r1(r["sup"]), "real": r1(r["real"]), "naive": r1(r["naive"])} for r in linhas_k],
        }
    print(f"[{u['nome']}] desagregacao · " + " · ".join(
        f"{k}: acerto 14d {100 - (desagregacao[k]['metricas']['erro_total_14d_pct'] or 0):.0f}%, "
        f"faixa {desagregacao[k]['metricas']['cobertura_ic95_pct']}%" for k in IDS_CAT), flush=True)
    print(f"[{u['nome']}] loja {ordem['order']}{ordem['seasonal_order']} · janela {janela} d · "
          f"MASE {met['mase']} · IC95 {met['cobertura_ic95_pct']}% · {time.time() - t0:.0f}s", flush=True)

    # ---- Categoria: participacao na previsao da loja
    shares = shares_por_dia_semana(fluxo, fim)
    previsao = []
    for i, data in enumerate(futuro):
        w = data.weekday()
        c = cal_u.loc[data]
        evento = c["nome_feriado"] if isinstance(c["nome_feriado"], str) else (
            c["data_comemorativa"] if isinstance(c["data_comemorativa"], str) else None)
        cats = {k: {"previsto": r1(prev[i] * shares[k][w]), "inf": r1(lo[i] * shares[k][w]),
                    "sup": r1(hi[i] * shares[k][w])} for k in IDS_CAT}
        s3 = sum(shares[k][w] for k in IDS_CAT)
        previsao.append({"data": str(data.date()), "dia_semana": DIA_CURTO[w],
                         "loja_fechada": bool(c["loja_fechada"]), "evento": evento,
                         "previsto": r1(prev[i] * s3), "inf": r1(lo[i] * s3), "sup": r1(hi[i] * s3),
                         "categorias": cats})

    # ---- Historico (fluxo por categoria + encomendas a parte)
    painel = fluxo[fluxo["cat"] != CAT_FORA]
    diario = painel.groupby(["emissao", "cat"])["qtdade"].sum().unstack(fill_value=0).reindex(idx, fill_value=0)
    enc_dia = enc[enc["cat"] != CAT_FORA].groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    ini8 = fim - pd.Timedelta(days=JANELA_SHARE_DIAS - 1)
    historico_diario = [
        {"data": str(d.date()), "dia_semana": DIA_CURTO[d.weekday()], "total": r1(row.sum()),
         "encomendas": r1(enc_dia.loc[d]),
         "categorias": {k: r1(row.get(k, 0)) for k in IDS_CAT}}
        for d, row in diario.loc[ini8:fim].iterrows()]
    sem = diario.resample("W-SUN", label="left", closed="left").sum()
    sem_enc = enc_dia.resample("W-SUN", label="left", closed="left").sum()
    historico_semanal = [
        {"semana": str((d + pd.Timedelta(days=1)).date()), "total": r1(row.sum()),
         "encomendas": r1(sem_enc.loc[d]), "categorias": {k: r1(row.get(k, 0)) for k in IDS_CAT}}
        for d, row in sem.iterrows()]

    # ---- Produtos: regulares (modelo proprio) + principais irregulares (so historico)
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    cat_sku = fluxo.groupby("produto_cod")["cat"].agg(lambda x: x.mode().iloc[0])
    reg_por_origem = {o: regulares_na_origem(matriz, aberta, o) for o in origens}
    regulares_fim = regulares_na_origem(matriz, aberta, fim + pd.Timedelta(days=1))
    regulares = sorted(s for s in regulares_fim if cat_sku.get(s) in IDS_CAT)
    flores_regulares = sorted(s for s in regulares_fim if cat_sku.get(s) == CAT_FORA)
    tarefas = [(s, [o for o in origens if s in reg_por_origem[o]], fim) for s in regulares]
    with ProcessPoolExecutor(workers, initializer=_init,
                             initargs=(matriz[regulares], X, fechados)) as ex:
        modelos = dict(ex.map(_modelo_produto, tarefas))
    print(f"[{u['nome']}] {len(regulares)} produtos regulares modelados "
          f"(+{len(flores_regulares)} de flores de corte fora do painel) · {time.time() - t0:.0f}s", flush=True)

    j8 = painel[painel["emissao"] >= ini8]
    vend8 = j8.groupby("produto_cod")["qtdade"].sum()
    irregulares = []
    for k in IDS_CAT:
        cand = vend8[[s for s in vend8.index if cat_sku.get(s) == k and s not in regulares_fim]]
        irregulares += list(cand.sort_values(ascending=False).head(IRREGULARES_POR_CATEGORIA).index)

    total_aberto_por_sku = {}
    produtos = []
    for s in regulares + irregulares:
        hist = v[v["produto_cod"] == s]
        hf = fluxo[fluxo["produto_cod"] == s]
        d = matriz[s] if s in matriz else pd.Series(0.0, index=idx)
        d = d[d.index >= d[d > 0].index.min()] if (d > 0).any() else d
        aberto = d[~d.index.isin(fechados)]
        sem8 = (d.reindex(pd.date_range(ini8, fim), fill_value=0)
                .resample("W-SUN", label="left", closed="left").sum())
        mod = modelos.get(s) if s in regulares else None
        produtos.append({
            "codigo": s, "nome": hist.sort_values("emissao")["produto_nome"].iloc[-1],
            "categoria": cat_sku[s], "subcategoria": hist["categoria_fina"].mode().iloc[0],
            "regular": s in regulares,
            "dias_com_venda": int((d > 0).sum()),
            "pct_dias_abertos_com_venda": r1((aberto > 0).mean() * 100) if len(aberto) else 0.0,
            "media_dia_aberto": r1(aberto.mean()) if len(aberto) else 0.0,
            "vendido_8_semanas": r1(vend8.get(s, 0.0)),
            "vendido_total": r1(hf["qtdade"].sum()),
            "vendido_em_encomendas": r1(hist.loc[hist["encomenda"], "qtdade"].sum()),
            "historico_semanal": [r1(x) for x in sem8.values],
            # Venda diaria (sem encomendas) dos ultimos 28 dias, para o grafico da previsao
            "historico_diario": [{"data": str(dt.date()), "vendido": r1(x)} for dt, x in
                                 (matriz[s] if s in matriz else pd.Series(0.0, index=idx))
                                 .loc[fim - pd.Timedelta(days=27):fim].items()],
            "modelo": None if mod is None else {k: mod[k] for k in ("ordem", "ordem_sazonal", "metricas", "status")},
            "previsao": [] if mod is None else mod["previsao"],
            "previsao_14d": r1(sum(x["previsto"] for x in mod["previsao"])) if mod else None,
            "backtest": [] if mod is None else mod["backtest"],
        })

    # ---- Encomendas: resumo e ultimas
    docs = (enc.groupby(["emissao", "doc_numero"])
            .apply(lambda g: pd.Series({"volume": g["qtdade"].sum(),
                                        "produtos": list(g.groupby("produto_nome")["qtdade"].sum()
                                                         .sort_values(ascending=False).head(3).index)}))
            .reset_index().sort_values("emissao"))
    encomendas = {
        "vendas": int(len(docs)), "dias": int(enc["emissao"].nunique()),
        "volume": r1(enc["qtdade"].sum()),
        "pct_volume": r1(enc["qtdade"].sum() / v["qtdade"].sum() * 100),
        "ultimas": [{"data": str(r.emissao.date()), "volume": r1(r.volume), "produtos": r.produtos}
                    for r in docs.tail(12).iloc[::-1].itertuples()],
    }

    return {
        **u,
        "periodo": {"inicio": str(ini.date()), "fim": str(fim.date()), "dias": len(idx)},
        "linhas": int(len(v)), "skus_vendidos": int(v["produto_cod"].nunique()),
        "volume_total": r1(painel["qtdade"].sum()),
        "volume_flores_de_corte": r1(fluxo.loc[fluxo["cat"] == "flores-de-corte", "qtdade"].sum()),
        "volume_por_categoria": {k: r1(painel.loc[painel["cat"] == k, "qtdade"].sum()) for k in IDS_CAT},
        "skus_por_categoria": {k: int(painel.loc[painel["cat"] == k, "produto_cod"].nunique()) for k in IDS_CAT},
        "regulares_por_categoria": {k: sum(1 for s in regulares if cat_sku[s] == k) for k in IDS_CAT},
        "volume_regulares_8_semanas_pct": {
            k: r1(sum(vend8.get(s, 0) for s in regulares if cat_sku[s] == k)
                  / max(1.0, float(j8.loc[j8["cat"] == k, "qtdade"].sum())) * 100) for k in IDS_CAT},
        "flores_regulares_fora_do_painel": len(flores_regulares),
        "encomendas": encomendas,
        "modelo": {"ordem": list(ordem["order"]), "ordem_sazonal": list(ordem["seasonal_order"]),
                   "aic": round(ordem["aic"], 1), "transformacao": "nenhuma",
                   "janela": "deslizante", "janela_dias": janela,
                   "base": f"sem encomendas (venda > {LIMIAR_QTD_VENDA} un. na nota)",
                   "exogenas": COLS_EXOG, "status": status(met), "metricas": met, "rodadas": rodadas},
        "desagregacao": desagregacao,
        "previsao": previsao,
        "historico_diario": historico_diario,
        "historico_semanal": historico_semanal,
        "produtos": produtos,
        "backtest": [{"data": str(r.data.date()), "previsto": r1(r.previsto), "inf": r1(r.inf),
                      "sup": r1(r.sup), "real": r1(r.real), "naive": r1(r.naive)}
                     for r in bt.drop_duplicates("data", keep="last").itertuples()],
    }


def amostra_registros(df: pd.DataFrame) -> list[dict]:
    """Ultimos 2 dias com venda de cada unidade — o cliente vira so o tipo."""
    linhas = []
    for u in UNIDADES:
        v = df[df["unidade"] == u["nome"]]
        dias = sorted(v["emissao"].unique())[-2:]
        for r in v[v["emissao"].isin(dias)].sort_values(["emissao", "doc_numero"]).itertuples():
            linhas.append({
                "data": str(pd.Timestamp(r.emissao).date()), "documento": r.doc_numero,
                "codigo": r.produto_cod, "produto": r.produto_nome, "unidade": u["id"],
                "categoria": r.cat, "quantidade": r1(r.qtdade), "valor": round(float(r.vl_total), 2),
                "tipo_cliente": "Consumidor" if str(r.cliente_nome).strip().upper() == "CONSUMIDOR" else "Cadastrado",
                "encomenda": bool(r.encomenda),
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
        # soma do log de importacao: o resumo da etapa 1 so traz o total quando ha planilha nova
        "duplicatas": sum(a["duplicatas"] for a in arquivos),
    }}


def gerar_painel(workers: int = 8) -> dict:
    """Treina os modelos e monta o painel (sem o bloco `importacao`).

    Usado por `main()` (JSON do frontend) e pelo backend (`backend/jobs`), que grava o
    resultado no banco.
    """
    df = carregar_base()
    cal = carregar_calendario()
    prods = df.groupby("cat")["produto_cod"].nunique()
    unidades = [gerar_unidade(df, cal, u, workers) for u in UNIDADES]
    return {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "fonte": "training_scripts/output/BaseClassificada03.csv + calendario_diario.csv",
        "base": {
            "inicio": str(df["emissao"].min().date()), "fim": str(df["emissao"].max().date()),
            "linhas": int(len(df)), "skus": int(df["produto_cod"].nunique()),
            "skus_por_categoria": {k: int(prods.get(k, 0)) for k in IDS_CAT},
        },
        "configuracao": {
            "horizonte_dias": HORIZONTE, "m": M, "alpha_ic": ALPHA,
            "janela_participacao_dias": JANELA_SHARE_DIAS,
            "primeira_origem_validacao": str(PRIMEIRA_ORIGEM.date()), "passo_origem_dias": PASSO_ORIGEM,
            "limiar_encomenda_un": LIMIAR_QTD_VENDA,
            "criterio_regular": {"adi_corte": ADI_CORTE, "min_span_dias": MIN_SPAN_DIAS,
                                 "fonte": "Syntetos, Boylan & Croston (2005)"},
            "modelo_loja": "SARIMAX, base sem encomendas, sem log1p, d = 1, janela deslizante",
            "modelo_produto": "SARIMAX por produto regular, base sem encomendas, sem log1p, d = 0",
        },
        "categorias": CATEGORIAS,
        "unidades": unidades,
        "registros_amostra": amostra_registros(df),
    }


def main(workers: int = 8):
    saida = {**gerar_painel(workers), "importacao": log_importacao()}
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"[ok] {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
