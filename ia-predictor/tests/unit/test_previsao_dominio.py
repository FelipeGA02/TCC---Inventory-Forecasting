"""Testes do dominio da previsao semanal (logica pura)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.domain import previsao as ev
from backend.domain.previsao import (
    COLS_EXOG, CalendarioIncompleto, Especificacao, ajustar, desde_primeira_venda, dias_fechados,
    indice_diario, matriz_exogenas, origens_backtest, parametros, prever,
    produtos_regulares, proxima_data_de_carga, reaplicar, series_da_unidade,
)

T = pd.Timestamp


def _cal(inicio="2026-01-01", fim="2026-03-31", unidade="U"):
    idx = pd.date_range(inicio, fim)
    return pd.DataFrame({"data": idx, "unidade": unidade,
                         "loja_fechada": (idx.weekday == 6).astype(int),
                         "abertura_excepcional": 0})


# ----------------------------------------------------------------- exogenas
def test_matriz_exogenas_tem_dummies_de_dia_e_calendario():
    idx = pd.date_range("2026-01-05", periods=7)              # segunda a domingo
    X = matriz_exogenas(_cal(), "U", idx)
    assert list(X.columns) == COLS_EXOG
    assert X["dia_seg"].tolist() == [1, 0, 0, 0, 0, 0, 0]
    assert X.loc[T("2026-01-11")].drop("loja_fechada").sum() == 0   # domingo e a base
    assert X.loc[T("2026-01-11"), "loja_fechada"] == 1


def test_calendario_incompleto_avisa_em_portugues():
    with pytest.raises(CalendarioIncompleto, match="não cobre 2 dia"):
        matriz_exogenas(_cal(fim="2026-03-31"), "U", pd.date_range("2026-03-30", "2026-04-02"))


def test_dias_fechados_sao_os_domingos():
    assert T("2026-01-04") in dias_fechados(_cal(), "U")
    assert T("2026-01-05") not in dias_fechados(_cal(), "U")


# ----------------------------------------------------------------- series
def test_loja_e_a_soma_das_categorias_e_dia_sem_venda_vira_zero():
    vendas = pd.DataFrame({
        "unidade": ["U", "U", "U", "V"], "data": pd.to_datetime(["2026-01-01", "2026-01-01",
                                                                 "2026-01-03", "2026-01-03"]),
        "categoria": ["A", "B", "A", "A"], "produto_cod": ["1", "2", "1", "9"],
        "qtd_fluxo": [2.0, 3.0, 4.0, 100.0]})
    idx = indice_diario(vendas)
    loja, cats, prods = series_da_unidade(vendas, "U", idx)
    assert loja.tolist() == [5.0, 0.0, 4.0]
    assert np.allclose(cats.sum(axis=1), loja)
    assert list(prods.columns) == ["1", "2"]


def test_desde_primeira_venda_corta_zeros_iniciais_e_futuro():
    s = pd.Series([0, 0, 3, 0, 5, 7], index=pd.date_range("2026-01-01", periods=6), dtype=float)
    assert desde_primeira_venda(s, T("2026-01-06")).tolist() == [3, 0, 5]


def test_produto_regular_exige_adi_baixo_e_historico_longo():
    idx = pd.date_range("2025-01-01", "2025-12-31")
    aberta = pd.Series(idx.weekday != 6, index=idx)
    diario = np.where(aberta, 5.0, 0.0)                         # vende todo dia aberto
    esporadico = np.where(np.arange(len(idx)) % 10 == 0, 5.0, 0.0)
    novo = np.where((idx >= "2025-10-01") & aberta, 5.0, 0.0)   # < 180 dias
    prods = pd.DataFrame({"diario": diario, "esporadico": esporadico, "novo": novo}, index=idx)
    assert produtos_regulares(prods, aberta, T("2026-01-01"), 1.32, 180) == ["diario"]


# ----------------------------------------------------------------- cargas e backtest
def test_proxima_terca():
    assert proxima_data_de_carga(T("2026-03-01"), 1) == T("2026-03-03")
    assert proxima_data_de_carga(T("2026-03-03"), 1) == T("2026-03-03")


def test_origens_do_backtest_no_mesmo_dia_da_semana_e_com_realizado():
    origem, H = T("2026-03-03"), 14
    o = origens_backtest(origem, H, 4)
    assert len(o) == 4 and all(d.weekday() == origem.weekday() for d in o)
    assert o[-1] + pd.Timedelta(days=H - 1) < origem
    assert o[-1] + pd.Timedelta(days=H + 6) >= origem           # e a mais recente possivel


# ----------------------------------------------------------------- metricas
def test_naive_e_escala_do_mase():
    tr = pd.Series(np.tile([1, 2, 3, 4, 5, 6, 0], 3), dtype=float)
    assert ev.naive_sazonal(tr, 9).tolist() == [1, 2, 3, 4, 5, 6, 0, 1, 2]
    assert ev.escala_mase(tr) == 0.0


def test_metricas_e_status():
    d = pd.DataFrame({"origem": [1, 1, 2, 2], "real": [10.0, 10, 10, 10],
                      "previsto": [9.0, 11, 10, 10], "ic_inf": [5.0, 5, 5, 11],
                      "ic_sup": [15.0, 15, 15, 15], "naive": [6.0, 14, 10, 10],
                      "escala": [2.0, 2, 2, 2]})
    m = ev.metricas(d)
    assert m["mase"] == 0.25 and m["erro_relativo_naive"] == 0.25
    assert m["cobertura_ic95_pct"] == 75.0
    assert ev.status(m) == ev.LOW_CONFIDENCE                    # cobertura < 90%
    assert ev.status({**m, "cobertura_ic95_pct": 95.0}) == ev.TRAINED
    assert ev.status({**m, "mase": 1.2, "cobertura_ic95_pct": 95.0}) == ev.LOW_CONFIDENCE


# ----------------------------------------------------------------- SARIMAX
def test_reaplicar_parametros_reproduz_o_ajuste():
    idx = pd.date_range("2025-01-01", periods=200)
    rng = np.random.default_rng(0)
    y = pd.Series(50 + 10 * (idx.weekday < 5) + rng.normal(0, 2, len(idx)), index=idx)
    X = matriz_exogenas(_cal("2025-01-01", "2025-08-31"), "U", idx)
    spec = Especificacao((1, 0, 0), (0, 0, 0, 7))
    res = ajustar(y, X, spec)
    fut = pd.date_range(idx[-1] + pd.Timedelta(days=1), periods=7)
    Xf = matriz_exogenas(_cal("2025-01-01", "2025-08-31"), "U", fut)
    a = prever(res, Xf)
    b = prever(reaplicar(y, X, spec, parametros(res)), Xf)
    assert np.allclose(a.values, b.values)
    assert (a["ic_inf"] <= a["previsto"]).all() and (a["previsto"] <= a["ic_sup"]).all()
