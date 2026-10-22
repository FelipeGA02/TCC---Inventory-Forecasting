"""Previsao diaria por categoria: desagregar o L1 da loja x SARIMAX direto em cada categoria.

Pergunta
--------
Para as 4 series `unidade x categoria` (Grama, Plantas diversas, Produtos de jardim, Flores
de corte), vale mais repartir a previsao da loja (L1) pela participacao da categoria — o
que o app faz hoje — ou ajustar um SARIMAX proprio em cada categoria?

Metodos comparados (mesma origem, mesmos 14 dias, mesma janela de treino)
--------------------------------------------------------------------------
  * `direto`         — SARIMAX na serie da categoria. Mesma receita do L1 da loja: fluxo
    diario, sem log1p, d = 1, m = 7, 6 dummies de dia da semana + `loja_fechada` +
    `abertura_excepcional`. Ordem por AIC no grid do L1, uma vez por serie, so com dados
    anteriores a 1a origem.
  * `desag_8sem_dds` — previsao L1 da loja x participacao da categoria NO MESMO DIA DA
    SEMANA nas ultimas 8 semanas (participacao movel x perfil de dia da semana, CLAUDE.md
    L2; e o metodo de `frontend_mock/gerar_dados_frontend.py`).
  * `desag_8sem`     — previsao L1 x participacao da categoria nas ultimas 8 semanas, sem
    perfil de dia da semana ("proportions of historical averages" numa janela movel, Gross
    & Sohl, 1990).
  * `naive`          — regua: repete os ultimos 7 dias da categoria.

Na desagregacao, a faixa de 95% e a do L1 multiplicada pela participacao (como no app).

Protocolo
---------
Walk-forward com janela DESLIZANTE: em cada origem o modelo e reajustado so com os ultimos
`janela` dias antes dela, onde `janela` = tamanho do treino na 1a origem (425 dias, como em
`baseline/treino_itabirito_janela_deslizante.py`). A origem anda 1 dia e cada ajuste preve
os 14 dias seguintes, de 2025-03-02 ate a ultima origem com 14 dias de realizado (351
origens). Toda participacao, ordem e escala do MASE usa so dados anteriores a origem.

Metricas nos dias de loja aberta (domingo/feriado com venda 0 inflam acerto sem dizer nada
da previsao). Alem do MASE, o erro relativo a naive (razao das somas), as rodadas em que o
metodo vence a naive, a cobertura e a largura do IC 95% (CLAUDE.md, "Comparacao entre
experimentos").

Significancia: teste de Diebold & Mariano (1995) com a correcao de amostra pequena de
Harvey, Leybourne & Newbold (1997), perda = erro absoluto, em duas series de perdas:
(1) h = 1, um erro por dia; (2) erro absoluto da soma dos 14 dias por origem (janelas
sobrepostas: autocorrelacao ate a defasagem 13, tratada com h = 14 no teste).

Extra: a soma das 4 previsoes diretas (bottom-up) contra o L1, na venda total da loja.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.categoria_direta_vs_desagregacao
    python -m training_scripts.disaggregation.categoria_direta_vs_desagregacao --unidade itabirito
    python -m training_scripts.disaggregation.categoria_direta_vs_desagregacao --so-metricas
"""
from __future__ import annotations

import argparse
import json
import os

# Um thread de BLAS por processo: os ajustes ja rodam em paralelo.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import time  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from training_scripts.baseline.sarimax_itabirito_core import (  # noqa: E402
    ALPHA, HORIZONTE, M, METRICS_DIR, PRIMEIRA_ORIGEM, ajustar, selecionar_ordem,
)
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (  # noqa: E402
    UNIDADES, carregar_fluxo, exogenas, fechados_da_unidade,
)

warnings.filterwarnings("ignore")

