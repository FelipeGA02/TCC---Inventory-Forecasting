"""Métricas do walk-forward e status do modelo (limiares do `CLAUDE.md`). Lógica pura.

As métricas que decidem o status são as dos **dias de loja aberta**: no domingo e no
feriado a venda é 0 e a previsão também, o que baixaria o MASE e subiria a cobertura sem
dizer nada sobre a previsão.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STATUS_TREINADO = "trained"
STATUS_BAIXA_CONFIANCA = "low_confidence"
STATUS_DADOS_INSUFICIENTES = "insufficient_data"
STATUS_ERRO = "error"


def _arred(v: float | None, casas: int = 3) -> float | None:
    return None if v is None or not np.isfinite(v) else round(float(v), casas)


def metricas_walk_forward(pontos: pd.DataFrame) -> dict:
    """Métricas de um walk-forward.

    `pontos`: uma linha por (origem, dia previsto), com `previsto`, `ic_inf`, `ic_sup`,
    `real`, `naive` (repete a última semana do treino), `escala` (erro médio da naïve
    sazonal dentro do treino da origem — o denominador do MASE) e `aberta` (bool).
    """
    d = pontos[pontos["aberta"]]
    if d.empty:
        return {"dias_avaliados": 0}
    erro = (d["real"] - d["previsto"]).abs()
    erro_naive = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    com_escala = d["escala"] > 0
    por_origem = d.assign(e=erro, en=erro_naive).groupby("origem")[["e", "en"]].sum()
    vendido = float(d["real"].sum())
    return {
        "origens": int(pontos["origem"].nunique()),
        "dias_avaliados": int(len(d)),
        "mae": _arred(erro.mean(), 2),
        "rmse": _arred(float(np.sqrt(((d["real"] - d["previsto"]) ** 2).mean())), 2),
        "mase": _arred((erro[com_escala] / d.loc[com_escala, "escala"]).mean()) if com_escala.any() else None,
        "erro_relativo_naive": _arred(erro.sum() / erro_naive.sum()) if erro_naive.sum() else None,
        "origens_vence_naive_pct": _arred((por_origem["e"] < por_origem["en"]).mean() * 100, 1),
        "cobertura_ic95_pct": _arred(dentro.mean() * 100, 1),
        "largura_ic95": _arred((d["ic_sup"] - d["ic_inf"]).mean(), 2),
        "venda_media_dia": _arred(d["real"].mean(), 2),
        "previsto_sobre_real_pct": _arred(d["previsto"].sum() / vendido * 100, 1) if vendido else None,
    }


def status_do_modelo(metricas: dict, *, mase_max: float = 1.0,
                     cobertura_min: float = 90.0, cobertura_max: float = 98.0) -> str:
    """`trained` se bate a naïve sazonal (MASE < `mase_max`) e a faixa de 95% acerta entre
    `cobertura_min` e `cobertura_max`; senão `low_confidence` — a previsão sai, com aviso."""
    mase, cob = metricas.get("mase"), metricas.get("cobertura_ic95_pct")
    if mase is None or cob is None:
        return STATUS_BAIXA_CONFIANCA
    ok = mase < mase_max and cobertura_min <= cob <= cobertura_max
    return STATUS_TREINADO if ok else STATUS_BAIXA_CONFIANCA
