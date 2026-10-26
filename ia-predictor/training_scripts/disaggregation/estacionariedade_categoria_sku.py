"""Estacionariedade das 12 series de categoria e de SKU — e se ela explica o `d` escolhido.

Pergunta
--------
O walk-forward de `variantes_log_d_categoria_sku.py` escolheu `d = 1` para quase tudo e
`d = 0` para Flores de corte, nas 2 unidades. Teste de raiz unitaria concorda? E onde nao
concordar, por que o walk-forward ganha a discussao?

Isso ja aconteceu um nivel acima: no L1 por loja o ADF indicava `d = 0` e o `d = 1` venceu
no walk-forward (doc 04, registrado no `CLAUDE.md`). Aqui o mesmo confronto e feito por
categoria e por SKU, com o diagnostico de POR QUE os dois discordam.

Desenho do teste — por que nao basta ADF na serie crua
------------------------------------------------------
A serie diaria tem ~17% de zeros, quase todos domingo e feriado (loja fechada). Isso e uma
media que muda com o dia da semana, nao uma raiz unitaria, e desregula ADF e KPSS: o teste
ve a estrutura periodica determinística e a confunde com dependencia. Alem disso o SARIMAX
do projeto leva 8 exogenas de calendario, logo `d` nao se aplica a serie crua — se aplica
ao que sobra DEPOIS do calendario, que e o que a parte ARMA modela.

Por isso cada serie e testada em 3 formas:

  * `crua`          — a serie diaria no calendario cheio (o que um leitor espera ver);
  * `aberta_sem_cal`— so dias de loja aberta, com o efeito de dia-da-semana removido por
                      OLS (residuo da regressao nas 6 dummies). **E esta a forma que
                      corresponde ao que o modelo diferencia**;
  * `aberta_dif1`   — a primeira diferenca da forma acima, para detectar
                      SOBREdiferenciacao.

Testes e como ler os dois juntos
--------------------------------
ADF (H0 = tem raiz unitaria) e KPSS (H0 = e estacionaria) tem hipoteses nulas opostas, e a
leitura conjunta e mais informativa que qualquer um sozinho:

  * ADF rejeita + KPSS nao rejeita -> I(0), `d = 0` basta;
  * ADF nao rejeita + KPSS rejeita -> I(1), `d = 1` se justifica;
  * ambos rejeitam                 -> ambiguo (tipico de nivel que anda devagar);
  * nenhum rejeita                 -> amostra nao decide.

Sinal de sobrediferenciacao: autocorrelacao de lag 1 da serie diferenciada bem negativa
(abaixo de -0,5 e o sinal classico) e/ou variancia que SOBE ao diferenciar.

Deriva local — a ponte entre "o teste diz I(0)" e "d = 1 ganhou"
----------------------------------------------------------------
Um teste de raiz unitaria olha a amostra inteira. Uma serie pode ser estacionaria em 2 anos
e ter nivel que anda em 8 semanas — e e no horizonte de 14 dias que a previsao vive. Por
isso tambem e medida a **deriva local**: amplitude da media movel de 56 dias dividida pela
media geral. Deriva alta com ADF rejeitando e exatamente o caso em que `d = 1` ganha no
walk-forward sem contrariar o teste: ele nao mede a mesma coisa.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.estacionariedade_categoria_sku
    python -m training_scripts.disaggregation.estacionariedade_categoria_sku --unidade jardim-canada
"""
from __future__ import annotations

import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

from training_scripts.baseline.sarimax_itabirito_core import DIAS, METRICS_DIR
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (
    UNIDADES, exogenas, fechados_da_unidade,
)
from training_scripts.disaggregation.variantes_log_d_categoria_sku import (
    HORIZONTE, montar_series,
)

warnings.filterwarnings("ignore")

ALPHA = 0.05
JANELA_DERIVA = 56         # 8 semanas: o horizonte em que a previsao de 14 dias vive
ACF1_SOBREDIF = -0.5       # abaixo disto, sinal classico de sobrediferenciacao


def _adf(x: np.ndarray) -> dict:
    """ADF com constante e lags por AIC. H0: tem raiz unitaria."""
    try:
        stat, p, lags, nobs, crit, _ = adfuller(x, regression="c", autolag="AIC")
    except Exception:                          # noqa: BLE001
        return {"stat": None, "p": None, "lags": None, "rejeita_h0": None}
    return {"stat": round(float(stat), 3), "p": round(float(p), 4), "lags": int(lags),
            "rejeita_h0": bool(p < ALPHA)}     # rejeitar = NAO tem raiz unitaria


def _kpss(x: np.ndarray) -> dict:
    """KPSS de nivel, lags automaticos. H0: e estacionaria."""
    try:
        stat, p, lags, crit = kpss(x, regression="c", nlags="auto")
    except Exception:                          # noqa: BLE001
        return {"stat": None, "p": None, "lags": None, "rejeita_h0": None}
    return {"stat": round(float(stat), 3), "p": round(float(p), 4), "lags": int(lags),
            "rejeita_h0": bool(p < ALPHA)}     # rejeitar = NAO e estacionaria


