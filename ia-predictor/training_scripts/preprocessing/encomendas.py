"""Separação de encomendas grandes + teto de picos na série do L1 (EDA 6, ADR-012).

Problema: a série diária de uma unidade mistura duas demandas de natureza diferente —
a venda de balcão (muitas linhas pequenas, previsível pelo calendário) e encomendas
pontuais de obra/paisagismo (poucas linhas enormes, a maioria faturada por boleto para
um punhado de clientes). Em Itabirito, uma única linha de Grama chega a 20.000 m² num
dia em que o típico é ~200 m². O SARIMAX não tem como antecipar esses picos e eles
inflam o erro de toda a série.

Solução em duas camadas, aplicadas nesta ordem:
  1. **Separar** (`limiares_encomenda` + `marcar_encomendas`): uma linha de venda é
     encomenda quando sua quantidade, sozinha, supera `k` dias típicos (mediana do volume
     diário em dias com venda, seg–sáb) da própria `unidade × categoria`. Essas linhas
     saem da série que o L1 prevê e viram um fluxo à parte (demanda sob pedido — não se
     repõe estoque para ela).
  2. **Teto** (`teto_quantil`): na série de balcão que sobra, os dias acima do quantil
     `q` dos dias abertos do treino são rebaixados a esse quantil (winsorização) antes de
     ajustar o modelo. Só o treino é alterado; o erro é sempre medido na série real.

O limiar é relativo ao dia típico (e não um percentil das linhas) porque em "Produtos de
jardim" linhas de 60–100 mudas são rotina: o p99 das linhas marcaria ~40% do volume.

Tudo é calculado só com o que estava disponível até a origem da previsão (os limiares e
o teto vêm do treino) — sem vazamento no walk-forward.

Funções puras (pandas/numpy): sem I/O, prontas para migrar para `backend/domain/`.
"""
from __future__ import annotations

import pandas as pd

K_DIAS_TIPICOS = 5      # uma linha maior que 5 dias típicos da unidade × categoria é encomenda
QUANTIL_TETO = 0.99     # teto da série de balcão (winsorização) no treino


def limiares_encomenda(linhas: pd.DataFrame, k: float = K_DIAS_TIPICOS,
                       col_qtd: str = "qtdade_n") -> dict[tuple[str, str], float]:
    """Limiar de quantidade por linha, por (unidade, categoria): `k` × mediana do volume
    diário em dias com venda de segunda a sábado. `linhas` precisa das colunas
    `unidade`, `categoria`, `data` e `col_qtd` — e deve conter só o período de treino."""
    diario = (linhas.dropna(subset=["data"])
              .groupby(["unidade", "categoria", linhas["data"].dt.normalize()])[col_qtd].sum())
    diario = diario[diario.index.get_level_values(2).weekday < 6]
    med = diario.groupby(level=[0, 1]).median()
    return {key: float(k * v) for key, v in med.items()}


def marcar_encomendas(linhas: pd.DataFrame, limiares: dict[tuple[str, str], float],
                      col_qtd: str = "qtdade_n") -> pd.Series:
    """Máscara booleana: True nas linhas cuja quantidade supera o limiar da sua
    unidade × categoria. Par sem limiar (sem histórico) nunca é marcado."""
    chave = pd.MultiIndex.from_arrays([linhas["unidade"], linhas["categoria"]])
    lim = pd.Series(chave.map(lambda k: limiares.get(k, float("inf"))), index=linhas.index)
    return linhas[col_qtd] > lim


def teto_quantil(serie: pd.Series, q: float = QUANTIL_TETO) -> pd.Series:
    """Winsoriza a série diária no quantil `q` dos dias abertos (seg–sáb com venda).
    Aplicar só ao treino; domingos e dias zerados não entram no cálculo do quantil."""
    abertos = serie[(serie.index.weekday < 6) & (serie > 0)]
    if abertos.empty:
        return serie
    return serie.clip(upper=float(abertos.quantile(q)))