CATEGORIAS = ["Grama", "Plantas diversas", "Produtos de jardim", "Flores de corte"]
JANELA_SHARE_DIAS = 56     # participacao movel do L2: ultimas 8 semanas (CLAUDE.md)
PASSO_ORIGEM = 1           # janelas sobrepostas: a origem anda 1 dia
LOJA = "__loja__"
METODOS = ["direto", "desag_8sem_dds", "desag_8sem"]
REFERENCIA = "desag_8sem_dds"   # metodo em uso no app


# --------------------------------------------------------------------------- #
# Ajustes (rodam em processos separados)
# --------------------------------------------------------------------------- #
_G: dict = {}


def _init(series: pd.DataFrame, X: pd.DataFrame, janela: int):
    _G.update(s=series, X=X, janela=janela)


def _ordem(nome: str):
    s = _G["s"][nome]
    pre = s[s.index < PRIMEIRA_ORIGEM]
    return nome, selecionar_ordem(pre, _G["X"].loc[pre.index])


def _lote(args) -> list[dict]:
    """Walk-forward de uma serie num bloco de origens."""
    nome, ordem, origens = args
    s, X, janela = _G["s"][nome], _G["X"], _G["janela"]
    linhas = []
    for o in origens:
        treino = s[s.index < o].iloc[-janela:]
        fut = pd.date_range(o, periods=HORIZONTE, freq="D")
        try:
            res = ajustar(treino, X.loc[treino.index], ordem["order"], ordem["seasonal_order"])
            fc = res.get_forecast(HORIZONTE, exog=X.loc[fut])
        except Exception:  # noqa: BLE001 — origem que nao converge
            continue
        mu = np.clip(np.asarray(fc.predicted_mean), 0, None)
        ic = np.clip(np.asarray(fc.conf_int(alpha=ALPHA)), 0, None)
        for h in range(HORIZONTE):
            linhas.append({"serie": nome, "origem": o, "data": fut[h], "horizonte": h + 1,
                           "previsto": mu[h], "ic_inf": ic[h, 0], "ic_sup": ic[h, 1]})
    return linhas


