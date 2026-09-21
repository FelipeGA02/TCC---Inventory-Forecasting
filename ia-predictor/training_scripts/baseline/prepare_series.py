"""Fase 1.2 do plano de experimentos — prepara as 9 séries diárias L1.

Reaproveita a infraestrutura de carga/canonicalização já validada pelo EDA
(`training_scripts/eda/_common.py`): mesma base transacional, mesma
reconstrução da série diária por `unidade × categoria` (soma de `qtdade`,
reindexada no calendário contínuo do par — dias sem venda viram 0).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.prepare_series
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..eda import _common as C

LOG_CV_THRESHOLD = 0.7        # CLAUDE.md — CV (std/mean) acima disso, aplicar log1p
MIN_OBSERVATIONS_DAYS = 180   # CLAUDE.md — mínimo de dias c/ venda p/ treinar L1


def carregar_series() -> dict[tuple[str, str], pd.Series]:
    """As 9 séries diárias L1 (uma por par `unidade × categoria`).

    Soma diária negativa por devolução (`qtdade` < 0, ver
    `docs/prediction/00-eda_report.md` §5 questão 4 — sem definição da parceira ainda) é truncada em 0: um dia com
    "-13 unidades" não é demanda negativa, é ruído de dado para o alvo do L1 e
    quebraria `log1p` (log de número < -1 é indefinido).
    """
    df = C.load_transacoes()
    pares = C.pares_l1(df)
    return {p: C.serie_diaria(df, p[0], p[1], span="par").clip(lower=0.0) for p in pares}


def aplicar_log1p(s: pd.Series) -> tuple[pd.Series, bool]:
    """`log1p(s)` se o CV da série ultrapassa `LOG_CV_THRESHOLD`, senão `s` como está.

    A flag de retorno é necessária para reverter a transformação no forecast
    (`np.expm1`) antes de calcular métricas na escala original de `qtdade`.
    """
    x = s.astype(float)
    media = x.mean()
    cv = float(x.std() / media) if media else 0.0
    if cv > LOG_CV_THRESHOLD:
        return np.log1p(x), True
    return x, False


def atende_minimo(s: pd.Series) -> bool:
    """`True` se a série tem >= MIN_OBSERVATIONS_DAYS dias com venda (> 0)."""
    return int((s.values > 0).sum()) >= MIN_OBSERVATIONS_DAYS


if __name__ == "__main__":
    for (u, c), s in carregar_series().items():
        _, log1p = aplicar_log1p(s)
        dias_venda = int((s.values > 0).sum())
        print(f"[prepare_series] {u} · {c}: {len(s)} dias calendário, "
              f"{dias_venda} dias c/ venda, log1p={log1p}, "
              f"min_180d={'ok' if atende_minimo(s) else 'insuficiente'}")
