"""Séries diárias de venda a partir das linhas de venda. Lógica pura (pandas)."""
from __future__ import annotations

import pandas as pd


def serie_diaria(vendas: pd.DataFrame, fim: pd.Timestamp, inicio: pd.Timestamp | None = None) -> pd.Series:
    """Quantidade vendida por dia, no calendário cheio de `inicio` a `fim`.

    `vendas`: colunas `emissao` (datetime) e `qtdade`. Dia sem venda vira 0 — quase sempre
    domingo ou feriado, que a exógena `loja_fechada` explica para o modelo. Sem `inicio`, a
    série começa na primeira venda (produto que ainda não existia não é demanda zero).
    """
    s = vendas.groupby("emissao")["qtdade"].sum().sort_index()
    ini = inicio if inicio is not None else (s.index.min() if len(s) else fim)
    s = s.reindex(pd.date_range(ini, fim, freq="D"), fill_value=0.0).astype(float)
    s.index.name = "data"
    return s
