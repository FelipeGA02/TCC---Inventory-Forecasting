"""Ajuste de parametros do SARIMAX por produto (SKUs de venda regular).

Continuacao de `sku_regular_vs_desagregacao.py`. La, o SARIMAX de cada SKU herdou a
configuracao do L1 da loja: d = 1 fixo e ordem escolhida por AIC na serie SEM
transformacao, mesmo na variante log1p. Aqui cada uma dessas escolhas vira hipotese:

  * d = 0 x d = 1 — no L1, d = 1 faz a previsao acompanhar o nivel recente da loja. Num
    SKU, a serie e ruidosa e volta a media; d = 1 pode fazer a previsao perseguir o ultimo
    pico. Com d = 0 o modelo leva constante (`trend="c"`, como no core).
  * transformacao (nenhuma x log1p) — e a ordem passa a ser escolhida por AIC na serie que
    o modelo de fato ajusta (transformada).

Configuracoes testadas por SKU: {d0, d1} x {sem_log, log1p}. Para cada uma, a ordem
(p,q em 0..2; P,Q em 0..1; m = 7) e escolhida por AIC com os dados anteriores a primeira
rodada em que o SKU e regular.

Escolha da configuracao sem vazamento (`auto`)
----------------------------------------------
Comparar as 4 configuracoes no teste e ficar com a melhor seria escolher olhando o
resultado. A variante `auto` escolhe por SKU usando so o passado: uma validacao interna
com 4 origens (a cada 14 dias, h = 14) nas 8 semanas anteriores a primeira rodada do SKU;
vence a configuracao de menor erro absoluto medio nos dias de loja aberta. E a variante
`auto` que responde "qual o resultado do SARIMAX por produto bem ajustado".

Mesmo protocolo externo do experimento anterior: fluxo diario, mesmos SKUs regulares por
rodada, origem andando de 1 em 1 dia desde 2025-03-02 com h = 14, metricas nos dias de loja
aberta. Saidas no formato da loja: `_previsoes.csv` (14 horizontes), `_operacional.csv`
(h = 1) e metricas em blocos todos os horizontes / `operacional_h1` / `por_horizonte`. A
validacao interna continua com 4 origens a cada 14 dias (8 semanas), que nao muda com o
passo do walk-forward externo.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.sku_regular_tuning --unidade itabirito
"""
from __future__ import annotations

import argparse
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

from training_scripts.baseline.sarimax_itabirito_core import (  # noqa: E402
    ALPHA, GRID_PQ, GRID_SPQ, HORIZONTE, M, MAXITER, METRICS_DIR, PRIMEIRA_ORIGEM,
)
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (  # noqa: E402
    PASSO_PADRAO, UNIDADES, blocos, carregar_fluxo, exogenas, fechados_da_unidade,
    gravar_previsoes, skus_regulares,
)

warnings.filterwarnings("ignore")

PASSO = PASSO_PADRAO       # walk-forward externo: origem anda 1 dia, como na loja
CONFIGS = {f"d{d}|{t}": {"d": d, "log": t == "log1p"} for d in (0, 1) for t in ("sem_log", "log1p")}
VALID_ORIGENS = 4          # validacao interna: 4 origens x 14 dias = 8 semanas antes da 1a rodada
VALID_PASSO = 14


# --------------------------------------------------------------------------- #
# Modelo
# --------------------------------------------------------------------------- #
def _z(y: pd.Series, log: bool) -> pd.Series:
    return np.log1p(y.clip(lower=0)) if log else y


def _ajustar(z, X, order, sorder):
    return SARIMAX(z, exog=X, order=order, seasonal_order=sorder,
                   trend="c" if order[1] == 0 else "n",
                   enforce_stationarity=False, enforce_invertibility=False
                   ).fit(disp=False, maxiter=MAXITER)


def _selecionar(y: pd.Series, X: pd.DataFrame, d: int, log: bool) -> dict | None:
    """Melhor ordem por AIC na serie transformada que o modelo vai ajustar."""
    z, melhor = _z(y, log), None
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        try:
            res = _ajustar(z, X.loc[z.index], (p, d, q), (P, 0, Q, M))
        except Exception:  # noqa: BLE001
            continue
        if np.isfinite(res.aic) and (melhor is None or res.aic < melhor["aic"]):
            melhor = {"order": (p, d, q), "seasonal_order": (P, 0, Q, M), "aic": float(res.aic)}
    return melhor


def _prever(y, X, ordem, futuro, log):
    res = _ajustar(_z(y, log), X.loc[y.index], ordem["order"], ordem["seasonal_order"])
    fc = res.get_forecast(len(futuro), exog=X.loc[futuro])
    mu, ic = np.asarray(fc.predicted_mean), np.asarray(fc.conf_int(alpha=ALPHA))
    volta = (lambda v: np.clip(np.expm1(v), 0, None)) if log else (lambda v: np.clip(v, 0, None))
    return volta(mu), volta(ic[:, 0]), volta(ic[:, 1])


