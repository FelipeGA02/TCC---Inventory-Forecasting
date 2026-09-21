"""Fase 1 do plano de experimentos — Modelo A0 (SARIMA puro) e Modelo A1
(SARIMAX + calendário) por `unidade × categoria`, **sem enriquecimento
externo** (feriados municipais/clima/datas comemorativas ficam para o Modelo B
— `training_scripts/enriched/`, Fase 3).

Para cada um dos 9 pares L1:
  1. prepara a série diária (`prepare_series`) e decide `log1p` pelo CV;
  2. seleciona a ordem por AIC (`order_selection`) — uma vez para A0 (sem
     exógena) e uma vez para A1 (com dummies de dia-da-semana + feriado
     nacional/véspera), sobre o pool de desenvolvimento (exclui o hold-out);
  3. avalia os dois modelos com o MESMO protocolo: hold-out de 28 dias +
     walk-forward CV (origem móvel, horizonte 14 dias, até 4 folds) +
     diagnóstico de resíduos (Ljung-Box, Shapiro-Wilk);
  4. aplica os limiares de `low_confidence` do CLAUDE.md (MASE >= 1.0 ou
     cobertura do IC 95% fora de [90%, 98%]).

Consolida tudo em `results/metrics/baseline_A0_A1.csv` (uma linha por
par × modelo) e `results/metrics/baseline_A0_A1.json` (detalhe completo,
incluindo os folds do walk-forward).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.run_baseline
"""
from __future__ import annotations

import sys
import time

import pandas as pd

from ..eda import _common as C
from . import order_selection as OS
from . import prepare_series as PS
from .calendar_exogenous import build_calendar_exogenous
from .evaluator import TEST_DAYS, avaliar_holdout, avaliar_walk_forward

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

MASE_LIMIAR = 1.0
COBERTURA_IC_FAIXA = (90.0, 98.0)


def _low_confidence(mase: float | None, cobertura: float | None) -> bool:
    if mase is None or mase >= MASE_LIMIAR:
        return True
    if cobertura is None or not (COBERTURA_IC_FAIXA[0] <= cobertura <= COBERTURA_IC_FAIXA[1]):
        return True
    return False


def _rodar_um_modelo(nome_modelo: str, y_original: pd.Series, y_fit: pd.Series,
                      log1p: bool, exog_full: pd.DataFrame | None) -> dict:
    y_dev = y_fit.iloc[:-TEST_DAYS]                # ordem escolhida sem ver o hold-out
    exog_dev = exog_full.loc[y_dev.index] if exog_full is not None else None

    t0 = time.time()
    ordem = OS.selecionar_ordem(y_dev, exog=exog_dev)
    t_ordem = time.time() - t0

    holdout = avaliar_holdout(
        y_original, y_fit, log1p, ordem["order"], ordem["seasonal_order"], exog_full=exog_full,
    )
    wf = avaliar_walk_forward(
        y_original, y_fit, log1p, ordem["order"], ordem["seasonal_order"], exog_full=exog_full,
    )
    low_conf = _low_confidence(holdout["mase"], holdout["cobertura_ic95"])
    return {
        "modelo": nome_modelo,
        "order": ordem["order"],
        "seasonal_order": ordem["seasonal_order"],
        "aic_selecao": ordem["aic"],
        "log1p": log1p,
        "tempo_selecao_ordem_s": round(t_ordem, 1),
        "status": "low_confidence" if low_conf else "trained",
        **{f"holdout_{k}": v for k, v in holdout.items()},
        "walk_forward": wf,
    }


def rodar_par(nome_par: str, u: str, c: str, y_original: pd.Series) -> list[dict]:
    y_fit, log1p = PS.aplicar_log1p(y_original)
    exog = build_calendar_exogenous(y_original.index)

    print(f"[baseline] {nome_par} — {len(y_original)} dias, log1p={log1p} — Modelo A0...")
    a0 = _rodar_um_modelo("A0_sarima_puro", y_original, y_fit, log1p, exog_full=None)
    print(f"[baseline] {nome_par} — A0: order={a0['order']}{a0['seasonal_order']} "
          f"MASE(holdout)={a0['holdout_mase']:.3f} status={a0['status']}")

    print(f"[baseline] {nome_par} — Modelo A1 (+ calendário)...")
    a1 = _rodar_um_modelo("A1_sarimax_calendario", y_original, y_fit, log1p, exog_full=exog)
    print(f"[baseline] {nome_par} — A1: order={a1['order']}{a1['seasonal_order']} "
          f"MASE(holdout)={a1['holdout_mase']:.3f} status={a1['status']}")

    for r in (a0, a1):
        r["par"] = nome_par
        r["unidade"] = u
        r["categoria"] = c
        r["dias_calendario"] = int(len(y_original))
        r["dias_com_venda"] = int((y_original.values > 0).sum())
    return [a0, a1]


def main() -> pd.DataFrame:
    t_inicio = time.time()
    series = PS.carregar_series()
    print(f"[baseline] {len(series)} pares L1 carregados")

    linhas = []
    for (u, c), s in series.items():
        nome_par = f"{u} · {c}"
        if not PS.atende_minimo(s):
            print(f"[baseline] {nome_par}: insufficient_data (< {PS.MIN_OBSERVATIONS_DAYS} "
                  "dias c/ venda) — pulando")
            continue
        linhas.extend(rodar_par(nome_par, u, c, s))

    detalhado = pd.DataFrame(linhas)
    resumo_cols = [
        "par", "unidade", "categoria", "modelo", "order", "seasonal_order", "log1p",
        "dias_calendario", "dias_com_venda", "holdout_mae", "holdout_rmse",
        "holdout_mase", "holdout_rmsse", "holdout_mape", "holdout_smape",
        "holdout_cobertura_ic95", "holdout_ljung_box_lag7_pvalue",
        "holdout_shapiro_pvalue", "status",
    ]
    resumo = detalhado[resumo_cols].copy()
    resumo["walk_forward_mase_medio"] = detalhado["walk_forward"].apply(lambda d: d["mase_medio"])
    resumo["walk_forward_rmsse_medio"] = detalhado["walk_forward"].apply(lambda d: d["rmsse_medio"])
    resumo["walk_forward_n_folds"] = detalhado["walk_forward"].apply(lambda d: d["n_folds"])

    csv_path = C.dump_metrics("baseline_A0_A1.json", {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "tempo_total_s": round(time.time() - t_inicio, 1),
        "linhas": linhas,
    })
    import os
    resumo_path = os.path.join(C.METRICS_DIR, "baseline_A0_A1.csv")
    resumo.to_csv(resumo_path, sep=";", index=False, encoding="utf-8")

    print(f"\n[baseline] concluído em {time.time() - t_inicio:.0f}s")
    print(f"[baseline] resumo: {os.path.relpath(resumo_path, C.REPO_ROOT)}")
    print(f"[baseline] detalhe: {csv_path}")
    print(resumo.to_string(index=False))
    return resumo


if __name__ == "__main__":
    main()
