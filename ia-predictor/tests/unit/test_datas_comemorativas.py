"""Fator das datas comemorativas (`backend/domain/models/datas_comemorativas.py`, ADR-019)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from backend.domain.models.datas_comemorativas import (
    DATAS_DE_PRESENTE,
    DATAS_DE_QUEDA,
    DATAS_FLORES_DE_CORTE,
    REGRA_ALTA,
    REGRA_QUEDA,
    Regra,
    ajustes,
    data_do_evento,
    dias_da_janela,
    multiplicadores,
)



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
    assert data_do_evento("Ano Novo", 2026).date() == date(2026, 1, 1)


def test_ano_novo_pega_a_semana_antes_do_1o_de_janeiro_do_ano_seguinte():
    """Previsão de dezembro: a semana do Ano Novo é a de 26 a 31/12, de uma data do ano seguinte."""
    X = _exogenas("2024-01-01", "2026-01-31")
    for ano in (2024, 2025, 2026):
        X.loc[pd.Timestamp(f"{ano}-01-01"), "loja_fechada"] = 1.0
    y = _venda(X, "2025-12-17", alta={data_do_evento("Ano Novo", 2025): 3.0})
    dias = pd.date_range("2025-12-18", periods=14)
    a = next(a for a in ajustes(y, X, dias, DATAS_FLORES_DE_CORTE, REGRA_ALTA) if a.evento == "Ano Novo")
    assert a.data == pd.Timestamp("2026-01-01")
    assert a.anos == (2025,)
    assert a.fator == pytest.approx(3.0, rel=0.05)
    # 28/12/2025 é domingo (fechada) e 1º/01 é feriado: ficam de fora
    assert [d.date() for d in a.dias] == [date(2025, 12, d) for d in (26, 27, 29, 30, 31)]
    assert "Ano Novo" not in DATAS_DE_PRESENTE


def test_fator_da_ocorrencia_passada_entra_pela_metade_so_na_semana_da_data():
    X = _exogenas("2024-01-01", "2025-06-30")
    y = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 3.0})
    dias = pd.date_range("2025-03-01", periods=14)
    lista = ajustes(y, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA)
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
    assert ajustes(curta, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA) == []
    # sem ocorrência passada (a 1ª venda é depois da data de 2024), nenhum ajuste
    sem_passado = _venda(X, "2025-04-30", alta=alta)[pd.Timestamp("2024-06-01"):]
    assert ajustes(sem_passado, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA) == []
    # com o histórico completo, ajusta
    assert [a.evento for a in ajustes(_venda(X, "2025-04-30", alta=alta), X, dias, DATAS_DE_PRESENTE, REGRA_ALTA)] \
        == ["Dia das Mães"]


def test_teto_piso_e_datas_fora_da_lista():
    X = _exogenas("2024-01-01", "2025-06-30")
    dias = pd.date_range("2025-03-01", periods=14)
    explode = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 12.0})
    assert ajustes(explode, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA)[0].multiplicador == 3.0
    cai = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 0.5})
    assert ajustes(cai, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA) == []  # nunca reduz a previsão
    alta = _venda(X, "2025-02-28", alta={data_do_evento("Dia da Mulher", 2024): 3.0})
    assert ajustes(alta, X, dias, ("Natal",), REGRA_ALTA) == []
    assert ajustes(alta, X, dias, (), REGRA_ALTA) == []


def test_dia_de_abertura_excepcional_e_loja_fechada_ficam_sem_ajuste():
    # Dia das Mães de 2025 é domingo: em Itabirito a loja abre (abertura excepcional)
    X = _exogenas("2024-01-01", "2025-06-30", excepcional=("2024-05-12", "2025-05-11"))
    y = _venda(X, "2025-04-30", alta={data_do_evento("Dia das Mães", 2024): 3.0})
    dias = pd.date_range("2025-05-01", periods=14)
    a = ajustes(y, X, dias, DATAS_DE_PRESENTE, REGRA_ALTA)[0]
    assert pd.Timestamp("2025-05-11") not in a.dias  # o dia a exógena já explica
    assert pd.Timestamp("2025-05-04") not in a.dias  # domingo fechado
    assert [d.date() for d in a.dias] == [date(2025, 5, d) for d in range(5, 11)]


def test_fator_junta_as_ultimas_ocorrencias():
    X = _exogenas("2023-01-01", "2026-06-30")
    y = _venda(X, "2026-02-28", alta={data_do_evento("Dia da Mulher", 2023): 9.0,
                                      data_do_evento("Dia da Mulher", 2024): 2.0,
                                      data_do_evento("Dia da Mulher", 2025): 2.0})
    dias = pd.date_range("2026-03-01", periods=14)
    a = ajustes(y, X, dias, DATAS_DE_PRESENTE, Regra(fracao=0.5, piso=1.0, teto=3.0, ocorrencias=2))[0]
    assert a.anos == (2024, 2025)  # a de 2023 já saiu
    assert a.fator == pytest.approx(2.0, rel=0.05)


def _exogenas_fim_de_ano(inicio: str, fim: str) -> pd.DataFrame:
    X = _exogenas(inicio, fim)
    for ano in range(X.index.min().year, X.index.max().year + 1):
        for dia in (f"{ano}-01-01", f"{ano}-12-25"):
            if pd.Timestamp(dia) in X.index:
                X.loc[pd.Timestamp(dia), "loja_fechada"] = 1.0
    return X


def test_queda_inteira_so_quando_as_2_ultimas_ocorrencias_cairam():
    """ADR-019, queda: a de 26 a 31/12 entra inteira (piso 0,2) se as 2 últimas ocorrências
    ficaram em até 0,8 de uma semana comum."""
    X = _exogenas_fim_de_ano("2024-01-01", "2027-01-31")
    dias = pd.date_range("2026-12-18", periods=14)
    ano_novo = lambda ano: data_do_evento("Ano Novo", ano)  # noqa: E731
    caiu = _venda(X, "2026-12-17", alta={ano_novo(2025): 0.4, ano_novo(2026): 0.4})
    a = next(a for a in ajustes(caiu, X, dias, DATAS_DE_QUEDA, REGRA_QUEDA) if a.evento == "Ano Novo")
    assert a.data == pd.Timestamp("2027-01-01") and a.anos == (2025, 2026)
    assert a.multiplicador == pytest.approx(a.fator) and a.fator == pytest.approx(0.4, rel=0.1)
    assert [d.date() for d in a.dias] == [date(2026, 12, d) for d in (26, 28, 29, 30, 31)]  # 27 é domingo
    # caiu num ano só: sem ajuste
    um_ano = _venda(X, "2026-12-17", alta={ano_novo(2025): 0.4})
    assert ajustes(um_ano, X, dias, DATAS_DE_QUEDA, REGRA_QUEDA) == []
    # uma ocorrência passada só (a venda começa em 2025): sem ajuste
    curta = caiu[pd.Timestamp("2025-03-01"):]
    assert ajustes(curta, X, dias, DATAS_DE_QUEDA, REGRA_QUEDA) == []
    # a semana que quase não vende fica no piso
    zerou = _venda(X, "2026-12-17", alta={ano_novo(2025): 0.0, ano_novo(2026): 0.0})
    assert ajustes(zerou, X, dias, DATAS_DE_QUEDA, REGRA_QUEDA)[0].multiplicador == REGRA_QUEDA.piso
    # a regra da queda nunca aumenta a previsão
    subiu = _venda(X, "2026-12-17", alta={ano_novo(2025): 0.5, ano_novo(2026): 3.0})
    assert ajustes(subiu, X, dias, DATAS_DE_QUEDA, REGRA_QUEDA) == []


def test_dia_do_trabalho_pela_regra():
    assert data_do_evento("Dia do Trabalho", 2026).date() == date(2026, 5, 1)
    assert "Dia do Trabalho" in DATAS_DE_QUEDA and "Dia do Trabalho" not in DATAS_FLORES_DE_CORTE
