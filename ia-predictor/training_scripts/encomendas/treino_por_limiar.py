"""Treino de produção com cada limiar de encomenda grande (ADR-018): fixo 2.000 × 4 × 3 desvios.

Pergunta
--------
O limiar de encomenda grande muda o fluxo diário que o SARIMAX recebe. Com o limiar de cada
loja em média + 4 (ou 3) desvios-padrão da quantidade dos pedidos, as previsões das séries
do sistema ficam melhores ou piores que com o limiar fixo de 2.000 un. (ADR-013)?

Séries e receita
----------------
As do serviço de previsão (ADR-017), montadas como em `servico_previsao._montar_series`: em
cada loja, as 4 categorias e cada produto de grama (o produto sem venda suficiente fica
`insufficient_data`, como no sistema). Receita de produção sem mudança: `treinar_serie` com
`ConfigTreino()` — SARIMAX m = 7, d = 0, D = 0, ordem por AIC antes da 1ª origem, janela
deslizante de 365 dias, 56 origens de 1 dia, h = 14, exógenas de calendário.

Variantes (só a marcação de encomenda grande muda)
--------------------------------------------------
  * `fixo` — pedido > 2.000 un. (ADR-013, o que o sistema usava);
  * `k4`   — pedido > média + 4 desvios dos pedidos da loja (ADR-018), base inteira;
  * `k3`   — idem com 3 desvios.

Leitura
-------
Cada variante é avaliada no **seu** fluxo, como o sistema avalia: o alvo muda entre elas
(o que sai como encomenda grande não é previsto). Por isso o que compara variantes é o erro
relativo à naïve na mesma janela, a cobertura do IC 95%, o status e o quanto do volume sai
do fluxo — não o MAE absoluto.

Execução (a partir de `ia-predictor/`) — um processo por série e variante, porque o pool de
processos não sobrevive a treinos longos no proot de desenvolvimento:
    python -m training_scripts.encomendas.treino_por_limiar --listar
    python -m training_scripts.encomendas.treino_por_limiar --variante k4 --serie itabirito:category:Grama
    python -m training_scripts.encomendas.treino_por_limiar --consolidar
Saída: `results/metrics/treino_limiar_encomendas/<variante>__<serie>.json` (+ `_backtest.csv`)
e, ao consolidar, `results/metrics/treino_limiar_encomendas.csv`.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import pandas as pd

from backend.domain.features.exogenous import matriz_exogena
from backend.domain.features.time_series import serie_diaria
from backend.domain.models.trainer import NIVEL_CATEGORIA, NIVEL_PRODUTO, ConfigTreino, treinar_serie
from training_scripts.preprocessing.classificacao_03 import CLASSIFIED_CSV
from training_scripts.preprocessing.extrair_base_01 import OUTPUT_DIR
from training_scripts.preprocessing.limpeza_para_treino_04 import CATEGORIA_NAO_PRODUTO, UNIDADES
from training_scripts.preprocessing.remove_encomendas_06 import (
    LIMIAR_QTD_VENDA,
    calcular_limiares,
    marcar_encomendas_por_unidade,
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "treino_limiar_encomendas")
CONSOLIDADO_CSV = os.path.join(_RAIZ, "results", "metrics", "treino_limiar_encomendas.csv")
CALENDARIO_CSV = os.path.join(OUTPUT_DIR, "calendario_diario.csv")

CATEGORIAS = ["Grama", "Plantas diversas", "Produtos de jardim", "Flores de corte"]
CATEGORIA_PRODUTOS = "Grama"
SLUG = {"Jardim Canadá": "jardim-canada", "Itabirito": "itabirito"}
VARIANTES = {"fixo": None, "k4": 4.0, "k3": 3.0}


def carregar() -> pd.DataFrame:
    df = pd.read_csv(CLASSIFIED_CSV, sep=";", dtype=str, keep_default_na=False)
    df["qtdade"] = pd.to_numeric(df["qtdade"], errors="coerce").fillna(0.0)
    df["emissao"] = pd.to_datetime(df["emissao"], errors="coerce")
    return df[(df["categoria"] != CATEGORIA_NAO_PRODUTO) & df["unidade"].isin(UNIDADES)
              & df["emissao"].notna()].copy()


def limiares_da_variante(df: pd.DataFrame, variante: str) -> dict:
    k = VARIANTES[variante]
    return {u: float(LIMIAR_QTD_VENDA) for u in UNIDADES} if k is None else calcular_limiares(df, k)


def chaves(df: pd.DataFrame) -> list[str]:
    """As séries do treino: 4 categorias e cada produto de grama que vendeu, por loja."""
    saida = []
    for unidade in UNIDADES:
        base = df[df["unidade"] == unidade]
        saida += [f"{SLUG[unidade]}:{NIVEL_CATEGORIA}:{c}" for c in CATEGORIAS]
        grama = base[base["categoria"] == CATEGORIA_PRODUTOS]
        ordem = grama.groupby("produto_cod")["qtdade"].sum().sort_values(ascending=False).index
        saida += [f"{SLUG[unidade]}:{NIVEL_PRODUTO}:{cod}" for cod in ordem]
    return saida


def montar(df: pd.DataFrame, variante: str, chave: str):
    """Série, exógenas e dias abertos de uma chave, com a marcação da variante."""
    slug, nivel, item = chave.split(":", 2)
    unidade = next(u for u, s in SLUG.items() if s == slug)
    limiares = limiares_da_variante(df, variante)
    df = df.assign(encomenda=marcar_encomendas_por_unidade(df, limiares))
    data_until = df["emissao"].max()
    vendas = df[df["unidade"] == unidade]
    fluxo = vendas[~vendas["encomenda"]]
    inicio = vendas["emissao"].min()

    cal = pd.read_csv(CALENDARIO_CSV, sep=";", parse_dates=["data"])
    cal_loja = cal[cal["unidade"] == unidade].set_index("data")[["loja_fechada", "abertura_excepcional"]]
    X, _ = matriz_exogena(pd.date_range(inicio, data_until + pd.Timedelta(days=ConfigTreino().horizonte), freq="D"),
                          cal_loja)
    aberta = X["loja_fechada"] == 0
    if nivel == NIVEL_CATEGORIA:
        y = serie_diaria(fluxo[fluxo["categoria"] == item], data_until, inicio=inicio)
        nome = item
    else:
        grama = vendas[vendas["categoria"] == CATEGORIA_PRODUTOS]
        ini_prod = grama.loc[grama["produto_cod"] == item, "emissao"].min()
        y = serie_diaria(fluxo[fluxo["produto_cod"] == item], data_until, inicio=ini_prod)
        X, aberta = X.loc[ini_prod:], aberta.loc[ini_prod:]
        nome = grama.sort_values("emissao").loc[grama["produto_cod"] == item, "produto_nome"].iloc[-1]
    serie = vendas[vendas["categoria"] == item] if nivel == NIVEL_CATEGORIA else vendas[vendas["produto_cod"] == item]
    volume = serie["qtdade"].sum()
    pct_encomenda = round(100 * serie.loc[serie["encomenda"], "qtdade"].sum() / volume, 1) if volume else None
    return y, X, aberta, nivel, nome, unidade, limiares[unidade], pct_encomenda


def rodar(variante: str, chave: str) -> dict:
    t0 = time.time()
    df = carregar()
    y, X, aberta, nivel, nome, unidade, limiar, pct_enc = montar(df, variante, chave)
    r = treinar_serie(y, X, aberta, ConfigTreino(), nivel)
    saida = {"variante": variante, "serie": chave, "unidade": unidade, "nivel": nivel, "nome": nome,
             "limiar_un": round(limiar, 1), "pct_volume_encomenda": pct_enc, "status": r.status, "motivo": r.motivo,
             "ordem": r.ordem, "ordem_sazonal": r.ordem_sazonal, "aic": r.aic, "metricas": r.metricas,
             "diagnostico": r.diagnostico, "segundos": round(time.time() - t0, 1)}
    os.makedirs(SAIDA_DIR, exist_ok=True)
    base = os.path.join(SAIDA_DIR, f"{variante}__{chave.replace(':', '_')}")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)
    if r.backtest is not None:
        r.backtest.to_csv(base + "_backtest.csv", sep=";", index=False)
    return saida


def consolidar() -> pd.DataFrame:
    linhas = []
    for caminho in sorted(glob.glob(os.path.join(SAIDA_DIR, "*.json"))):
        with open(caminho, encoding="utf-8") as fh:
            r = json.load(fh)
        m = r.get("metricas") or {}
        linhas.append({"variante": r["variante"], "unidade": r["unidade"], "nivel": r["nivel"], "serie": r["serie"],
                       "nome": r["nome"], "limiar_un": r["limiar_un"], "pct_volume_encomenda": r["pct_volume_encomenda"],
                       "status": r["status"], "motivo": r["motivo"],
                       "ordem": f"{tuple(r['ordem'])}{tuple(r['ordem_sazonal'])}" if r["ordem"] else None,
                       **{k: m.get(k) for k in ("mase", "erro_relativo_naive", "origens_vence_naive_pct",
                                                "cobertura_ic95_pct", "largura_ic95", "mae", "venda_media_dia",
                                                "previsto_sobre_real_pct", "erro_total_14d_pct")},
                       "ljung_box_p": (r.get("diagnostico") or {}).get("ljung_box_p"),
                       "segundos": r["segundos"]})
    tab = pd.DataFrame(linhas)
    tab.to_csv(CONSOLIDADO_CSV, sep=";", index=False, encoding="utf-8")
    return tab


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--listar", action="store_true", help="imprime as chaves das séries")
    p.add_argument("--variante", choices=list(VARIANTES))
    p.add_argument("--serie")
    p.add_argument("--consolidar", action="store_true")
    a = p.parse_args()
    if a.listar:
        print("\n".join(chaves(carregar())))
    elif a.consolidar:
        tab = consolidar()
        pd.set_option("display.width", 250)
        treinadas = tab[tab["mase"].notna()]
        print(treinadas.pivot_table(index=["unidade", "nome"], columns="variante",
                                    values=["erro_relativo_naive", "mase", "cobertura_ic95_pct"],
                                    aggfunc="first").to_string())
        print(f"[treino_por_limiar] {len(tab)} resultados em {CONSOLIDADO_CSV}")
    else:
        r = rodar(a.variante, a.serie)
        m = r["metricas"] or {}
        print(f"[treino_por_limiar] {a.variante} {a.serie}: {r['status']} · MASE {m.get('mase')} · "
              f"erro/naïve {m.get('erro_relativo_naive')} · IC95 {m.get('cobertura_ic95_pct')}% · {r['segundos']}s")


if __name__ == "__main__":
    main()
