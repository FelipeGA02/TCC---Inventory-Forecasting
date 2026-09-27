"""Bases externas para enriquecer a série diária: feriados (BrasilAPI) e clima (Open-Meteo).

Cada fonte é baixada uma vez e guardada em `data/external/`. As execuções seguintes leem o
cache, então o experimento é reproduzível mesmo sem internet.

- Feriados nacionais: BrasilAPI (`/api/feriados/v1/{ano}`). Já inclui Carnaval, Sexta-feira
  Santa, Corpus Christi e Consciência Negra (20/11, nacional desde 2024).
- Fechamentos locais: não há API de feriado municipal. Usamos só as datas em que **as duas
  lojas** ficaram sem venda num dia útil que não é feriado nacional, observadas nos dados
  (15/08 em 2024 e 2025; 08/12/2025). A confirmação fica como pergunta para a floricultura.
- Clima diário: Open-Meteo Archive (reanálise ERA5), gratuito e sem chave. Um ponto por
  loja: Jardim Canadá (Nova Lima) e Itabirito.
"""
from __future__ import annotations

import json
import os
import urllib.request

import pandas as pd

_ENRICHED_DIR = os.path.dirname(os.path.abspath(__file__))
_IA_PREDICTOR_ROOT = os.path.dirname(os.path.dirname(_ENRICHED_DIR))
EXTERNAL_DIR = os.path.join(_IA_PREDICTOR_ROOT, "data", "external")

LOJAS_COORD = {  # (latitude, longitude)
    "jardim_canada": (-20.06, -43.97),
    "itabirito": (-20.25, -43.80),
}

# Dias úteis sem venda nas duas lojas que não são feriado nacional (ver docstring).
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
