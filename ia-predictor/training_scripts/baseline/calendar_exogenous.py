"""Fase 1.3 — exógenas de calendário do baseline (Modelo A1, sem enriquecimento).

Só o que dá para derivar do próprio calendário, sem nenhuma base externa —
feriados municipais, clima e "dias até data comemorativa" ficam para o Modelo B
(`training_scripts/enriched/`, Fase 3 do plano de experimentos):

- dummies de dia-da-semana (terça a domingo; segunda-feira é a categoria-base
  omitida — evita a armadilha da dummy, já que o SARIMAX ajusta intercepto);
- feriado nacional fixo (mesma tabela do EDA, `eda._common.feriados_fixos`) e
  véspera de feriado.

Uso:
    from training_scripts.baseline.calendar_exogenous import build_calendar_exogenous
    exog = build_calendar_exogenous(serie.index)
"""
from __future__ import annotations

import pandas as pd

from ..eda import _common as C

_DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

EXOG_COLS = [f"dow_{nome}" for nome in _DIAS[1:]] + ["feriado_nacional", "vespera_feriado"]


def build_calendar_exogenous(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Exógenas de calendário para o índice diário informado.

    Determinístico a partir da data — funciona tanto para o histórico (ajuste)
    quanto para datas futuras (forecast), sem depender de nenhum dado ainda não
    observado.
    """
    idx = pd.DatetimeIndex(index).normalize()
    out = pd.DataFrame(index=idx)
    for i, nome in enumerate(_DIAS[1:], start=1):   # pula segunda (baseline)
        out[f"dow_{nome}"] = (idx.weekday == i).astype(float)

    anos = range(idx.year.min(), idx.year.max() + 1)
    feriados = C.feriados_fixos(anos)
    vesperas = feriados - pd.Timedelta(days=1)
    out["feriado_nacional"] = idx.isin(feriados).astype(float)
    out["vespera_feriado"] = idx.isin(vesperas).astype(float)
    return out[EXOG_COLS]


if __name__ == "__main__":
    idx = pd.date_range("2026-01-01", "2026-01-14", freq="D")
    print(build_calendar_exogenous(idx))
