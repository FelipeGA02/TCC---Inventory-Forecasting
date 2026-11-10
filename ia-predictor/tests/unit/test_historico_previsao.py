"""Regra do histórico da previsão (`domain.historico_previsao`): cada dia guarda o registro
mais antigo — do walk-forward, a janela que o previu primeiro; da previsão, os 14 primeiros dias."""
from datetime import date, timedelta

import pandas as pd

from backend.domain.historico_previsao import pontos_a_gravar, pontos_da_serie, serie_com_previsto

INICIO = date(2026, 3, 1)


def _p(dia: date, valor: float, source: str, origem: date | None = None, item: str = "grama") -> dict:
    return {"level": "category", "item": item, "day": dia, "predicted": valor, "lower_95": 0.0,
            "upper_95": valor * 2, "source": source, "origin_date": origem or dia}


def _dias(ini: date, n: int) -> list[date]:
    return [ini + timedelta(days=i) for i in range(n)]


def test_previsao_nova_entra_nos_dias_sem_registro():
    previsao = [_p(d, 10, "forecast", INICIO) for d in _dias(INICIO, 14)]
    novos = pontos_a_gravar(set(), [], previsao)
    assert sorted(p["day"] for p in novos) == _dias(INICIO, 14)


def test_dia_ja_gravado_fica_com_a_previsao_mais_antiga():
    # a previsão de uma semana atrás gravou 22/02..07/03; o treino novo prevê de 01/03 em diante
    gravados = {("category", "grama", d) for d in _dias(date(2026, 2, 22), 14)}
    walk_forward = [_p(d, 99, "walk_forward") for d in _dias(date(2026, 2, 15), 14)]
    previsao = [_p(d, 10, "forecast", INICIO) for d in _dias(INICIO, 14)]
    novos = pontos_a_gravar(gravados, walk_forward, previsao)
    assert sorted(p["day"] for p in novos) == _dias(date(2026, 2, 15), 7) + _dias(date(2026, 3, 8), 7)


def test_mesmo_dia_repetido_fica_com_a_origem_mais_antiga():
    dia = INICIO - timedelta(days=1)
    walk_forward = [_p(dia, 1, "walk_forward", dia), _p(dia, 14, "walk_forward", dia - timedelta(days=13)),
                    _p(dia, 5, "walk_forward", dia - timedelta(days=4))]
    novos = pontos_a_gravar(set(), walk_forward, [])
    assert [(p["day"], p["predicted"]) for p in novos] == [(dia, 14)]


def test_serie_sem_previsto_antes_do_primeiro_treino():
    real = pd.Series([3.0, 4.0, 6.0], index=pd.date_range("2025-03-01", periods=3))
    serie = serie_com_previsto(real, {date(2025, 3, 2): (5.0, 1.0, 9.0, "walk_forward", date(2025, 2, 17), True),
                                      date(2025, 3, 3): (7.0, 2.0, 12.0, "forecast", date(2025, 2, 25), False)})
    assert serie[0] == {"data": "2025-03-01", "real": 3.0, "previsto": None, "inf": None, "sup": None,
                        "fonte": None, "horizonte": None, "loja_fechada": None}
    assert serie[1]["previsto"] == 5.0 and serie[1]["sup"] == 9.0
    assert (serie[1]["fonte"], serie[1]["horizonte"], serie[1]["loja_fechada"]) == ("walk_forward", 14, True)
    assert (serie[2]["fonte"], serie[2]["horizonte"]) == ("forecast", 7)  # previsto 7 dias antes


def _saida_do_treino(fim: pd.Timestamp, origens: int = 3, horizonte: int = 14, dias_previsao: int = 21):
    """`backtest` e `previsao` no formato do `ResultadoSerie` do trainer."""
    ultima = fim - pd.Timedelta(days=horizonte - 1)
    linhas = [{"origem": o, "data": o + pd.Timedelta(days=h), "horizonte": h + 1, "previsto": 10.0 * (h + 1),
               "ic_inf": 1.0, "ic_sup": 99.0, "real": 0.0, "naive": 0.0}
              for o in pd.date_range(ultima - pd.Timedelta(days=origens - 1), ultima) for h in range(horizonte)]
    futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=dias_previsao)
    previsao = pd.DataFrame({"data": futuro, "previsto": 20.0, "ic_inf": 2.0, "ic_sup": 40.0})
    return pd.DataFrame(linhas), previsao