def _veredito(adf: dict, kps: dict) -> str:
    a, k = adf["rejeita_h0"], kps["rejeita_h0"]
    if a is None or k is None:
        return "indeterminado"
    if a and not k:
        return "I(0) — d=0 basta"
    if not a and k:
        return "I(1) — d=1 se justifica"
    if a and k:
        return "ambiguo — nivel anda devagar"
    return "amostra nao decide"


def _sem_calendario(y: pd.Series, X: pd.DataFrame, abertos: pd.DatetimeIndex) -> pd.Series:
    """Residuo de `y` nos dias de loja aberta, com o efeito de dia-da-semana removido.

    OLS nas 6 dummies (domingo e a base, mas domingo nao aparece: a loja esta fechada).
    Sem essa limpeza, ADF e KPSS leem o ciclo semanal deterministico como dependencia.
    """
    idx = y.index.intersection(abertos)
    cols = [f"dia_{d}" for d in DIAS]
    A = np.column_stack([np.ones(len(idx)), X.loc[idx, cols].values])
    b, *_ = np.linalg.lstsq(A, y.loc[idx].values, rcond=None)
    return pd.Series(y.loc[idx].values - A @ b, index=idx)


def _deriva(y: pd.Series, janela: int = JANELA_DERIVA) -> float | None:
    """Amplitude da media movel de `janela` dias, em multiplos da media geral."""
    m = y.rolling(janela).mean().dropna()
    if len(m) < 2 or y.mean() == 0:
        return None
    return round(float((m.max() - m.min()) / y.mean()), 2)


def analisar(unidade_slug: str) -> pd.DataFrame:
    unidade = UNIDADES[unidade_slug]
    series, _, meta = montar_series(unidade)
    fechados = fechados_da_unidade(unidade)
    ini = min(s.index.min() for s in series.values())
    fim = max(s.index.max() for s in series.values()) + pd.Timedelta(days=HORIZONTE)
    X = exogenas(unidade, pd.date_range(ini, fim, freq="D"))
    abertos = pd.DatetimeIndex([d for d in pd.date_range(ini, fim, freq="D")
                                if d not in fechados])

    linhas = []
    for nome, y in series.items():
        r = _sem_calendario(y, X, abertos)      # o que a parte ARMA de fato ve
        d1 = r.diff().dropna()
        formas = {"crua": y, "aberta_sem_cal": r, "aberta_dif1": d1}

        reg = {
            "unidade": unidade, "serie": nome, "n_dias": len(y),
            "zeros_pct": round(float((y == 0).mean() * 100), 1),
            "media": round(float(y.mean()), 1),
            "cv": round(float(y.std() / y.mean()), 2) if y.mean() else None,
            "deriva_56d_x_media": _deriva(y[y.index.isin(abertos)]),
            "acf1_dif1": round(float(d1.autocorr(1)), 3),
            "var_sobe_ao_diferenciar": bool(d1.var() > r.var()),
        }
        for forma, x in formas.items():
            a, k = _adf(x.values), _kpss(x.values)
            reg[f"adf_p_{forma}"] = a["p"]
            reg[f"kpss_p_{forma}"] = k["p"]
            reg[f"veredito_{forma}"] = _veredito(a, k)
        reg["sobrediferenciado"] = bool(reg["acf1_dif1"] < ACF1_SOBREDIF
                                        or reg["var_sobe_ao_diferenciar"])
        linhas.append(reg)

    return pd.DataFrame(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unidade", default=None, choices=sorted(UNIDADES),
                    help="uma unidade; sem o argumento, roda as 2")
    a = ap.parse_args()
    slugs = [a.unidade] if a.unidade else sorted(UNIDADES)

    tudo = pd.concat([analisar(s) for s in slugs], ignore_index=True)
    os.makedirs(METRICS_DIR, exist_ok=True)
    base = os.path.join(METRICS_DIR, "estacionariedade_categoria_sku")
    tudo.to_csv(f"{base}.csv", sep=";", index=False, decimal=".")
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump({"alpha": ALPHA, "janela_deriva_dias": JANELA_DERIVA,
                   "acf1_corte_sobredif": ACF1_SOBREDIF,
                   "linhas": tudo.to_dict("records")}, fh, ensure_ascii=False,
                  indent=2, default=str)

    pd.set_option("display.width", 250)
    print("=== perfil das series (dias de loja aberta para a deriva) ===")
    print(tudo[["unidade", "serie", "n_dias", "zeros_pct", "media", "cv",
                "deriva_56d_x_media"]].to_string(index=False))
    print("\n=== ADF (H0: raiz unitaria) e KPSS (H0: estacionaria) — p-valores ===")
    print(tudo[["unidade", "serie", "adf_p_crua", "kpss_p_crua",
                "adf_p_aberta_sem_cal", "kpss_p_aberta_sem_cal",
                "adf_p_aberta_dif1", "kpss_p_aberta_dif1"]].to_string(index=False))
    print("\n=== veredito por forma ===")
    print(tudo[["unidade", "serie", "veredito_crua", "veredito_aberta_sem_cal",
                "veredito_aberta_dif1"]].to_string(index=False))
    print("\n=== sinais de sobrediferenciacao ===")
    print(tudo[["unidade", "serie", "acf1_dif1", "var_sobe_ao_diferenciar",
                "sobrediferenciado"]].to_string(index=False))
    print(f"\n[arquivos] {base}.csv · {base}.json")


if __name__ == "__main__":
    main()
