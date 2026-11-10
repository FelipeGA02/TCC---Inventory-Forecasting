"""Avaliação de uma série na tela de histórico (`domain.painel.avaliacao_do_historico`)."""
from backend.domain.painel import avaliacao_do_historico

METRICAS = {"origens": 56, "dias_avaliados": 672, "mae": 250.0, "rmse": 340.0, "mase": 0.85,
            "erro_relativo_naive": 0.8, "cobertura_ic95_pct": 95.0, "largura_ic95": 1000.0,
            "venda_media_dia": 1000.0, "previsto_sobre_real_pct": 110.0, "erro_total_14d_pct": 30.0}


def test_traz_as_metricas_da_tela_e_o_erro_em_porcentagem_da_venda():
    a = avaliacao_do_historico(METRICAS, "trained", "2026-03-02T10:00:00", "2026-02-28")
    assert a == {"status": "trained", "treinado_em": "2026-03-02T10:00:00", "dados_ate": "2026-02-28",
                 "dias_avaliados": 672, "mae": 250.0, "wape_pct": 25.0, "mase": 0.85,
                 "largura_ic95": 1000.0, "venda_media_dia": 1000.0}


def test_sem_venda_media_o_erro_em_porcentagem_fica_vazio():
    a = avaliacao_do_historico({**METRICAS, "venda_media_dia": 0.0}, "trained", "2026-03-02T10:00:00", None)
    assert a["wape_pct"] is None and a["mae"] == 250.0


def test_sem_metricas_nao_ha_avaliacao():
    assert avaliacao_do_historico(None, "insufficient_data", "2026-03-02T10:00:00", None) is None
    assert avaliacao_do_historico({"dias_avaliados": 0}, "error", "2026-03-02T10:00:00", None) is None
