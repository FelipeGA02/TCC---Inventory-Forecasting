"""**Substituído por `estacionariedade_fiel_ao_modelo.py`** (doc 10 §3.1): este script testa o resíduo
só dos dias de loja aberta, emendados e sem `loja_fechada`, e não a série que o SARIMAX diferencia
(todos os dias, com as exógenas do modelo). Fica como registro da 1ª versão do doc 10.

Raiz unitária e nível local na janela em que o AIC escolhe a ordem — fundamento teórico para d.

Pergunta: a janela de 365 dias que o treino usa para escolher a ordem (a que termina na véspera da 1ª origem
do walk-forward, `trainer.treinar_serie`) pede d = 1? O teste é feito nessa janela em cada um dos 52 cortes
semanais das variantes (01/03/2025 a 21/02/2026) e no corte de produção (última venda da base).

Séries: as 8 categorias (as 6 que não são Grama servem de controle: nelas o d = 1 não ajudou) e os produtos
de grama com previsão. Mesma série do treino (`servico_previsao._montar_series`, sem encomendas grandes).

Três fundamentos, todos sobre o que o SARIMAX vê depois do calendário:

1. **Regra de Hyndman & Khandakar (2008, J. Stat. Softw. 27(3))**, a do `auto.arima`: d = 1 se o KPSS de nível
   (Kwiatkowski, Phillips, Schmidt & Shin, 1992) rejeita a estacionariedade a 5% nos resíduos da regressão nas
   exógenas. Aqui: resíduo de OLS nas dummies de dia da semana e na abertura excepcional, nos dias de loja
   aberta (dia fechado não é observação: o modelo de produção zera a previsão nele).
2. **Modelo de nível local** (Harvey, 1989, *Forecasting, Structural Time Series Models and the Kalman Filter*;
   Muth, 1960): y_t = μ_t + x_t'β + u_t, μ_t = μ_{t−1} + η_t, u_t AR(1). Com σ²_η > 0 a forma reduzida de y é
   integrada de ordem 1 (o nível local puro é exatamente um ARIMA(0,1,1)); com σ²_η = 0 o nível é constante e
   d = 0. Teste de razão de verossimilhança de σ²_η = 0 contra σ²_η > 0; como o parâmetro está na fronteira, a
   distribuição nula é ½χ²₀ + ½χ²₁ (Self & Liang, 1987, JASA 82). O KPSS é o teste LM dessa mesma hipótese.
   Dia de loja fechada entra como observação faltante no filtro de Kalman.
3. **ADF** (Said & Dickey, 1984; lags por AIC) e **DF-GLS** (Elliott, Rothenberg & Stock, 1996), H0: raiz
   unitária. Quando a diferença da série tem raiz MA perto de −1 (ACF1 da diferença perto de −0,5, o caso
   destas séries), o ADF rejeita a raiz unitária muito mais que os 5% nominais (Schwert, 1989, JBES 7;
   Agiakloglou & Newbold, 1992); o DF-GLS sofre menos com isso (Ng & Perron, 2001). Por isso a rejeição do
   ADF não basta para afirmar d = 0.

Uso (a partir de `ia-predictor/`, com o banco de DATABASE_URL):
    python -m training_scripts.validation.estacionariedade_janela_aic --workers 12
"""
from __future__ import annotations

import argparse
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import chi2

from backend.domain.models.trainer import ConfigTreino, motivo_inelegivel, origens_walk_forward

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(_RAIZ, "results", "metrics", "estacionariedade_janela_aic")
VARIANTES = os.path.join(_RAIZ, "results", "metrics", "variantes_nivel_sazonal")
ALPHA = 0.05
CORTES = list(pd.date_range("2025-03-01", "2026-02-21", freq="7D"))


