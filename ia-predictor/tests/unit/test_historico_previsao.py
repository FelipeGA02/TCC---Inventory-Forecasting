"""Regra do histórico da previsão (`domain.historico_previsao`)."""
from datetime import date, timedelta

import pandas as pd

from backend.domain.historico_previsao import pontos_a_gravar, pontos_da_serie, serie_com_previsto

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


def test_serie_sem_previsto_antes_do_primeiro_treino():
    real = pd.Series([3.0, 4.0, 6.0], index=pd.date_range("2025-03-01", periods=3))
    serie = serie_com_previsto(real, {date(2025, 3, 2): (5.0, 1.0, 9.0, "walk_forward", date(2025, 3, 2), True),
                                      date(2025, 3, 3): (7.0, 2.0, 12.0, "forecast", date(2025, 2, 25), False)})
    assert serie[0] == {"data": "2025-03-01", "real": 3.0, "previsto": None, "inf": None, "sup": None,
                        "fonte": None, "horizonte": None, "loja_fechada": None}
    assert serie[1]["previsto"] == 5.0 and serie[1]["sup"] == 9.0
    assert (serie[1]["fonte"], serie[1]["horizonte"], serie[1]["loja_fechada"]) == ("walk_forward", 1, True)
    assert (serie[2]["fonte"], serie[2]["horizonte"]) == ("forecast", 7)  # previsto 7 dias antes


def _saida_do_treino(fim: pd.Timestamp, origens: int = 3, horizonte: int = 14):
    """`backtest`, `complemento` e `previsao` no formato do `ResultadoSerie` do trainer."""
    ultima = fim - pd.Timedelta(days=horizonte - 1)
    linhas = [{"origem": o, "data": o + pd.Timedelta(days=h), "horizonte": h + 1, "previsto": 10.0 * (h + 1),
               "ic_inf": 1.0, "ic_sup": 99.0, "real": 0.0, "naive": 0.0}
              for o in pd.date_range(ultima - pd.Timedelta(days=origens - 1), ultima) for h in range(horizonte)]
    dias = pd.date_range(ultima + pd.Timedelta(days=1), fim)
    complemento = pd.DataFrame({"origem": dias, "data": dias, "previsto": 5.0, "ic_inf": 1.0, "ic_sup": 9.0})
    futuro = pd.date_range(fim + pd.Timedelta(days=1), periods=horizonte)
    previsao = pd.DataFrame({"data": futuro, "previsto": 20.0, "ic_inf": 2.0, "ic_sup": 40.0})
    return pd.DataFrame(linhas), complemento, previsao


def test_walk_forward_entra_so_com_o_primeiro_dia_de_cada_janela():
    fim = pd.Timestamp("2026-02-28")
    backtest, complemento, previsao = _saida_do_treino(fim)
    wf, prev = pontos_da_serie("product", "100", backtest, complemento, previsao)
    assert [p["day"] for p in wf] == _dias(date(2026, 2, 13), 16)  # 3 origens + 13 do complemento
    assert all(p["origin_date"] == p["day"] and p["source"] == "walk_forward" for p in wf)
    assert {p["predicted"] for p in wf[:3]} == {10.0}  # h = 1 das origens completas, não h = 2..14
    assert {p["predicted"] for p in wf[3:]} == {5.0}
    assert [p["day"] for p in prev] == _dias(date(2026, 3, 1), 14)
    assert {(p["source"], p["origin_date"], p["level"], p["item"]) for p in prev} == {
        ("forecast", date(2026, 3, 1), "product", "100")}
    assert {p["store_closed"] for p in wf + prev} == {None}  # sem o calendário do treino


def test_ponto_guarda_a_loja_fechada_que_o_treino_viu():
    fim = pd.Timestamp("2026-02-28")
    backtest, complemento, previsao = _saida_do_treino(fim)
    dias = pd.date_range("2026-01-01", "2026-03-31")
    fechada = pd.Series(dias.weekday == 6, index=dias)  # domingo
    wf, prev = pontos_da_serie("category", "grama", backtest, complemento, previsao, fechada=fechada)
    assert all(p["store_closed"] is (p["day"].weekday() == 6) for p in prev)  # 01 e 08/03 são domingo
    assert next(p for p in wf if p["day"] == date(2026, 2, 22))["store_closed"] is True


def test_ponto_guarda_o_fator_da_data_comemorativa():
    """ADR-019: o multiplicador que entrou no previsto vai para `event_factor`; 1 vira nulo."""
    fim = pd.Timestamp("2026-02-28")
    backtest, complemento, previsao = _saida_do_treino(fim)
    previsao["fator"] = [2.0] * 7 + [1.0] * 7
    backtest["fator"] = 1.0
    wf, prev = pontos_da_serie("category", "flores-de-corte", backtest, complemento, previsao)
    assert [p["event_factor"] for p in prev] == [2.0] * 7 + [None] * 7
    assert {p["event_factor"] for p in wf} == {None}  # o complemento sem a coluna também


def _treinar(gravado: dict, inicio: date, walk_forward: list[dict], previsao: list[dict]) -> None:
    """O que `servico_previsao.gravar_historico` faz no banco, num dict (chave → ponto)."""
    for k in [k for k in gravado if k[2] >= inicio]:
        del gravado[k]
    for p in pontos_a_gravar(set(gravado), walk_forward, previsao, inicio):
        gravado[(p["level"], p["item"], p["day"])] = p


def test_treino_semanal_congela_os_dias_ate_o_inicio_seguinte():
    gravado = {}
    t1, t2 = date(2026, 3, 1), date(2026, 3, 10)  # o 2º treino 9 dias depois
    _treinar(gravado, t1, [], [_p(d, 10, "forecast") for d in _dias(t1, 14)])
    _treinar(gravado, t2, [_p(d, 99, "walk_forward") for d in _dias(t2 - timedelta(days=69), 69)],
             [_p(d, 20, "forecast") for d in _dias(t2, 14)])
    valores = {k[2]: p["predicted"] for k, p in gravado.items()}
    assert [valores[d] for d in _dias(t1, 9)] == [10] * 9  # congelados
    assert [valores[d] for d in _dias(t2, 14)] == [20] * 14
    assert min(valores) == t2 - timedelta(days=69) and valores[t1 - timedelta(days=1)] == 99

