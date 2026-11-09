"""Treino de uma série (`backend/domain/models/trainer.py`) sobre dados sintéticos."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.domain.features.exogenous import COLUNAS_EXOGENAS, matriz_exogena
from backend.domain.models import evaluator, forecaster, trainer
from backend.domain.models.trainer import (
    NIVEL_CATEGORIA,
    NIVEL_PRODUTO,
    ConfigTreino,
    motivo_inelegivel,
    origens_complemento,
    origens_walk_forward,
    treinar_serie,
)

FIM = pd.Timestamp("2026-02-28")
RAPIDA = ConfigTreino(janela_dias=60, origens=4, grade_pq=(0, 1), grade_PQ=(0,), min_historico_dias=30,
                      min_dias_com_venda=10)


def _calendario(inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    dias = pd.date_range(inicio, fim, freq="D")
    return pd.DataFrame({"loja_fechada": (dias.weekday == 6).astype(int), "abertura_excepcional": 0}, index=dias)


def _serie(dias: int = 200, semente: int = 7) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """Venda com perfil semanal (pico ter–qui, domingo fechado) e ruído."""
    rng = np.random.default_rng(semente)
    idx = pd.date_range(FIM - pd.Timedelta(days=dias - 1), FIM, freq="D")
    perfil = np.array([40, 60, 65, 62, 45, 25, 0.0])
    y = pd.Series(np.clip(perfil[idx.weekday] + rng.normal(0, 6, len(idx)), 0, None), index=idx)
    y[idx.weekday == 6] = 0.0
    X, _ = matriz_exogena(pd.date_range(idx[0], FIM + pd.Timedelta(days=14), freq="D"),
                          _calendario(idx[0], FIM + pd.Timedelta(days=14)))
    return y, X, X["loja_fechada"] == 0


def test_origens_andam_um_dia_e_deixam_o_horizonte_a_frente():
    cfg = ConfigTreino(origens=56, horizonte=14)
    origens = origens_walk_forward(FIM, cfg)
    assert len(origens) == 56
    assert origens[-1] == FIM - pd.Timedelta(days=13)  # a última ainda tem 14 dias de venda conhecida
    assert all((b - a).days == 1 for a, b in zip(origens, origens[1:]))
    # o complemento vai da origem seguinte até o último dia com venda
    assert origens_complemento(FIM, cfg) == list(pd.date_range(FIM - pd.Timedelta(days=12), FIM))


def test_treina_com_m7_d0_D0_e_preve_14_dias():
    y, X, aberta = _serie()
    r = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_TREINADO, r.motivo
    assert r.ordem[1] == 0 and r.ordem_sazonal[1] == 0 and r.ordem_sazonal[3] == 7
    assert list(r.previsao["data"]) == list(pd.date_range(FIM + pd.Timedelta(days=1), periods=14))
    assert (r.previsao[["previsto", "ic_inf", "ic_sup"]] >= 0).all().all()
    domingo = r.previsao[r.previsao["data"].dt.weekday == 6]
    assert (domingo[["previsto", "ic_inf", "ic_sup"]] == 0).all().all()  # loja fechada no domingo
    assert r.backtest["origem"].nunique() == RAPIDA.origens
    assert set(r.backtest["horizonte"]) == set(range(1, 15))
    assert r.metricas["mase"] is not None and r.metricas["dias_avaliados"] > 0


def test_previsao_final_vai_alem_do_horizonte_do_walk_forward():
    """ADR-021: o walk-forward (status) usa `horizonte`; a previsão final, `horizonte_previsao`."""
    y, _, _ = _serie()
    X, _ = matriz_exogena(pd.date_range(y.index[0], FIM + pd.Timedelta(days=91), freq="D"),
                          _calendario(y.index[0], FIM + pd.Timedelta(days=91)))
    cfg = ConfigTreino(**{**RAPIDA.__dict__, "horizonte_previsao": 91})
    assert cfg.dias_previsao == 91 and RAPIDA.dias_previsao == RAPIDA.horizonte == 14
    r = treinar_serie(y, X, X["loja_fechada"] == 0, cfg, NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_TREINADO, r.motivo
    assert list(r.previsao["data"]) == list(pd.date_range(FIM + pd.Timedelta(days=1), periods=91))
    assert set(r.backtest["horizonte"]) == set(range(1, 15))  # o teste continua com h = 14
    # mesmo modelo, mesmos dados: os 14 primeiros dias são os da previsão de 14
    curta = treinar_serie(y, X, X["loja_fechada"] == 0, RAPIDA, NIVEL_CATEGORIA)
    np.testing.assert_allclose(r.previsao["previsto"].values[:14], curta.previsao["previsto"].values)
    assert r.metricas == curta.metricas


def test_d_escolhido_pelo_walk_forward():
    """ADR-020: com `d_candidatos`, cada d tem a sua ordem e o seu walk-forward; fica o que errou
    menos, e o backtest, as métricas e a previsão são os dele."""
    y, X, aberta = _serie()
    rng = np.random.default_rng(3)
    nivel = pd.Series(np.cumsum(rng.normal(0, 4, len(y))), index=y.index)  # nível que anda
    y = (y + nivel.where(y > 0, 0)).clip(lower=0)
    cfg = ConfigTreino(**{**RAPIDA.__dict__, "d_candidatos": (0, 1)})
    r = treinar_serie(y, X, aberta, cfg, NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_TREINADO, r.motivo
    sel = r.metricas["selecao_d"]
    assert set(sel) == {"0", "1"} and all(v["ordem"][0][1] == int(d) for d, v in sel.items())
    d = r.metricas["d_escolhido"]
    assert r.ordem[1] == d and sel[str(d)]["mae"] == min(v["mae"] for v in sel.values())
    assert r.metricas["mae"] == sel[str(d)]["mae"]
    # cada um sozinho dá o mesmo walk-forward do candidato
    so = treinar_serie(y, X, aberta, ConfigTreino(**{**RAPIDA.__dict__, "d": d}), NIVEL_CATEGORIA)
    assert so.metricas["mae"] == r.metricas["mae"] and so.ordem == r.ordem
    np.testing.assert_allclose(so.previsao["previsto"].values, r.previsao["previsto"].values)


def test_d_candidato_que_nao_ajusta_fica_de_fora(monkeypatch):
    y, X, aberta = _serie()
    original = trainer.selecionar_ordem

    def falha_com_d1(*a, **k):
        if k["d"] == 1:
            raise trainer.NenhumaOrdemConvergiu()
        return original(*a, **k)

    monkeypatch.setattr(trainer, "selecionar_ordem", falha_com_d1)
    r = treinar_serie(y, X, aberta, ConfigTreino(**{**RAPIDA.__dict__, "d_candidatos": (0, 1)}), NIVEL_CATEGORIA)
    assert r.ordem[1] == 0 and r.metricas["d_escolhido"] == 0 and set(r.metricas["selecao_d"]) == {"0"}


def test_d1_treina_sem_constante():
    """ADR-020: com d = 1 a constante viraria tendência, então o modelo fica sem ela."""
    y, X, aberta = _serie()
    r = treinar_serie(y, X, aberta, ConfigTreino(**{**RAPIDA.__dict__, "d": 1}), NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_TREINADO, r.motivo
    assert r.ordem[1] == 1 and "intercept" not in r.coeficientes
    assert (r.previsao[["previsto", "ic_inf", "ic_sup"]] >= 0).all().all()


def test_dia_de_loja_fechada_tem_previsao_e_faixa_zeradas():
    """O SARIMAX só desconta um valor fixo no dia fechado: depois de um sábado forte, os
    termos MA deixavam previsto e faixa acima de zero no domingo (Flores de corte, 01/03)."""
    class _Previsao:
        predicted_mean = np.array([30.0, 7.2, 40.0])
        def conf_int(self, alpha):
            return np.array([[10.0, 50.0], [0.0, 117.8], [-5.0, 90.0]])

    class _Resultado:
        def get_forecast(self, passos, exog):
            return _Previsao()

    dias = pd.date_range("2026-02-28", periods=3)  # sábado, domingo (fechada), segunda
    X = pd.DataFrame({"loja_fechada": [0.0, 1.0, 0.0], "abertura_excepcional": 0.0}, index=dias)
    prev, inf, sup = forecaster.prever(_Resultado(), X)
    assert list(prev) == [30.0, 0.0, 40.0]
    assert list(inf) == [10.0, 0.0, 0.0]  # o limite negativo continua cortado em zero
    assert list(sup) == [50.0, 0.0, 90.0]


def test_janela_deslizante_e_ordem_sem_olhar_o_periodo_avaliado(monkeypatch):
    y, X, aberta = _serie()
    ajustes, escolha = [], {}
    original_ajustar, original_selecionar = trainer.ajustar, trainer.selecionar_ordem

    def espiao_ajustar(serie, *a, **k):
        ajustes.append(serie.index)
        return original_ajustar(serie, *a, **k)

    def espiao_selecionar(serie, *a, **k):
        escolha["ultimo_dia"] = serie.index.max()
        return original_selecionar(serie, *a, **k)

    monkeypatch.setattr(trainer, "ajustar", espiao_ajustar)
    monkeypatch.setattr(trainer, "selecionar_ordem", espiao_selecionar)
    treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)

    origens = origens_walk_forward(FIM, RAPIDA) + origens_complemento(FIM, RAPIDA)
    assert escolha["ultimo_dia"] < origens[0]  # AIC só com dados anteriores à 1ª origem
    walk = ajustes[:-1]  # o último é a previsão final
    assert len(walk) == RAPIDA.origens + 13  # as completas e as do complemento
    for janela, origem in zip(walk, origens):
        assert len(janela) == RAPIDA.janela_dias  # deslizante: tamanho fixo
        assert janela.max() == origem - pd.Timedelta(days=1)  # termina na véspera da origem
    assert ajustes[-1].max() == FIM and len(ajustes[-1]) == RAPIDA.janela_dias


def test_primeiro_dia_das_janelas_chega_ate_a_ultima_venda_fora_das_metricas():
    y, X, aberta = _serie()
    r = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)
    assert list(r.complemento["data"]) == list(pd.date_range(FIM - pd.Timedelta(days=12), FIM))
    assert (r.complemento["origem"] == r.complemento["data"]).all()  # só h = 1
    assert (r.complemento[["previsto", "ic_inf", "ic_sup"]] >= 0).all().all()
    # o 1º dia das janelas completas e o do complemento: um previsto por dia, sem buraco até FIM
    h1 = list(r.backtest.loc[r.backtest["horizonte"] == 1, "data"]) + list(r.complemento["data"])
    assert h1 == list(pd.date_range(origens_walk_forward(FIM, RAPIDA)[0], FIM))
    # as métricas são só das origens completas
    assert r.backtest["origem"].nunique() == RAPIDA.origens and r.metricas["origens"] == RAPIDA.origens


def test_produto_que_quase_nao_vende_fica_sem_modelo():
    y, X, aberta = _serie()
    y[:] = 0.0
    y.iloc[[-3, -20, -40]] = 5.0  # 3 dias com venda, todos dentro da janela de 60
    r = treinar_serie(y, X, aberta, RAPIDA, NIVEL_PRODUTO)
    assert r.status == evaluator.STATUS_DADOS_INSUFICIENTES
    assert "vendeu em 3 dia(s)" in r.motivo
    assert r.previsao is None and r.backtest is None


def test_historico_curto_fica_sem_modelo():
    y, X, aberta = _serie(dias=40)
    assert "histórico de" in motivo_inelegivel(y, RAPIDA, NIVEL_CATEGORIA)


def test_falha_no_ajuste_vira_erro_sem_derrubar(monkeypatch):
    y, X, aberta = _serie()

    def quebra(*_a, **_k):
        raise np.linalg.LinAlgError("matriz singular")

    monkeypatch.setattr(trainer, "ajustar", quebra)
    r = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_ERRO
    assert r.origens_com_falha == RAPIDA.origens


def test_ajuste_final_registra_coeficientes_e_diagnostico_dos_residuos():
    y, X, aberta = _serie()
    r = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)
    assert {"intercept", "loja_fechada", "dia_seg", "sigma2"} <= set(r.coeficientes)
    assert set(r.diagnostico) == {"ljung_box_p", "shapiro_p"}
    assert all(0 <= v <= 1 for v in r.diagnostico.values())


def test_diagnostico_aponta_residuo_correlacionado():
    passeio = pd.Series(np.cumsum(np.random.default_rng(3).normal(size=300)))  # cada valor puxa o seguinte
    ruido = pd.Series(np.random.default_rng(3).normal(size=300))
    assert evaluator.diagnostico_residuos(passeio, descartar=7)["ljung_box_p"] <= evaluator.P_DIAGNOSTICO
    assert evaluator.diagnostico_residuos(ruido, descartar=7)["ljung_box_p"] > evaluator.P_DIAGNOSTICO
    assert evaluator.diagnostico_residuos(pd.Series([1.0] * 30), descartar=7) == {"ljung_box_p": None,
                                                                                   "shapiro_p": None}


def test_erro_no_total_de_14_dias_e_origens_que_vencem_a_naive():
    pontos = pd.DataFrame({
        "origem": [1, 1, 2, 2], "previsto": [10.0, 10.0, 10.0, 10.0], "ic_inf": [0.0] * 4, "ic_sup": [20.0] * 4,
        "real": [12.0, 12.0, 5.0, 5.0], "naive": [12.0, 12.0, 20.0, 20.0], "escala": [1.0] * 4, "aberta": [True] * 4})
    m = evaluator.metricas_walk_forward(pontos)
    # janela 1: previu 20, vendeu 24; janela 2: previu 20, vendeu 10 → (4 + 10) / 34
    assert m["erro_total_14d_pct"] == round(14 / 34 * 100, 1)
    assert m["origens_vence_naive"] == 1  # só a janela 2 erra menos que a naïve


def test_metricas_ignoram_dia_fechado():
    pontos = pd.DataFrame({
        "origem": [1, 1, 1], "previsto": [10.0, 10.0, 0.0], "ic_inf": [5.0, 5.0, 0.0], "ic_sup": [15.0, 15.0, 0.0],
        "real": [12.0, 30.0, 0.0], "naive": [8.0, 8.0, 0.0], "escala": [4.0, 4.0, 4.0], "aberta": [True, True, False]})
    m = evaluator.metricas_walk_forward(pontos)
    assert m["dias_avaliados"] == 2
    assert m["mae"] == 11.0 and m["cobertura_ic95_pct"] == 50.0


def test_serie_que_ajusta_tem_previsao_mesmo_errando_mais_que_a_naive():
    """Sem classificação de confiança: MASE e cobertura ficam nas métricas, não no status."""
    idx = pd.date_range("2025-01-01", periods=400, freq="D")
    rng = np.random.default_rng(3)
    y = pd.Series(rng.poisson(5, len(idx)).astype(float), index=idx)  # ruído puro: a naïve empata
    fut = pd.date_range(idx[0], periods=len(idx) + 30, freq="D")
    X = pd.DataFrame({"seg": (fut.dayofweek == 0).astype(float)}, index=fut)
    aberta = pd.Series(True, index=fut)
    cfg = ConfigTreino(origens=4, grade_pq=(0,), grade_PQ=(0,), min_historico_dias=180)
    r = treinar_serie(y, X, aberta, cfg, NIVEL_CATEGORIA)
    assert r.status == evaluator.STATUS_TREINADO and r.previsao is not None
    assert "mase" in r.metricas and "cobertura_ic95_pct" in r.metricas


def test_fator_das_datas_multiplica_so_a_semana_da_data():
    """ADR-019: a semana do Dia da Mulher de 2025 vendeu 3× o normal; a previsão de 01 a
    14/03/2026 sai multiplicada de segunda a sábado antes do dia 08 (domingo, loja fechada)."""
    y, X, aberta = _serie(dias=430)
    y[pd.date_range("2025-03-03", "2025-03-08")] *= 3.0
    sem = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA)
    com = treinar_serie(y, X, aberta, RAPIDA, NIVEL_CATEGORIA, com_fator=True)
    assert set(sem.previsao["fator"]) == {1.0} and sem.ajustes == []

    semana = com.previsao["data"].between("2026-03-02", "2026-03-07")
    assert com.previsao.loc[semana, "fator"].between(1.8, 2.1).all()  # 1 + (≈3 − 1) / 2
    assert set(com.previsao.loc[~semana, "fator"]) == {1.0}
    for c in ("previsto", "ic_inf", "ic_sup"):
        assert np.allclose(com.previsao[c], sem.previsao[c] * com.previsao["fator"])
    assert [(a["evento"], a["data"], a["anos"]) for a in com.ajustes] == [("Dia da Mulher", "2026-03-08", [2025])]
    # o walk-forward e o complemento (fevereiro) não pegam a semana da data
    assert set(com.backtest["fator"]) == {1.0} and set(com.complemento["fator"]) == {1.0}
    assert com.metricas == sem.metricas


def test_dia_fora_do_calendario_usa_o_padrao_da_loja():
    dias = pd.date_range("2026-03-01", "2026-03-10", freq="D")  # 01/03/2026 é domingo
    X, faltando = matriz_exogena(dias, _calendario(dias[0], pd.Timestamp("2026-03-04")))
    assert list(X.columns) == COLUNAS_EXOGENAS
    assert len(faltando) == 6
    assert X.loc["2026-03-08", "loja_fechada"] == 1.0  # domingo fora do calendário
    assert X.loc["2026-03-09", "loja_fechada"] == 0.0


def test_dominio_nao_importa_framework_nem_banco():
    """Regra Inviolável nº 1: `backend/domain/` não importa FastAPI, SQLAlchemy nem APScheduler."""
    proibidos = {"fastapi", "sqlalchemy", "apscheduler", "starlette"}
    raiz = Path(__file__).resolve().parents[2] / "backend" / "domain"
    for arquivo in raiz.rglob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            nomes = ([a.name for a in no.names] if isinstance(no, ast.Import)
                     else [no.module or ""] if isinstance(no, ast.ImportFrom) else [])
            for nome in nomes:
                assert nome.split(".")[0] not in proibidos, f"{arquivo.name} importa {nome}"


def test_gravacao_do_treino_tenta_de_novo_quando_o_banco_cai(monkeypatch):
    """Queda curta da conexão (DNS) não derruba o treino: a gravação espera e repete."""
    from sqlalchemy.exc import OperationalError

    from backend.services import servico_previsao

    monkeypatch.setattr(servico_previsao.time, "sleep", lambda _s: None)
    chamadas = []

    def grava():
        chamadas.append(1)
        if len(chamadas) < 3:
            raise OperationalError("SELECT 1", {}, Exception("failed to resolve host"))
        return "ok"

    assert servico_previsao._com_retentativa(grava) == "ok"
    assert len(chamadas) == 3

    # fora do ar além das tentativas: o erro sobe e o treino fica `error`
    chamadas.clear()
    monkeypatch.setattr(servico_previsao, "_ESPERAS_RETENTATIVA_S", (1,))
    with pytest.raises(OperationalError):
        servico_previsao._com_retentativa(grava)
    assert len(chamadas) == 2