def _residuo(y: pd.Series, X: pd.DataFrame, aberta: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """y nos dias de loja aberta e as exógenas desses dias (sem `loja_fechada` e sem a segunda, a base)."""
    idx = y.index[aberta.loc[y.index].values.astype(bool)]
    cols = [c for c in X.columns if c not in ("loja_fechada", "dia_seg") and X.loc[idx, c].std() > 0]
    return y.loc[idx].astype(float), X.loc[idx, cols].astype(float)


def _testes(y: pd.Series, X: pd.DataFrame, aberta: pd.Series) -> dict:
    from arch.unitroot import DFGLS
    from statsmodels.tools.sm_exceptions import InterpolationWarning
    from statsmodels.tsa.statespace.structural import UnobservedComponents
    from statsmodels.tsa.stattools import adfuller, kpss
    warnings.simplefilter("ignore")

    ya, Xa = _residuo(y, X, aberta)
    A = np.column_stack([np.ones(len(ya)), Xa.values])
    b, *_ = np.linalg.lstsq(A, ya.values, rcond=None)
    r = ya.values - A @ b
    out = {"dias_abertos": len(r), "acf1_dif": float(pd.Series(np.diff(r)).autocorr(1))}
    out["kpss_p"] = float(kpss(r, regression="c", nlags="auto")[1])
    out["adf_p"] = float(adfuller(r, regression="c", autolag="AIC")[1])
    try:
        out["dfgls_p"] = float(DFGLS(r, trend="c", method="aic").pvalue)
    except Exception:  # noqa: BLE001
        out["dfgls_p"] = np.nan

    # nível local × nível fixo, dia fechado = faltante
    yn = y.astype(float).where(aberta.loc[y.index].astype(bool))
    Xn = X.loc[y.index, list(Xa.columns)]
    llf = {}
    for nome, estoc in (("local", True), ("fixo", False)):
        m = UnobservedComponents(yn, level=True, stochastic_level=estoc, irregular=True, autoregressive=1, exog=Xn)
        best = None
        for metodo in ("lbfgs", "nm"):
            try:
                f = m.fit(disp=False, method=metodo, maxiter=500)
                if best is None or f.llf > best.llf:
                    best = f
            except Exception:  # noqa: BLE001
                pass
        llf[nome] = best
    if llf["local"] is not None and llf["fixo"] is not None:
        lr = max(0.0, 2 * (llf["local"].llf - llf["fixo"].llf))
        out["lr_nivel"] = lr
        out["lr_p"] = 0.5 * float(chi2.sf(lr, 1)) if lr > 0 else 1.0
        s_eta = float(np.sqrt(max(llf["local"].params.get("sigma2.level", 0.0), 0.0)))
        out["deriva_30d_pct"] = s_eta * np.sqrt(30) / float(ya.mean()) * 100 if ya.mean() else np.nan
    return out


def tarefa(args) -> list[dict]:
    chave, nivel, y, X, aberta, corte = args
    cfg = ConfigTreino()
    y_c = y[y.index <= corte]
    origem0 = origens_walk_forward(corte, cfg)[0]
    pre = y_c[y_c.index < origem0].iloc[-cfg.janela_dias:]
    base = {"serie": chave, "corte": f"{corte:%Y-%m-%d}", "inicio": f"{pre.index.min():%Y-%m-%d}" if len(pre) else None,
            "fim": f"{pre.index.max():%Y-%m-%d}" if len(pre) else None}
    if motivo_inelegivel(y_c, cfg, nivel) or len(pre) < cfg.min_historico_dias:
        return [{**base, "pulado": True}]
    try:
        return [{**base, "pulado": False, **_testes(pre, X, aberta)}]
    except Exception as e:  # noqa: BLE001
        return [{**base, "pulado": True, "erro": str(e)[:200]}]


def _ganho_d1() -> pd.Series:
    g = []
    for d in (VARIANTES, VARIANTES + "_produtos"):
        f = os.path.join(d, "resumo_semanal.csv")
        if os.path.exists(f):
            r = pd.read_csv(f, sep=";")
            g.append(r[r["variante"] == "d1"].set_index("serie")["mae_vs_base"])
    return pd.concat(g) if g else pd.Series(dtype=float)


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[~df["pulado"]]
    prod = ok[ok["corte"] == ok["corte"].max()].set_index("serie")
    sem = ok[ok["corte"] != ok["corte"].max()]
    g = sem.groupby("serie")
    res = pd.DataFrame({
        "janelas": g.size(),
        "kpss_rejeita_pct": g["kpss_p"].apply(lambda p: (p < ALPHA).mean() * 100),
        "nivel_local_pct": g["lr_p"].apply(lambda p: (p < ALPHA).mean() * 100),
        "adf_nao_rejeita_pct": g["adf_p"].apply(lambda p: (p >= ALPHA).mean() * 100),
        "dfgls_nao_rejeita_pct": g["dfgls_p"].apply(lambda p: (p >= ALPHA).mean() * 100),
        "acf1_dif_mediana": g["acf1_dif"].median(),
        "deriva_30d_mediana_pct": g["deriva_30d_pct"].median(),
    })
    for c, n in (("kpss_p", "prod_kpss_p"), ("lr_p", "prod_lr_p"), ("adf_p", "prod_adf_p"),
                 ("dfgls_p", "prod_dfgls_p"), ("deriva_30d_pct", "prod_deriva_30d_pct")):
        res[n] = prod[c]
    res["ganho_d1_pct"] = _ganho_d1()
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    series = carregar_series()
    escolhidas = {k: s for k, s in series.items()
                  if s.nivel == "category" or not motivo_inelegivel(s.y, ConfigTreino(), s.nivel)}
    fim = max(s.y.index.max() for s in escolhidas.values())
    tarefas = [(k, s.nivel, s.y, s.X, s.aberta, c) for k, s in escolhidas.items() for c in CORTES + [fim]]
    print(f"{len(escolhidas)} séries × {len(CORTES) + 1} janelas = {len(tarefas)} tarefas", flush=True)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    t = time.time()
    linhas = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for i, r in enumerate(pool.map(tarefa, tarefas, chunksize=4), 1):
            linhas += r
            if i % 100 == 0:
                print(f"{i}/{len(tarefas)} {time.time() - t:.0f}s", flush=True)
    df = pd.DataFrame(linhas)
    os.makedirs(SAIDA, exist_ok=True)
    df.to_csv(os.path.join(SAIDA, "janelas.csv"), sep=";", index=False)
    res = resumir(df)
    res.round(4).to_csv(os.path.join(SAIDA, "resumo.csv"), sep=";")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