def test_walk_forward_entra_com_a_janela_mais_antiga_de_cada_dia():
    fim = pd.Timestamp("2026-02-28")
    backtest, previsao = _saida_do_treino(fim)
    wf, prev = pontos_da_serie("product", "100", backtest, previsao)
    primeira = date(2026, 2, 13)  # 1ª das 3 origens; a última é 15/02
    assert [p["day"] for p in wf] == _dias(primeira, 16)  # todos os dias até a última venda
    horizontes = [(p["day"] - p["origin_date"]).days + 1 for p in wf]
    assert horizontes == list(range(1, 15)) + [14, 14]  # os primeiros dias só nas primeiras janelas
    assert all(p["origin_date"] == primeira for p in wf[:14])  # a 1ª origem cobre 13/02..26/02
    assert [p["predicted"] for p in wf[-2:]] == [140.0, 140.0]  # 27 e 28/02: h = 14 das origens 2 e 3
    assert {p["source"] for p in wf} == {"walk_forward"}
    # da previsão de 21 dias, só os 14 primeiros
    assert [p["day"] for p in prev] == _dias(date(2026, 3, 1), 14)
    assert {(p["source"], p["origin_date"], p["level"], p["item"]) for p in prev} == {
        ("forecast", date(2026, 3, 1), "product", "100")}
    assert {p["store_closed"] for p in wf + prev} == {None}  # sem o calendário do treino


def test_ponto_guarda_a_loja_fechada_que_o_treino_viu():
    fim = pd.Timestamp("2026-02-28")
    backtest, previsao = _saida_do_treino(fim)
    dias = pd.date_range("2026-01-01", "2026-03-31")
    fechada = pd.Series(dias.weekday == 6, index=dias)  # domingo
    wf, prev = pontos_da_serie("category", "grama", backtest, previsao, fechada=fechada)
    assert all(p["store_closed"] is (p["day"].weekday() == 6) for p in prev)  # 01 e 08/03 são domingo
    assert next(p for p in wf if p["day"] == date(2026, 2, 22))["store_closed"] is True


def test_ponto_guarda_o_fator_da_data_comemorativa():
    """ADR-019: o multiplicador que entrou no previsto vai para `event_factor`; 1 vira nulo."""
    fim = pd.Timestamp("2026-02-28")
    backtest, previsao = _saida_do_treino(fim, dias_previsao=14)
    previsao["fator"] = [2.0] * 7 + [1.0] * 7
    backtest["fator"] = 1.0
    wf, prev = pontos_da_serie("category", "flores-de-corte", backtest, previsao)
    assert [p["event_factor"] for p in prev] == [2.0] * 7 + [None] * 7
    assert {p["event_factor"] for p in wf} == {None}


def _treinar(gravado: dict, walk_forward: list[dict], previsao: list[dict]) -> None:
    """O que `servico_previsao.gravar_historico` faz no banco, num dict (chave → ponto)."""
    for p in pontos_a_gravar(set(gravado), walk_forward, previsao):
        gravado[(p["level"], p["item"], p["day"])] = p


def test_treino_semanal_mantem_a_previsao_mais_antiga_de_cada_dia():
    gravado = {}
    t1, t2 = date(2026, 3, 1), date(2026, 3, 10)  # o 2º treino 9 dias depois
    _treinar(gravado, [], [_p(d, 10, "forecast", t1) for d in _dias(t1, 14)])
    _treinar(gravado, [_p(d, 99, "walk_forward", d - timedelta(days=13)) for d in _dias(t2 - timedelta(days=69), 69)],
             [_p(d, 20, "forecast", t2) for d in _dias(t2, 14)])
    valores = {k[2]: p["predicted"] for k, p in gravado.items()}
    assert [valores[d] for d in _dias(t1, 14)] == [10] * 14  # a 1ª previsão inteira fica
    assert [valores[d] for d in _dias(t1 + timedelta(days=14), 9)] == [20] * 9  # o resto da 2ª
    assert min(valores) == t2 - timedelta(days=69) and valores[t1 - timedelta(days=1)] == 99
