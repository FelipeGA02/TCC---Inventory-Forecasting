"""Exógenas de calendário do SARIMAX: 6 dummies de dia da semana (domingo é a base),
`loja_fechada` e `abertura_excepcional` — as 8 do L1 (`CLAUDE.md`, seção L1).

Lógica pura: recebe o calendário de uma loja já lido (DataFrame indexado por data) e
devolve a matriz para qualquer conjunto de datas, passado ou futuro.
"""
from __future__ import annotations

import pandas as pd

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CALENDARIO = ["loja_fechada", "abertura_excepcional"]
COLUNAS_EXOGENAS = [f"dia_{d}" for d in DIAS_SEMANA] + COLS_CALENDARIO

_DOMINGO = 6


def matriz_exogena(datas: pd.DatetimeIndex, calendario: pd.DataFrame) -> tuple[pd.DataFrame, list[pd.Timestamp]]:
    """Matriz de exógenas para `datas` e a lista dos dias que o calendário não cobre.

    `calendario`: indexado por data, com as colunas `loja_fechada` e `abertura_excepcional`.
    Dia fora do calendário (tipicamente o fim do horizonte quando o calendário não foi
    estendido) recebe o padrão da loja — fechada no domingo, sem abertura excepcional — e
    volta na lista para quem chama registrar o aviso.
    """
    X = pd.DataFrame(index=datas)
    for i, nome in enumerate(DIAS_SEMANA):  # 0 = segunda ... 5 = sábado; domingo é a base
        X[f"dia_{nome}"] = (datas.weekday == i).astype(float)

    cal = calendario.reindex(datas)
    faltando = list(datas[cal["loja_fechada"].isna()])
    X["loja_fechada"] = cal["loja_fechada"].fillna(pd.Series(datas.weekday == _DOMINGO, index=datas)).astype(float)
    X["abertura_excepcional"] = cal["abertura_excepcional"].fillna(0).astype(float)
    return X[COLUNAS_EXOGENAS], faltando