# --------------------------------------------------------------------------- #
# Tarefas (rodam em processos separados): 1 por SKU para escolher ordens e `auto`,
# depois 1 por SKU x origem para o walk-forward
# --------------------------------------------------------------------------- #
_G: dict = {}


def _init(matriz, X, fechados):
    _G["m"], _G["X"], _G["fech"] = matriz, X, fechados


def _serie(sku, ate):
    s = _G["m"][sku]
    s = s[s.index < ate]
    return s[s.index >= s[s > 0].index.min()]


def _preparar_sku(args) -> tuple[str, dict, dict]:
    """Ordem de cada configuracao e escolha `auto`, so com dados antes da 1a rodada do SKU."""
    sku, primeira = args
    X, fech, m = _G["X"], _G["fech"], _G["m"]
    hist = _serie(sku, primeira)

    # 1) ordem por AIC para cada configuracao, com dados antes da 1a rodada do SKU
    ordens = {k: _selecionar(hist, X, c["d"], c["log"]) for k, c in CONFIGS.items()}

    # 2) validacao interna nas 8 semanas anteriores -> escolha da configuracao `auto`
    v_origens = [primeira - pd.Timedelta(days=VALID_PASSO * i) for i in range(VALID_ORIGENS, 0, -1)]
    erro_valid = {}
    for k, c in CONFIGS.items():
        if ordens[k] is None:
            continue
        aes = []
        for vo in v_origens:
            fut = pd.date_range(vo, periods=HORIZONTE, freq="D")
            try:
                p, _, _ = _prever(_serie(sku, vo), X, ordens[k], fut, c["log"])
            except Exception:  # noqa: BLE001
                continue
            aberto = ~fut.isin(fech)
            aes.extend(np.abs(m.loc[fut, sku].values - p)[aberto])
        if aes:
            erro_valid[k] = float(np.mean(aes))
    escolhida = min(erro_valid, key=erro_valid.get) if erro_valid else None

    meta = {"ordens": {k: (None if v is None else {"order": list(v["order"]),
                                                    "seasonal_order": list(v["seasonal_order"])})
                       for k, v in ordens.items()},
            "erro_validacao": erro_valid, "config_auto": escolhida}
    return sku, ordens, meta


