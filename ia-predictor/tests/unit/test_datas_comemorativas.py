"""Fator das datas comemorativas (`backend/domain/models/datas_comemorativas.py`, ADR-019)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from backend.domain.models.datas_comemorativas import (
    DATAS_DE_PRESENTE,
    ajustes,
    data_do_evento,
    dias_da_janela,
    multiplicadores,
)

PARAMS = {"fracao": 0.5, "teto": 3.0, "ocorrencias": 3}


def _exogenas(inicio: str, fim: str, excepcional: tuple[str, ...] = ()) -> pd.DataFrame:
    dias = pd.date_range(inicio, fim, freq="D")
    X = pd.DataFrame({"loja_fechada": (dias.weekday == 6).astype(float), "abertura_excepcional": 0.0}, index=dias)
    for d in excepcional:
        X.loc[pd.Timestamp(d), ["loja_fechada", "abertura_excepcional"]] = [0.0, 1.0]
    return X


def _venda(X: pd.DataFrame, fim: str, alta: dict[pd.Timestamp, float] | None = None, semente: int = 3) -> pd.Series:
    """Venda com perfil semanal (domingo fechado) e a semana de cada data em `alta`
    multiplicada (data → quantas vezes o normal)."""
    rng = np.random.default_rng(semente)
    dias = X.index[X.index <= pd.Timestamp(fim)]
    perfil = np.array([20, 30, 32, 31, 40, 15, 0.0])
    y = pd.Series(perfil[dias.weekday] + rng.normal(0, 1, len(dias)), index=dias).clip(lower=0)
    y[X.loc[dias, "loja_fechada"].values == 1] = 0.0
    for d, vezes in (alta or {}).items():
        semana = dias_da_janela(X, d).intersection(dias)
        y[semana] *= vezes
    return y


def test_datas_seguem_a_regra_de_cada_ano():
    assert data_do_evento("Dia das Mães", 2025) == pd.Timestamp("2025-05-11")  # 2º domingo de maio
    assert data_do_evento("Dia das Mães", 2026) == pd.Timestamp("2026-05-10")
    assert data_do_evento("Dia dos Pais", 2025) == pd.Timestamp("2025-08-10")
    assert data_do_evento("Dia da Mulher", 2027).date() == date(2027, 3, 8)
    assert data_do_evento("Natal", 2026).date() == date(2026, 12, 25)


def test_fator_da_ocorrencia_passada_entra_pela_metade_so_na_semana_da_data():
    X = _exogenas("2024-01-01", "2025-06-30")
    y = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 3.0})
    dias = pd.date_range("2025-03-01", periods=14)
    lista = ajustes(y, X, dias, DATAS_DE_PRESENTE, **PARAMS)
    assert [a.evento for a in lista] == ["Dia da Mulher"]
    a = lista[0]
    assert a.fator == pytest.approx(3.0, rel=0.05)
    assert a.multiplicador == pytest.approx(1 + 0.5 * (a.fator - 1))
    assert a.anos == (2024,)
    # 08/03/2025 é sábado: de 02 (domingo, fechada) a 08/03, os 6 dias de loja aberta
    assert [d.date() for d in a.dias] == [date(2025, 3, d) for d in range(3, 9)]
    m = multiplicadores(dias, lista)
    assert set(m[dias.isin(list(a.dias))]) == {a.multiplicador}
    assert set(m[~dias.isin(list(a.dias))]) == {1.0}


def test_nao_olha_o_futuro_nem_ocorrencia_sem_as_semanas_seguintes():
    X = _exogenas("2024-01-01", "2025-06-30")
    alta = {data_do_evento("Dia das Mães", 2024): 3.0}
    dias = pd.date_range("2025-05-01", periods=14)
    # a venda conhecida acaba 2 semanas depois do Dia das Mães de 2024: falta a base de depois
    curta = _venda(X, "2024-05-26", alta=alta)
    assert ajustes(curta, X, dias, DATAS_DE_PRESENTE, **PARAMS) == []
    # sem ocorrência passada (a 1ª venda é depois da data de 2024), nenhum ajuste
    sem_passado = _venda(X, "2025-04-30", alta=alta)[pd.Timestamp("2024-06-01"):]
    assert ajustes(sem_passado, X, dias, DATAS_DE_PRESENTE, **PARAMS) == []
    # com o histórico completo, ajusta
    assert [a.evento for a in ajustes(_venda(X, "2025-04-30", alta=alta), X, dias, DATAS_DE_PRESENTE, **PARAMS)] \
        == ["Dia das Mães"]


def test_teto_piso_e_datas_fora_da_lista():
    X = _exogenas("2024-01-01", "2025-06-30")
    dias = pd.date_range("2025-03-01", periods=14)
    explode = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 12.0})
    assert ajustes(explode, X, dias, DATAS_DE_PRESENTE, **PARAMS)[0].multiplicador == 3.0
    cai = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 0.5})
    assert ajustes(cai, X, dias, DATAS_DE_PRESENTE, **PARAMS) == []  # nunca reduz a previsão
    alta = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 3.0})
    assert ajustes(alta, X, dias, ("Natal",), **PARAMS) == []
    assert ajustes(alta, X, dias, (), **PARAMS) == []


def test_dia_de_abertura_excepcional_e_loja_fechada_ficam_sem_ajuste():
    # Dia das Mães de 2025 é domingo: em Itabirito a loja abre (abertura excepcional)
    X = _exogenas("2024-01-01", "2025-06-30", excepcional=("2024-05-12", "2025-05-11"))
    y = _venda(X, "2025-04-30", alta={data_do_evento("Dia das Mães", 2024): 3.0})
    dias = pd.date_range("2025-05-01", periods=14)
    a = ajustes(y, X, dias, DATAS_DE_PRESENTE, **PARAMS)[0]
    assert pd.Timestamp("2025-05-11") not in a.dias  # o dia a exógena já explica
    assert pd.Timestamp("2025-05-04") not in a.dias  # domingo fechado
    assert [d.date() for d in a.dias] == [date(2025, 5, d) for d in range(5, 11)]


def test_fator_junta_as_ultimas_ocorrencias():
    X = _exogenas("2023-01-01", "2026-06-30")
    y = _venda(X, "2026-02-28", alta={data_do_evento("Dia da Mulher", 2023): 9.0,
                                      data_do_evento("Dia da Mulher", 2024): 2.0,
                                      data_do_evento("Dia da Mulher", 2025): 2.0})
    dias = pd.date_range("2026-03-01", periods=14)
    a = ajustes(y, X, dias, DATAS_DE_PRESENTE, fracao=0.5, teto=3.0, ocorrencias=2)[0]
    assert a.anos == (2024, 2025)  # a de 2023 já saiu
    assert a.fator == pytest.approx(2.0, rel=0.05)
