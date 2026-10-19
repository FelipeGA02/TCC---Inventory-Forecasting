"""Rotina semanal completa sobre a base sintetica (grid e backtest reduzidos)."""
from __future__ import annotations

import json

import pandas as pd

from backend.services.forecast_service import (
    Armazenamento, ConfigPrevisao, executar_previsao_semanal,
)


def _config() -> ConfigPrevisao:
    return ConfigPrevisao(janela_dias=300, n_origens_backtest=4, workers=1,
                          grid_pq=range(0, 2), grid_spq=range(0, 1))


def _arm(base) -> Armazenamento:
    return Armazenamento(base / "processed", base / "models", base / "results")


def test_rotina_semanal_grava_previsao_metricas_registro_e_logs(base_sintetica):
    arm = _arm(base_sintetica)
    r = executar_previsao_semanal(arm, _config())

    assert r["status"] == "completed"
    assert r["origem"] == "2026-04-28" and r["data_carga"] == "2026-04-28"   # terca
    assert r["horizonte_dias"] == 14

    prev = pd.read_csv(r["arquivos"]["previsao"], sep=";", dtype={"chave": str})
    series = prev.groupby(["nivel", "chave"]).size()
    assert set(prev["nivel"]) == {"loja", "categoria", "produto"}
    assert ("produto", "G1") in series and ("produto", "G2") not in series   # esporadico fica fora
    assert (series == 14).all()
    assert (prev["ic_inf_95"] <= prev["previsto"]).all()
    assert (prev["previsto"] <= prev["ic_sup_95"]).all()
    assert prev.loc[prev["dia_semana"] == "dom", "loja_fechada"].eq(1).all()

    met = pd.read_csv(r["arquivos"]["metricas"], sep=";")
    assert {"mase", "cobertura_ic95_pct", "erro_relativo_naive", "largura_ic95"} <= set(met.columns)
    assert set(met["status"]) <= {"trained", "low_confidence"}

    reg = json.loads((base_sintetica / "models" / "registro_modelos.json").read_text("utf-8"))
    loja = reg["series"]["Loja Teste|loja|total"]
    assert loja["versao"] == 1 and loja["spec"]["order"][1] == 1 and loja["params"]
    assert reg["series"]["Loja Teste|produto|G1"]["spec"]["order"][1] == 0   # produto: d = 0

    linhas = (base_sintetica / "results" / "logs" / "execucoes.jsonl").read_text("utf-8").splitlines()
    assert json.loads(linhas[-1])["status"] == "completed"
    assert list((base_sintetica / "results" / "logs").glob("previsao_*.log"))


def test_segunda_execucao_sem_base_nova_e_pulada_e_reusa_ordem(base_sintetica):
    arm = _arm(base_sintetica)
    executar_previsao_semanal(arm, _config())
    assert executar_previsao_semanal(arm, _config())["status"] == "skipped"

    r = executar_previsao_semanal(arm, _config(), forcar=True)
    reg = arm.ler_registro()
    assert r["status"] == "completed"
    assert reg["series"]["Loja Teste|loja|total"]["versao"] == 1          # ordem reaproveitada
    hist = pd.read_csv(r["arquivos"]["historico"], sep=";")
    assert hist["execucao_id"].nunique() == 1                       # mesma carga substituida
