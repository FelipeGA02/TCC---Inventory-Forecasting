"""Fixtures compartilhadas: base sintetica no formato de `data/processed/`."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # ia-predictor/


def _calendario(unidades, inicio, fim) -> pd.DataFrame:
    idx = pd.date_range(inicio, fim, freq="D")
    return pd.concat([pd.DataFrame({
        "data": idx.strftime("%Y-%m-%d"), "unidade": u,
        "loja_fechada": (idx.weekday == 6).astype(int), "abertura_excepcional": 0,
    }) for u in unidades], ignore_index=True)


def _vendas(unidade: str, idx: pd.DatetimeIndex, rng) -> pd.DataFrame:
    """2 categorias + 1 produto que vende todo dia aberto + 1 esporadico."""
    aberto = idx.weekday != 6
    perfil = np.array([1.2, 1.4, 1.4, 1.3, 1.1, 0.7, 0.0])[idx.weekday]
    linhas = []
    for cat, prods in {"Grama": [("G1", 30), ("G2", 0)], "Flores de corte": [("F1", 8)]}.items():
        for cod, base in prods:
            if base:
                q = np.where(aberto, rng.poisson(base * perfil), 0)
            else:   # esporadico: ~1 venda a cada 15 dias
                q = np.where(aberto & (rng.random(len(idx)) < 0.07), rng.poisson(20, len(idx)), 0)
            for d, v in zip(idx, q):
                if v > 0:
                    linhas.append((unidade, d.strftime("%Y-%m-%d"), cat, cod, f"Produto {cod}",
                                   float(v), 0.0))
    return pd.DataFrame(linhas, columns=["unidade", "data", "categoria", "produto_cod",
                                         "produto_nome", "qtd_fluxo", "qtd_encomenda"])


@pytest.fixture
def base_sintetica(tmp_path: Path) -> Path:
    """`data/processed/` sintetico: 1 unidade, ~16 meses terminando numa segunda."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2025-01-01", "2026-04-27", freq="D")       # 2026-04-27 = segunda
    processed = tmp_path / "processed"
    processed.mkdir()
    vendas = _vendas("Loja Teste", idx, rng)
    vendas.to_csv(processed / "vendas_diarias.csv", sep=";", index=False)
    _calendario(["Loja Teste"], "2025-01-01", "2026-06-30").to_csv(
        processed / "calendario_diario.csv", sep=";", index=False)
    sha = {n: hashlib.sha256((processed / n).read_bytes()).hexdigest()
           for n in ("vendas_diarias.csv", "calendario_diario.csv")}
    (processed / "manifesto.json").write_text(json.dumps({"sha256": sha}), encoding="utf-8")
    return tmp_path
