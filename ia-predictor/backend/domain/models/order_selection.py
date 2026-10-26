"""Escolha da ordem (p, q)(P, Q) do SARIMAX por AIC, com d, D e m fixos. Lógica pura."""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.domain.models.forecaster import ajustar


@dataclass(frozen=True)
class OrdemEscolhida:
    ordem: tuple[int, int, int]
    ordem_sazonal: tuple[int, int, int, int]
    aic: float
    ordens_testadas: int
    ordens_convergidas: int


class NenhumaOrdemConvergiu(Exception):
    """Nenhum ponto do grid ajustou com AIC finito."""


def selecionar_ordem(y: pd.Series, X: pd.DataFrame, *, d: int, D: int, m: int,
                     grade_pq: tuple[int, ...], grade_PQ: tuple[int, ...], maxiter: int = 200,
                     ao_ajustar=None) -> OrdemEscolhida:
    """Menor AIC no grid. Quem chama passa só dados anteriores à primeira origem do
    walk-forward, para a escolha não olhar o período avaliado.

    O AIC compara ordens com os mesmos `d` e `D` sobre a mesma série; não compara séries
    nem diferenciações diferentes entre si.
    """
    melhor: tuple[float, tuple, tuple] | None = None
    grade = list(itertools.product(grade_pq, grade_pq, grade_PQ, grade_PQ))
    convergidas = 0
    for p, q, P, Q in grade:
        ordem, sazonal = (p, d, q), (P, D, Q, m)
        try:
            aic = float(ajustar(y, X, ordem, sazonal, maxiter).aic)
        except Exception:  # noqa: BLE001 — ordem que não ajusta fica de fora do grid
            aic = float("nan")
        if ao_ajustar:
            ao_ajustar()
        if not np.isfinite(aic):
            continue
        convergidas += 1
        if melhor is None or aic < melhor[0]:
            melhor = (aic, ordem, sazonal)
    if melhor is None:
        raise NenhumaOrdemConvergiu()
    return OrdemEscolhida(ordem=melhor[1], ordem_sazonal=melhor[2], aic=melhor[0],
                          ordens_testadas=len(grade), ordens_convergidas=convergidas)
