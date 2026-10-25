"""Regra do histórico da previsão (`domain.historico_previsao`)."""
from datetime import date, timedelta

import pandas as pd

from backend.domain.historico_previsao import pontos_a_gravar, serie_com_previsto

INICIO = date(2026, 3, 1)


def _p(dia: date, valor: float, source: str, item: str = "grama") -> dict:
    return {"level": "category", "item": item, "day": dia, "predicted": valor, "lower_95": 0.0,
            "upper_95": valor * 2, "source": source}


def _dias(ini: date, n: int) -> list[date]:
    return [ini + timedelta(days=i) for i in range(n)]


def test_previsao_nova_entra_inteira():
    previsao = [_p(d, 10, "forecast") for d in _dias(INICIO, 14)]
    novos = pontos_a_gravar(set(), [], previsao, INICIO)
    assert [p["day"] for p in novos] == _dias(INICIO, 14)


def test_dia_ja_gravado_antes_do_inicio_fica_congelado():
    # semana passada a previsão gravou 22/02..07/03; agora o treino vai até 28/02
    gravados = {("category", "grama", d) for d in _dias(date(2026, 2, 22), 7)}
    walk_forward = [_p(d, 99, "walk_forward") for d in _dias(date(2026, 2, 15), 14)]
    novos = pontos_a_gravar(gravados, walk_forward, [], INICIO)
    assert sorted(p["day"] for p in novos) == _dias(date(2026, 2, 15), 7)  # só os vazios


def test_atraso_maior_que_14_dias_e_preenchido_pelo_walk_forward():
    # última previsão cobriu até 14/02; as vendas só chegaram até 28/02
    gravados = {("category", "grama", d) for d in _dias(date(2026, 2, 1), 14)}
    walk_forward = [_p(d, 5, "walk_forward") for d in _dias(date(2026, 2, 1), 28)]
    previsao = [_p(d, 10, "forecast") for d in _dias(INICIO, 14)]
    novos = pontos_a_gravar(gravados, walk_forward, previsao, INICIO)
    wf = sorted(p["day"] for p in novos if p["source"] == "walk_forward")
    assert wf == _dias(date(2026, 2, 15), 14)
    assert sum(p["source"] == "forecast" for p in novos) == 14


def test_walk_forward_nao_passa_do_inicio_nem_repete_dia():
    walk_forward = [_p(INICIO, 1, "walk_forward"), _p(INICIO - timedelta(days=1), 1, "walk_forward"),
                    _p(INICIO - timedelta(days=1), 2, "walk_forward")]
    novos = pontos_a_gravar(set(), walk_forward, [], INICIO)
    assert [(p["day"], p["predicted"]) for p in novos] == [(INICIO - timedelta(days=1), 1)]


def test_serie_sem_previsto_antes_da_data_fixa():
    real = pd.Series([3.0, 4.0], index=pd.date_range("2025-03-01", periods=2))
    serie = serie_com_previsto(real, {date(2025, 3, 2): (5.0, 1.0, 9.0)})
    assert serie[0] == {"data": "2025-03-01", "real": 3.0, "previsto": None, "inf": None, "sup": None}
    assert serie[1]["previsto"] == 5.0 and serie[1]["sup"] == 9.0