def _rodada_sku(args) -> list[dict]:
    """3) walk-forward externo: uma origem de um SKU, todas as configuracoes."""
    sku, o, ordens = args
    X, m = _G["X"], _G["m"]
    s = _serie(sku, o)
    fut = pd.date_range(o, periods=HORIZONTE, freq="D")
    real = m.loc[fut, sku].values
    ult7 = s.values[-M:]
    naive = np.array([ult7[i % M] for i in range(HORIZONTE)])
    escala = float(np.mean(np.abs(s.values[M:] - s.values[:-M])))
    linhas = []
    for k, c in CONFIGS.items():
        if ordens[k] is None:
            continue
        try:
            p, lo, hi = _prever(s, X, ordens[k], fut, c["log"])
        except Exception:  # noqa: BLE001
            continue
        for h in range(HORIZONTE):
            linhas.append({"origem": o, "data": fut[h], "horizonte": h + 1, "sku": sku,
                           "config": k, "previsto": p[h], "ic_inf": lo[h], "ic_sup": hi[h],
                           "real": real[h], "naive": naive[h], "escala": escala})
    return linhas


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def executar(slug: str, workers: int, passo: int = PASSO) -> dict:
    unidade = UNIDADES[slug]
    t0 = time.time()
    fluxo, nomes = carregar_fluxo(unidade)
    idx = pd.date_range(fluxo["emissao"].min(), fluxo["emissao"].max(), freq="D")
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    X = exogenas(unidade, idx.append(pd.date_range(idx[-1] + pd.Timedelta(days=1),
                                                   periods=HORIZONTE, freq="D")))
    aberta = (X.loc[idx, "loja_fechada"] == 0).astype(int)
    fechados = fechados_da_unidade(unidade)
    origens = list(pd.date_range(PRIMEIRA_ORIGEM, idx[-1] - pd.Timedelta(days=HORIZONTE - 1),
                                 freq=f"{passo}D"))
    regulares = {o: skus_regulares(matriz, aberta, o) for o in origens}
    todos = sorted({s for lst in regulares.values() for s in lst})
    por_sku = {s: [o for o in origens if s in regulares[o]] for s in todos}
    matriz = matriz[todos]
    print(f"=== {unidade} === {len(todos)} SKUs regulares · {len(origens)} rodadas "
          f"(origem a cada {passo} dia(s)) · {len(CONFIGS)} configuracoes {list(CONFIGS)}", flush=True)

    metas, ordens, linhas = {}, {}, []
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(matriz, X, fechados)) as ex:
        for sku, ords, meta in ex.map(_preparar_sku, [(s, o[0]) for s, o in por_sku.items()]):
            ordens[sku], metas[sku] = ords, meta
            print(f"  [{sku}] auto = {meta['config_auto']} · {time.time() - t0:.0f}s", flush=True)
        tarefas = [(s, o, ordens[s]) for s, lst in por_sku.items() for o in lst]
        for n, lin in enumerate(ex.map(_rodada_sku, tarefas, chunksize=4), start=1):
            linhas.extend(lin)
            if n % 250 == 0 or n == len(tarefas):
                print(f"  [walk-forward] {n}/{len(tarefas)} SKU-rodadas · {time.time() - t0:.0f}s",
                      flush=True)
    prev = pd.DataFrame(linhas)

    # `auto`: para cada SKU, as linhas da configuracao escolhida na validacao interna
    auto = pd.concat([prev[(prev["sku"] == s) & (prev["config"] == mt["config_auto"])]
                      for s, mt in metas.items() if mt["config_auto"]]).assign(config="auto")
    prev = pd.concat([prev, auto], ignore_index=True)

    aberto = prev[~prev["data"].isin(fechados)]
    met = {k: blocos(d) for k, d in aberto.groupby("config")}
    ordem_cfg = [*CONFIGS, "auto"]

    # Por SKU: erro / naive no mesmo periodo (abaixo de 1 = venceu o naive sazonal)
    tab = []
    for s, d in aberto.groupby("sku"):
        reg = {"sku": s, "nome": nomes.get(s, ""), "rodadas": len(por_sku[s]),
               "config_auto": metas[s]["config_auto"]}
        for k in ordem_cfg:
            g = d[d["config"] == k]
            if len(g):
                reg[f"{k}|mase"] = round(float(((g.real - g.previsto).abs() / g.escala).mean()), 3)
                reg[f"{k}|razao_naive"] = round(float((g.real - g.previsto).abs().sum()
                                                      / (g.real - g.naive).abs().sum()), 3)
        tab.append(reg)
    tab = pd.DataFrame(tab).sort_values("rodadas", ascending=False)

    base = os.path.join(METRICS_DIR, f"sku_tuning_{slug}")
    arquivos = gravar_previsoes(prev, base)
    tab.to_csv(f"{base}_por_sku.csv", sep=";", index=False, decimal=".")
    saida = {"unidade": unidade, "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
             "configs": list(CONFIGS),
             "walk_forward": {"primeira_origem": str(PRIMEIRA_ORIGEM.date()), "passo_origem_dias": passo,
                              "n_rodadas": len(origens), "horizonte_dias": HORIZONTE},
             "validacao_interna": {"origens": VALID_ORIGENS, "passo": VALID_PASSO},
             "metricas_dias_abertos": met, "por_sku": metas,
             "arquivos": {**arquivos, "por_sku": f"{base}_por_sku.csv"}}
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)

    print(f"\n[resultado] {unidade} · dias de loja aberta")
    print(f"  {'config':14s} {'':5s} {'MASE':>6s} {'÷naive':>7s} {'vence':>6s} {'IC95':>6s} {'larg':>6s} "
          f"{'prev/real':>9s}  ok?")
    for k in ordem_cfg:
        for rot, chave in (("h1-14", "geral_todos_horizontes"), ("h=1", "operacional_h1")):
            b = met[k][chave]
            print(f"  {k:14s} {rot:5s} {b['mase']:6.3f} {b['erro_relativo_naive']:7.3f} "
                  f"{b['vence_naive_pct']:5.1f}% {b['cobertura_ic95_pct']:5.1f}% {b['largura_ic95']:6.1f} "
                  f"{b['previsto_sobre_real_pct']:8.1f}%  {'SIM' if b['passa_criterio_diario'] else 'nao'}")
    print("\n[por SKU] erro ÷ naive sazonal no mesmo periodo (< 1 = venceu o naive)")
    cols = ["nome", "config_auto"] + [f"{k}|razao_naive" for k in ordem_cfg]
    print(tab[cols].to_string(index=False))
    print(f"\n[configuracao escolhida na validacao] {pd.Series([m['config_auto'] for m in metas.values()]).value_counts().to_dict()}")
    print(f"[arquivos] {base}.json · _previsoes.csv · _operacional.csv · _por_sku.csv "
          f"({time.time() - t0:.0f}s)", flush=True)
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--unidade", choices=list(UNIDADES), default="itabirito")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--passo", type=int, default=PASSO, help="dias entre origens")
    a = ap.parse_args()
    executar(a.unidade, a.workers, a.passo)


if __name__ == "__main__":
    main()
