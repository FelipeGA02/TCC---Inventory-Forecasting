"""Dias de venda que faltariam na base depois de uma planilha (`domain.etl.cobertura`).

Datas de outubro de 2026: 20/10 é terça e 25/10 é domingo (loja fechada no padrão).
"""
from datetime import date, timedelta

from backend.domain.etl.cobertura import dias_faltando


def _d(dia: int, mes: int = 10) -> date:
    return date(2026, mes, dia)


def _dias(ini: date, fim: date) -> set[date]:
    return {ini + timedelta(days=i) for i in range((fim - ini).days + 1)}


def _abertos(ini: date, fim: date) -> set[date]:
    return {d for d in _dias(ini, fim) if d.weekday() != 6}


def test_tres_dias_entre_a_base_e_a_planilha():
    f, = dias_faltando({"jc": _abertos(_d(24), _d(31))}, {"jc": _d(20)}, {}, {})
    assert f.dias == [_d(21), _d(22), _d(23)]
    assert f.intervalos == [(_d(21), _d(23))]
    assert f.ultima_na_base == _d(20) and f.na_planilha == (_d(24), _d(31))


def test_domingo_entre_a_base_e_a_planilha_nao_falta():
    assert dias_faltando({"jc": _abertos(_d(26), _d(31))}, {"jc": _d(24)}, {}, {}) == []


def test_domingo_no_meio_nao_separa_o_intervalo():
    f, = dias_faltando({"jc": _abertos(_d(27), _d(31))}, {"jc": _d(23)}, {}, {})
    assert f.dias == [_d(24), _d(26)] and f.intervalos == [(_d(24), _d(26))]


def test_calendario_da_loja_vale_sobre_o_padrao():
    calendario = {"ita": {_d(22): True, _d(25): False}}  # feriado na quinta; abertura no domingo
    f, = dias_faltando({"ita": _abertos(_d(26), _d(31))}, {"ita": _d(20)}, {}, calendario)
    assert f.dias == [_d(21), _d(23), _d(24), _d(25)]
    assert f.intervalos == [(_d(21), _d(25))]  # o feriado no meio não separa


def test_loja_que_nao_esta_na_planilha_fica_para_tras():
    faltando = dias_faltando({"jc": _abertos(_d(21), _d(31))}, {"jc": _d(20), "ita": _d(20)}, {}, {})
    assert [f.unit_id for f in faltando] == ["ita"]
    assert faltando[0].na_planilha is None and len(faltando[0].dias) == 10  # 21 a 31/10 sem o domingo


def test_dia_sem_venda_dentro_da_planilha():
    planilha = {"jc": _abertos(_d(1), _d(10)) - {_d(5)}}
    f, = dias_faltando(planilha, {}, {}, {})  # base vazia: só o período da planilha
    assert f.dias == [_d(5)] and f.ultima_na_base is None
    # o dia já está na base: não falta
    assert dias_faltando(planilha, {"jc": _d(31)}, {"jc": {_d(5)}}, {}) == []


def test_planilha_antiga_nao_cobra_os_dias_depois_dela():
    planilha = {"jc": _abertos(_d(1, 9), _d(15, 9))}
    assert dias_faltando(planilha, {"jc": _d(31)}, {}, {}) == []


def test_planilha_vazia():
    assert dias_faltando({}, {"jc": _d(20)}, {}, {}) == []
