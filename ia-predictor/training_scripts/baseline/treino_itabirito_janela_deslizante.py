"""Os 4 treinos SARIMAX de Itabirito com janela DESLIZANTE no walk-forward.

Os treinos A-D usam janela expansiva: em cada origem o modelo e reajustado com todos os
dados desde 02/01/2024, e o treino cresce de 425 para 775 dias ao longo do teste. Aqui a
janela anda junto com a origem e o treino fica com tamanho fixo: so os ultimos
`JANELA_DIAS` dias antes de cada origem.

Tamanho da janela: o do treino na primeira origem (425 dias, de 02/01/2024 a 01/03/2025).
Nao e um numero escolhido: e o que torna a comparacao limpa — na primeira rodada as duas
janelas sao identicas, e daí em diante a unica diferenca e a deslizante descartar o dado
mais antigo a cada dia. Ordem do SARIMAX, exogenas, origens e metricas sao as mesmas dos
treinos A-D (`sarimax_itabirito_core`).

Saidas com sufixo `_deslizante`, para nao sobrescrever os resultados da janela expansiva.

Uso (a partir de `ia-predictor/`; cada variante em um processo, podem rodar em paralelo):
    python -m training_scripts.baseline.treino_itabirito_janela_deslizante --variante fluxo_sem_log
    python -m training_scripts.baseline.treino_itabirito_janela_deslizante --variante todas
"""
from __future__ import annotations

import argparse

import pandas as pd

from training_scripts.baseline.sarimax_itabirito_core import (
    BASE_ENCOMENDAS, BASE_FLUXO_DIARIO, BASE_ITABIRITO, PRIMEIRA_ORIGEM, executar, serie_diaria,
)

VARIANTES = {
    "sem_log": dict(usar_log1p=False),                                   # base com encomendas
    "log1p": dict(usar_log1p=True),
    "fluxo_sem_log": dict(usar_log1p=False, base_csv=BASE_FLUXO_DIARIO, encomendas_csv=BASE_ENCOMENDAS),
    "fluxo_log1p": dict(usar_log1p=True, base_csv=BASE_FLUXO_DIARIO, encomendas_csv=BASE_ENCOMENDAS),
}


def janela_dias() -> int:
    """Tamanho do treino na primeira origem (a janela expansiva comeca desse tamanho)."""
    y = serie_diaria(BASE_ITABIRITO)
    return int((y.index < PRIMEIRA_ORIGEM).sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variante", choices=[*VARIANTES, "todas"], default="todas")
    a = ap.parse_args()
    janela = janela_dias()
    for v in (VARIANTES if a.variante == "todas" else [a.variante]):
        executar(f"itabirito_{v}_deslizante", janela_dias=janela, **VARIANTES[v])


if __name__ == "__main__":
    main()
