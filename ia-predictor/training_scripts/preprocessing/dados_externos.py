"""Bases externas: feriados nacionais (BrasilAPI) e clima (Open-Meteo).

Cada fonte é baixada uma vez e guardada em `data/external/`. As execuções seguintes leem o
cache, então o pipeline é reproduzível mesmo sem internet.

- Feriados nacionais: BrasilAPI (`/api/feriados/v1/{ano}`). Já inclui Carnaval, Sexta-feira
  Santa, Corpus Christi e Consciência Negra (20/11, nacional desde 2024). Usado pela Etapa 6
  (`build_calendar.py`).
- Clima diário: Open-Meteo Archive (reanálise ERA5), gratuito e sem chave. **Não entra no
  pipeline** (EDA §4 item 19: sem ganho na série total, doc 03). Fica aqui porque o
  experimento `enriched/sarimax_serie_crua_enriquecida.py` o usa.

Feriados municipais não têm fonte pronta. Os dias em que a loja fechou sem explicação
estão em `constants.py` (`FECHAMENTOS_OBSERVADOS`), só como fatos do histórico.

Movido de `training_scripts/enriched/` em 2026-09-27: a busca de feriados passou a ser
usada pelo pré-processamento.
"""
from __future__ import annotations

import json
import os
import urllib.request

import pandas as pd

_PREPROCESSING_DIR = os.path.dirname(os.path.abspath(__file__))
_IA_PREDICTOR_ROOT = os.path.dirname(os.path.dirname(_PREPROCESSING_DIR))
EXTERNAL_DIR = os.path.join(_IA_PREDICTOR_ROOT, "data", "external")

LOJAS_COORD = {  # (latitude, longitude)
    "jardim_canada": (-20.06, -43.97),
    "itabirito": (-20.25, -43.80),
}

# Lista plana usada pelo experimento enriquecido (doc 03): dias úteis sem venda nas duas
# lojas que não são feriado nacional. A regra completa, por loja, está em `constants.py`.
FECHAMENTOS_LOCAIS = ["2024-08-15", "2025-08-15", "2025-12-08"]


def _baixar_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def feriados_nacionais(anos) -> pd.DataFrame:
    linhas = []
    for ano in anos:
        path = os.path.join(EXTERNAL_DIR, f"feriados_nacionais_{ano}.json")
        if not os.path.exists(path):
            os.makedirs(EXTERNAL_DIR, exist_ok=True)
            dados = _baixar_json(f"https://brasilapi.com.br/api/feriados/v1/{ano}")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(dados, fh, ensure_ascii=False)
        with open(path, encoding="utf-8") as fh:
            linhas += json.load(fh)
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["date"])
    return df[["data", "name"]].rename(columns={"name": "nome"})


def clima_diario(inicio: str, fim: str) -> pd.DataFrame:
    """Chuva (mm) e temperatura máxima (°C) por dia, média das duas lojas."""
    path = os.path.join(EXTERNAL_DIR, f"clima_open_meteo_{inicio}_{fim}.csv")
    if not os.path.exists(path):
        os.makedirs(EXTERNAL_DIR, exist_ok=True)
        tabelas = []
        for loja, (lat, lon) in LOJAS_COORD.items():
            url = (
                "https://archive-api.open-meteo.com/v1/archive"
                f"?latitude={lat}&longitude={lon}&start_date={inicio}&end_date={fim}"
                "&daily=precipitation_sum,temperature_2m_max&timezone=America%2FSao_Paulo"
            )
            d = _baixar_json(url)["daily"]
            tabelas.append(pd.DataFrame({
                "data": d["time"], "loja": loja,
                "chuva_mm": d["precipitation_sum"], "temp_max": d["temperature_2m_max"],
            }))
        pd.concat(tabelas).to_csv(path, index=False)
    df = pd.read_csv(path, parse_dates=["data"])
    return df.groupby("data")[["chuva_mm", "temp_max"]].mean()
