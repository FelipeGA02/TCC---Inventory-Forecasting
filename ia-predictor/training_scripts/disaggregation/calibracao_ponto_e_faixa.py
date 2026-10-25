"""Da previsao bruta ao que a loja recebe: calibra o ponto e escolhe a largura da faixa.

Pergunta
--------
`variantes_log_d_categoria_sku.py` responde "qual variante erra menos". Nao responde o que
a previsao como servico precisa decidir:

  1. o numero do dia tem que acertar perto (h = 1..3 pesa mais que h = 14);
  2. a faixa tem que conter o realizado na frequencia prometida;
  3. a faixa nao pode ser larga a ponto de nao informar nada — um teto de 7x a media
     diaria "acerta" quase sempre e nao vale nada para quem decide compra.

Este modulo nao reajusta nada: le o `_previsoes.csv` do walk-forward e trata dois defeitos
que a tabela de variantes expoe mas nao corrige.

Defeito 1 — o ponto do `log1p` e mediana, nao media
---------------------------------------------------
Em serie de cauda longa a mediana fica muito abaixo da media: em Itabirito a variante
`log1p|d1` preve 52% do vendido em Grama e 46% no SKU da Esmeralda. Aqui o ponto recebe um
fator multiplicativo `k` por horizonte, estimado so na janela de calibracao
(`k = soma(real) / soma(previsto)`). E a correcao de vies que o fator de Duan tentou fazer
no doc 04 §2 e explodiu — a diferenca e que `k` sai do erro observado no walk-forward, nao
de uma hipotese sobre a distribuicao dos residuos.

Defeito 2 — o IC 95% do SARIMAX e largo e nao e o que a loja quer
-----------------------------------------------------------------
A faixa aqui vem dos quantis empiricos do erro de previsao na janela de calibracao, por
horizonte, em niveis nominais de 50% a 95%. Com isso a largura passa a ser uma escolha de
negocio: cobertura menor em troca de uma faixa que cabe numa decisao. Reporta tambem a
faixa de um lado so (`teto`), que e a forma do "quanto ter disponivel" do doc 04 §5.

Honestidade do numero
---------------------
As origens sao partidas em ordem cronologica: `FRACAO_CALIBRACAO` das primeiras estimam
`k` e os quantis, o resto avalia. Calibrar e avaliar na mesma janela daria cobertura
perfeita por construcao. Por isso os numeros deste modulo NAO sao comparaveis com os do
`variantes_log_d_categoria_sku.py`, que avalia todas as origens.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.calibracao_ponto_e_faixa --unidade itabirito
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from training_scripts.baseline.sarimax_itabirito_core import METRICS_DIR
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (
    UNIDADES, fechados_da_unidade,
)

FRACAO_CALIBRACAO = 0.6        # 60% das origens calibram, 40% avaliam
NIVEIS = [0.50, 0.80, 0.90, 0.95]
NIVEL_TETO = 0.90              # faixa de um lado so: quantil 90 do erro
GRUPOS_H = {"h1_3": range(1, 4), "h4_7": range(4, 8), "h8_14": range(8, 15)}


def carregar(unidade: str, slug: str) -> pd.DataFrame:
    caminho = os.path.join(METRICS_DIR, f"{slug}_previsoes.csv")
    if not os.path.exists(caminho):
        raise SystemExit(f"nao encontrei {caminho} — rode variantes_log_d_categoria_sku antes")
    d = pd.read_csv(caminho, sep=";", decimal=".", parse_dates=["origem", "data"])
    return d[~d["data"].isin(fechados_da_unidade(unidade))].copy()


def _split(origens: np.ndarray) -> tuple[set, set]:
    o = np.sort(np.unique(origens))
    corte = int(len(o) * FRACAO_CALIBRACAO)
    return set(o[:corte]), set(o[corte:])


def calibrar_e_avaliar(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uma linha por (serie, variante, grupo de horizonte) com ponto e faixas avaliados."""
    cal_o, ava_o = _split(d["origem"].values)
    linhas, pontos = [], []

    for (serie, var), g in d.groupby(["serie", "variante"]):
        # Fator de vies por horizonte: estimado na calibracao, aplicado na avaliacao.
        cal = g[g["origem"].isin(cal_o)]
        k = {}
        for h, gh in cal.groupby("horizonte"):
            s = gh["previsto"].sum()
            k[int(h)] = float(gh["real"].sum() / s) if s > 0 else 1.0

        g = g.assign(k=g["horizonte"].map(k))
        g["corrigido"] = (g["previsto"] * g["k"]).clip(lower=0)
        cal, ava = g[g["origem"].isin(cal_o)], g[g["origem"].isin(ava_o)]

        for grupo, hs in GRUPOS_H.items():
            c = cal[cal["horizonte"].isin(hs)]
            a = ava[ava["horizonte"].isin(hs)]
            if a.empty or c.empty:
                continue
            media_real = float(a["real"].mean())
            ae_n = (a["real"] - a["naive"]).abs().sum()

            pontos.append({
                "serie": serie, "variante": var, "grupo_h": grupo,
                "k_medio": round(float(np.mean([k[h] for h in hs if h in k])), 3),
                "media_real": round(media_real, 1),
                "mae_bruto": round(float((a["real"] - a["previsto"]).abs().mean()), 2),
                "mae_corrigido": round(float((a["real"] - a["corrigido"]).abs().mean()), 2),
                "rel_naive_bruto": round(float((a["real"] - a["previsto"]).abs().sum() / ae_n), 3)
                if ae_n else None,
                "rel_naive_corrigido": round(float((a["real"] - a["corrigido"]).abs().sum() / ae_n), 3)
                if ae_n else None,
                "vies_bruto_pct": round(float(a["previsto"].sum() / a["real"].sum() * 100), 1)
                if a["real"].sum() else None,
                "vies_corrigido_pct": round(float(a["corrigido"].sum() / a["real"].sum() * 100), 1)
                if a["real"].sum() else None,
            })

            # Quantis do erro na calibracao -> faixa na avaliacao. O centro da faixa e
            # avaliado nas duas versoes: o ponto bruto do SARIMAX e o corrigido por k.
            # Importa porque a correcao de vies piora o erro absoluto (a mediana e o ponto
            # que minimiza MAE), entao a faixa recomendada tem de ficar em volta do bruto.
            for centro in ("bruto", "corrigido"):
                col = "previsto" if centro == "bruto" else "corrigido"
                erro_cal = (c["real"] - c[col]).values
                for nivel in NIVEIS:
                    lo_q, hi_q = np.quantile(erro_cal, [(1 - nivel) / 2, 1 - (1 - nivel) / 2])
                    lo = (a[col] + lo_q).clip(lower=0)
                    hi = (a[col] + hi_q).clip(lower=0)
                    dentro = (a["real"] >= lo) & (a["real"] <= hi)
                    linhas.append({
                        "serie": serie, "variante": var, "grupo_h": grupo, "centro": centro,
                        "faixa": f"{int(nivel * 100)}%", "tipo": "dois lados",
                        "cobertura_pct": round(float(dentro.mean() * 100), 1),
                        "largura_media": round(float((hi - lo).mean()), 1),
                        "largura_x_media_diaria": round(float((hi - lo).mean() / media_real), 2)
                        if media_real else None,
                    })

                # Faixa de um lado so: piso 0, teto no quantil NIVEL_TETO do erro.
                hi_q = float(np.quantile(erro_cal, NIVEL_TETO))
                teto = (a[col] + hi_q).clip(lower=0)
                linhas.append({
                    "serie": serie, "variante": var, "grupo_h": grupo, "centro": centro,
                    "faixa": f"teto {int(NIVEL_TETO * 100)}%", "tipo": "um lado",
                    "cobertura_pct": round(float((a["real"] <= teto).mean() * 100), 1),
                    "largura_media": round(float(teto.mean()), 1),
                    "largura_x_media_diaria": round(float(teto.mean() / media_real), 2)
                    if media_real else None,
                })

    return pd.DataFrame(pontos), pd.DataFrame(linhas)