# --------------------------------------------------------------------------- #
# Desagregacao
# --------------------------------------------------------------------------- #
def participacoes(cat: pd.DataFrame, origem: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    """Participacao das categorias nas 8 semanas antes da origem: por dia da semana (7 x 4)
    e plana (4). Dia da semana sem venda na janela (domingo) recebe a participacao plana."""
    j = cat[(cat.index < origem)].iloc[-JANELA_SHARE_DIAS:]
    plana = j.sum() / j.sum().sum()
    por_dia = j.groupby(j.index.weekday).sum()
    tot = por_dia.sum(axis=1)
    dds = por_dia.div(tot.where(tot > 0), axis=0)
    dds = dds.reindex(range(7)).apply(lambda r: r.fillna(plana[r.name]))
    return dds, plana


def desagregar(prev_loja: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    partes = []
    for o, g in prev_loja.groupby("origem"):
        dds, plana = participacoes(cat, o)
        wd = g["data"].dt.weekday.values
        for c in CATEGORIAS:
            for met, f in (("desag_8sem_dds", dds[c].values[wd]), ("desag_8sem", plana[c])):
                partes.append(g.assign(serie=c, metodo=met, previsto=g["previsto"] * f,
                                       ic_inf=g["ic_inf"] * f, ic_sup=g["ic_sup"] * f))
    return pd.concat(partes, ignore_index=True)


def anexar_real_e_naive(prev: pd.DataFrame, series: pd.DataFrame, janela: int) -> pd.DataFrame:
    """Real, naive sazonal e escala do MASE de cada (serie, origem) — da janela de treino."""
    ref = {}
    for nome in prev["serie"].unique():
        s = series[nome]
        for o in prev.loc[prev["serie"] == nome, "origem"].unique():
            tr = s[s.index < o].iloc[-janela:].values
            ref[(nome, o)] = (tr[-M:], float(np.mean(np.abs(tr[M:] - tr[:-M]))))
    chave = list(zip(prev["serie"], prev["origem"]))
    prev = prev.copy()
    prev["naive"] = [ref[k][0][(h - 1) % M] for k, h in zip(chave, prev["horizonte"])]
    prev["escala"] = [ref[k][1] for k in chave]
    prev["real"] = [series.at[d, n] for n, d in zip(prev["serie"], prev["data"])]
    return prev


# --------------------------------------------------------------------------- #
# Metricas
# --------------------------------------------------------------------------- #
def _bloco(d: pd.DataFrame) -> dict:
    ae = (d["real"] - d["previsto"]).abs()
    ae_n = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    ok = d["escala"] > 0
    q = d.assign(ae=ae, ae_n=ae_n).groupby("origem").agg(
        prev=("previsto", "sum"), real=("real", "sum"), ae=("ae", "sum"), ae_n=("ae_n", "sum"))
    cob = float(dentro.mean() * 100)
    mase = float((ae[ok] / d.loc[ok, "escala"]).mean())
    return {
        "n_dias": int(len(d)), "n_origens": int(len(q)),
        "venda_media_dia": round(float(d["real"].mean()), 1),
        "mae": round(float(ae.mean()), 2),
        "mase": round(mase, 3),
        "erro_relativo_naive": round(float(ae.sum() / ae_n.sum()), 3) if ae_n.sum() else None,
        "vence_naive_pct": round(float((q["ae"] < q["ae_n"]).mean() * 100), 1),
        "cobertura_ic95_pct": round(cob, 1),
        "largura_ic95": round(float((d["ic_sup"] - d["ic_inf"]).mean()), 1),
        "previsto_sobre_real_pct": round(float(d["previsto"].sum() / d["real"].sum() * 100), 1),
        "erro_total_14d_pct": round(float((q["prev"] - q["real"]).abs().sum() / q["real"].sum() * 100), 1),
        "passa_criterio_diario": bool(mase < 1.0 and 90.0 <= cob <= 98.0),
    }


def diebold_mariano(perda_a: np.ndarray, perda_b: np.ndarray, h: int) -> dict:
    """DM com correcao HLN (1997). d = perda_a - perda_b; estatistica < 0 => A melhor."""
    d = np.asarray(perda_a) - np.asarray(perda_b)
    n = len(d)
    dc = d - d.mean()
    gamma = [np.dot(dc[k:], dc[:n - k]) / n for k in range(min(h, n))]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        var = gamma[0] / n                     # fallback se a soma ficar nao positiva
    dm = d.mean() / np.sqrt(var)
    hln = dm * np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    p = 2 * stats.t.sf(abs(hln), df=n - 1)
    return {"n": int(n), "dif_media_perda": round(float(d.mean()), 3),
            "estatistica_hln": round(float(hln), 3), "p_valor": round(float(p), 4)}


def comparar(prev: pd.DataFrame, fechados: set) -> dict:
    """Metricas por (categoria, metodo) e DM de cada metodo contra a referencia."""
    out = {}
    aberto = ~prev["data"].isin(fechados)
    for c in CATEGORIAS + [LOJA]:
        dc = prev[prev["serie"] == c]
        out[c] = {"metodos": {}, "diebold_mariano_vs_" + REFERENCIA: {}}
        for met, d in dc.groupby("metodo"):
            da = d[aberto.loc[d.index]]
            out[c]["metodos"][met] = {
                "dias_abertos_h1_14": _bloco(da),
                "dias_abertos_h1": _bloco(da[da["horizonte"] == 1]),
                "dias_abertos_h14": _bloco(da[da["horizonte"] == 14]),
                "todos_os_dias_h1_14": _bloco(d),
            }
        if c == LOJA:
            continue
        ref = dc[(dc["metodo"] == REFERENCIA) & aberto.loc[dc.index]]
        for met in [m for m in METODOS if m != REFERENCIA]:
            alt = dc[(dc["metodo"] == met) & aberto.loc[dc.index]]
            j = alt.merge(ref, on=["origem", "data", "horizonte"], suffixes=("", "_r"))
            j1 = j[j["horizonte"] == 1].sort_values("data")
            q = (j.groupby("origem").agg(p=("previsto", "sum"), pr=("previsto_r", "sum"),
                                         r=("real", "sum")).sort_index())
            out[c]["diebold_mariano_vs_" + REFERENCIA][met] = {
                "h1_erro_absoluto_diario": diebold_mariano(
                    (j1["real"] - j1["previsto"]).abs(), (j1["real"] - j1["previsto_r"]).abs(), 1),
                "soma_14d_erro_absoluto": diebold_mariano(
                    (q["r"] - q["p"]).abs(), (q["r"] - q["pr"]).abs(), HORIZONTE),
            }
    return out


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def _base(slug: str) -> str:
    return os.path.join(METRICS_DIR, f"categoria_direta_vs_desag_{slug}")


def montar_series(unidade: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    fluxo, _ = carregar_fluxo(unidade)
    idx = pd.date_range(fluxo["emissao"].min(), fluxo["emissao"].max(), freq="D")
    cat = (fluxo.groupby(["emissao", "categoria"])["qtdade"].sum().unstack(fill_value=0.0)
           .reindex(index=idx, columns=CATEGORIAS, fill_value=0.0))
    loja = fluxo.groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    if not np.allclose(loja.values, cat.sum(axis=1).values):
        raise ValueError("a venda da loja nao e a soma das 4 categorias")
    series = cat.assign(**{LOJA: loja})
    X = exogenas(unidade, idx.append(pd.date_range(idx[-1] + pd.Timedelta(days=1),
                                                   periods=HORIZONTE, freq="D")))
    return series, X


def executar(slug: str, workers: int) -> dict:
    unidade = UNIDADES[slug]
    t0 = time.time()
    series, X = montar_series(unidade)
    idx = series.index
    janela = int((idx < PRIMEIRA_ORIGEM).sum())
    origens = list(pd.date_range(PRIMEIRA_ORIGEM, idx[-1] - pd.Timedelta(days=HORIZONTE - 1),
                                 freq=f"{PASSO_ORIGEM}D"))
    print(f"=== {unidade} === janela deslizante {janela} d · {len(origens)} origens "
          f"({origens[0].date()} -> {origens[-1].date()}) · h={HORIZONTE}", flush=True)

    nomes = [LOJA] + CATEGORIAS
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(series, X, janela)) as ex:
        ordens = dict(ex.map(_ordem, nomes))
        for n in nomes:
            print(f"[ordem] {n:20s} {ordens[n]['order']}{ordens[n]['seasonal_order']} "
                  f"AIC {ordens[n]['aic']:.1f}", flush=True)
        print(f"[ordens] {time.time() - t0:.0f}s", flush=True)
        blocos = [origens[i::workers] for i in range(workers)]
        tarefas = [(n, ordens[n], b) for n in nomes for b in blocos if b]
        linhas = [l for lote in ex.map(_lote, tarefas) for l in lote]
    fits = pd.DataFrame(linhas)
    print(f"[walk-forward] {fits.groupby('serie')['origem'].nunique().to_dict()} origens "
          f"ajustadas ({time.time() - t0:.0f}s)", flush=True)

    loja = fits[fits["serie"] == LOJA]
    # So origens em que a loja e as 4 categorias convergiram: mesma amostra para todos.
    comuns = set.intersection(*(set(fits.loc[fits["serie"] == n, "origem"]) for n in nomes))
    direto = fits[(fits["serie"] != LOJA)].assign(metodo="direto")
    bottom_up = (direto.groupby(["origem", "data", "horizonte"], as_index=False)
                 [["previsto", "ic_inf", "ic_sup"]].sum()
                 .assign(serie=LOJA, metodo="bottom_up_direto"))
    # IC do bottom-up somando limites = cobertura conservadora (assume correlacao perfeita).
    prev = pd.concat([direto, desagregar(loja, series[CATEGORIAS]),
                      loja.assign(metodo="l1_loja"), bottom_up], ignore_index=True)
    prev = prev[prev["origem"].isin(comuns)]
    prev = anexar_real_e_naive(prev, series, janela).reset_index(drop=True)
    prev.to_csv(f"{_base(slug)}_previsoes.csv", sep=";", index=False, decimal=".")

    config = {
        "base": "fluxo diario (sem servico e taxa, sem encomendas > 2.000 un. no documento — ADR-013)",
        "categorias": CATEGORIAS,
        "janela": "deslizante", "janela_dias": janela,
        "passo_origem_dias": PASSO_ORIGEM, "horizonte_dias": HORIZONTE,
        "primeira_origem": str(PRIMEIRA_ORIGEM.date()), "n_origens": len(origens),
        "n_origens_comuns": len(comuns),
        "janela_participacao_dias": JANELA_SHARE_DIAS,
        "receita_sarimax": "sem log1p, d = 1, D = 0, m = 7, exogenas de calendario; ordem por AIC antes da 1a origem",
        "ordens": {n: {"order": list(o["order"]), "seasonal_order": list(o["seasonal_order"]),
                       "aic": o["aic"]} for n, o in ordens.items()},
        "metodos": METODOS + ["naive", "l1_loja", "bottom_up_direto"],
        "referencia": REFERENCIA,
        "tempo_s": round(time.time() - t0),
    }
    return relatorio(slug, prev, config)


def relatorio(slug: str, prev: pd.DataFrame, config: dict) -> dict:
    unidade = UNIDADES[slug]
    met = comparar(prev, fechados_da_unidade(unidade))
    saida = {"unidade": unidade, "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
             "config": config, "metricas": met,
             "arquivos": {"previsoes": f"{_base(slug)}_previsoes.csv"}}
    with open(f"{_base(slug)}.json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)

    print(f"\n[resultado] {unidade} · dias de loja aberta, h = 1..14 (h = 1 entre parenteses)")
    print(f"  {'serie':20s} {'metodo':17s} {'MASE':>13s} {'÷naive':>7s} {'vence':>6s} "
          f"{'IC95':>6s} {'largura':>8s} {'prev/real':>9s} {'erro 14d':>8s}")
    for c in CATEGORIAS + [LOJA]:
        for m, b in met[c]["metodos"].items():
            g, h1 = b["dias_abertos_h1_14"], b["dias_abertos_h1"]
            print(f"  {c:20s} {m:17s} {g['mase']:6.3f} ({h1['mase']:.3f}) "
                  f"{g['erro_relativo_naive']:7.3f} {g['vence_naive_pct']:5.1f}% "
                  f"{g['cobertura_ic95_pct']:5.1f}% {g['largura_ic95']:8.1f} "
                  f"{g['previsto_sobre_real_pct']:8.1f}% {g['erro_total_14d_pct']:7.1f}%")
        for m, t in met[c].get("diebold_mariano_vs_" + REFERENCIA, {}).items():
            a, b = t["h1_erro_absoluto_diario"], t["soma_14d_erro_absoluto"]
            print(f"  {'':20s} DM {m} vs {REFERENCIA}: h=1 est {a['estatistica_hln']:+.2f} "
                  f"p {a['p_valor']:.3f} · soma 14d est {b['estatistica_hln']:+.2f} p {b['p_valor']:.3f}")
    print(f"[arquivos] {_base(slug)}.json · _previsoes.csv", flush=True)
    return saida


def recalcular_metricas(slug: str) -> dict:
    prev = pd.read_csv(f"{_base(slug)}_previsoes.csv", sep=";", parse_dates=["origem", "data"])
    with open(f"{_base(slug)}.json", encoding="utf-8") as fh:
        config = json.load(fh)["config"]
    return relatorio(slug, prev, config)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--unidade", choices=[*UNIDADES, "todas"], default="todas")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--so-metricas", action="store_true",
                    help="recalcula metricas a partir do _previsoes.csv ja salvo")
    a = ap.parse_args()
    for slug in (UNIDADES if a.unidade == "todas" else [a.unidade]):
        recalcular_metricas(slug) if a.so_metricas else executar(slug, a.workers)


if __name__ == "__main__":
    main()