def executar(unidade_slug: str) -> dict:
    unidade = UNIDADES[unidade_slug]
    slug = f"variantes_log_d_fluxo_{unidade_slug.replace('-', '_')}"
    d = carregar(unidade, slug)
    cal_o, ava_o = _split(d["origem"].values)
    pontos, faixas = calibrar_e_avaliar(d)

    base = os.path.join(METRICS_DIR, f"calibracao_{unidade_slug.replace('-', '_')}")
    pontos.to_csv(f"{base}_ponto.csv", sep=";", index=False, decimal=".")
    faixas.to_csv(f"{base}_faixa.csv", sep=";", index=False, decimal=".")

    print(f"=== {unidade} === calibracao {len(cal_o)} origens · avaliacao {len(ava_o)} origens")
    print("\n--- PONTO (avaliacao; bruto = saida do SARIMAX, corrigido = x k do vies) ---")
    print(pontos.to_string(index=False))
    print("\n--- FAIXA (avaliacao; largura em multiplos da venda media do dia) ---")
    print(faixas.to_string(index=False))

    saida = {
        "unidade": unidade, "slug_origem": slug,
        "fracao_calibracao": FRACAO_CALIBRACAO,
        "n_origens_calibracao": len(cal_o), "n_origens_avaliacao": len(ava_o),
        "niveis": NIVEIS, "nivel_teto": NIVEL_TETO,
        "grupos_horizonte": {k: [min(v), max(v)] for k, v in GRUPOS_H.items()},
        "ponto": pontos.to_dict("records"),
        "faixa": faixas.to_dict("records"),
        "nota": ("numeros NAO comparaveis com variantes_log_d_*: aqui a avaliacao usa so as "
                 f"ultimas {len(ava_o)} origens, o resto calibra k e os quantis."),
    }
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)
    print(f"\n[arquivos] {base}.json · {base}_ponto.csv · {base}_faixa.csv")
    return saida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unidade", default="itabirito", choices=sorted(UNIDADES))
    executar(ap.parse_args().unidade)


if __name__ == "__main__":
    main()
