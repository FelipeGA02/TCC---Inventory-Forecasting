"""SARIMAX por produto com encomenda marcada POR PRODUTO (alem da regra da loja).

Problema que motiva o teste: a regra de encomenda da loja (venda > 2.000 un. no documento,
ADR-013) foi calibrada para o total da loja. Para um produto cuja venda tipica e de 10 un.,
vendas de 300 a 1.200 un. continuam na serie — na Grama Esmeralda (ITO) elas sao 2,7% das
vendas e 35% do volume. Junto com os dias abertos sem venda, isso deixa a serie do produto
muito variavel em log, e a faixa de 95% do modelo com log1p sai ~10x a previsao: calibrada,
mas larga demais para decidir compra.

Regra por produto
-----------------
Uma venda do produto (soma do produto no mesmo documento) e encomenda se for atipica PARA
AQUELE PRODUTO: z-score modificado de Iglewicz & Hoaglin (1993) em log1p(quantidade),

    M = 0,6745 * (log1p(q) - mediana) / MAD,    encomenda se M > 3,5  (so a cauda de cima)

com mediana e MAD das vendas do proprio produto. MAD = 0 (muitas vendas iguais) cai para o
desvio absoluto medio, como em `preprocessing/remove_encomendas_06.marcar_outliers`.
Aplicada DEPOIS da regra da loja: parte do fluxo diario.

Sem vazamento: mediana e MAD sao recalculadas em cada rodada, so com vendas anteriores a
origem. O limite vale para o treino e para a janela de teste — o alvo previsto e o fluxo
do produto sem as encomendas dele, definido com o que se sabia na origem.

Mesmo protocolo de `sku_regular_tuning.py` (mesmos SKUs regulares, origem andando de 1 em 1
dia com h = 14, 4 configuracoes d x transformacao, ordem por AIC na serie transformada),
para a comparacao ser direta — por isso o tuning precisa ter rodado antes com o mesmo
passo. Saidas no formato da loja: `_previsoes.csv`, `_operacional.csv` (h = 1) e metricas
em blocos todos os horizontes / `operacional_h1` / `por_horizonte`. A validacao interna (`auto`) nao entra: no teste anterior ela nao
ganhou da configuracao fixa.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.sku_encomenda_por_produto --unidade itabirito
"""
from __future__ import annotations

import argparse
import json
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import time  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from training_scripts.baseline.sarimax_itabirito_core import (  # noqa: E402
    HORIZONTE, M, METRICS_DIR, PRIMEIRA_ORIGEM,
)
from training_scripts.disaggregation.sku_regular_tuning import (  # noqa: E402
    CONFIGS, PASSO, _prever, _selecionar,
)
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (  # noqa: E402
    UNIDADES, blocos, carregar_fluxo, exogenas, fechados_da_unidade, gravar_previsoes,
    skus_regulares,
)

warnings.filterwarnings("ignore")

LIMIAR_M = 3.5             # Iglewicz & Hoaglin (1993)
CONST_MAD = 0.6745


def limite_produto(qtds: pd.Series) -> float:
    """Maior venda que ainda e 'normal' para o produto (em unidades)."""
    z = np.log1p(qtds.clip(lower=0))
    med = float(z.median())
    dev = (z - med).abs()
    mad = float(dev.median()) or float(dev.mean())
    if mad == 0:
        return float("inf")
    return float(np.expm1(med + LIMIAR_M * mad / CONST_MAD))


# --------------------------------------------------------------------------- #
# Uma tarefa por SKU (processo separado)
# --------------------------------------------------------------------------- #
_G: dict = {}


def _init(vendas, idx, X, fechados):
    _G.update(vendas=vendas, idx=idx, X=X, fech=fechados)


def _series_na_origem(sku: str, origem: pd.Timestamp):
    """Treino e janela de teste do SKU com o limite calculado so com o passado."""
    v = _G["vendas"][_G["vendas"]["produto_cod"] == sku]
    passado = v[v["emissao"] < origem]
    lim = limite_produto(passado["q"])
    normal = v[v["q"] <= lim]
    diario = normal.groupby("emissao")["q"].sum().reindex(_G["idx"], fill_value=0.0)
    total = v.groupby("emissao")["q"].sum().reindex(_G["idx"], fill_value=0.0)
    treino = diario[diario.index < origem]
    treino = treino[treino.index >= treino[treino > 0].index.min()]
    return treino, diario, total, lim, float(passado.loc[passado["q"] > lim, "q"].sum()), float(passado["q"].sum())


def _ordens_sku(args):
    """Ordem de cada configuracao, com dados antes da 1a rodada do SKU."""
    sku, primeira = args
    hist, *_ = _series_na_origem(sku, primeira)
    return sku, {k: _selecionar(hist, _G["X"], c["d"], c["log"]) for k, c in CONFIGS.items()}


def _rodada_sku(args):
    """Uma origem de um SKU, todas as configuracoes, com o limite calculado na origem."""
    sku, o, ordens = args
    X = _G["X"]
    s, diario, total, lim, vol_enc, vol_hist = _series_na_origem(sku, o)
    fut = pd.date_range(o, periods=HORIZONTE, freq="D")
    real, real_fluxo = diario.loc[fut].values, total.loc[fut].values
    ult7 = s.values[-M:]
    naive = np.array([ult7[i % M] for i in range(HORIZONTE)])
    escala = float(np.mean(np.abs(s.values[M:] - s.values[:-M])))
    limite = {"origem": str(o.date()), "limite": lim,
              "pct_volume_passado_marcado": vol_enc / vol_hist * 100 if vol_hist else 0.0}
    linhas = []
    for k, c in CONFIGS.items():
        if ordens[k] is None:
            continue
        try:
            p, lo, hi = _prever(s, X, ordens[k], fut, c["log"])
        except Exception:  # noqa: BLE001
            continue
        for h in range(HORIZONTE):
            linhas.append({"origem": o, "data": fut[h], "horizonte": h + 1, "sku": sku,
                           "config": k, "previsto": p[h], "ic_inf": lo[h], "ic_sup": hi[h],
                           "real": real[h], "real_fluxo_loja": real_fluxo[h],
                           "naive": naive[h], "escala": escala})
    return sku, limite, linhas


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def _largura(d: pd.DataFrame) -> dict:
    ok = d["previsto"] > 0
    return {"limite_sup_sobre_previsto_mediana": round(float((d.loc[ok, "ic_sup"] / d.loc[ok, "previsto"]).median()), 2),
            "largura_sobre_venda_media": round(float((d["ic_sup"] - d["ic_inf"]).mean() / d["real"].mean()), 2)}


def _blocos_com_largura(d: pd.DataFrame) -> dict:
    b = blocos(d)
    b["geral_todos_horizontes"].update(_largura(d))
    b["operacional_h1"].update(_largura(d[d["horizonte"] == 1]))
    return b


def executar(slug: str, workers: int, passo: int = PASSO) -> dict:
    unidade = UNIDADES[slug]
    t0 = time.time()
    fluxo, nomes = carregar_fluxo(unidade)
    idx = pd.date_range(fluxo["emissao"].min(), fluxo["emissao"].max(), freq="D")
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    X = exogenas(unidade, idx.append(pd.date_range(idx[-1] + pd.Timedelta(days=1),
                                                   periods=HORIZONTE, freq="D")))
    aberta = (X.loc[idx, "loja_fechada"] == 0).astype(int)
    fechados = fechados_da_unidade(unidade)
    origens = list(pd.date_range(PRIMEIRA_ORIGEM, idx[-1] - pd.Timedelta(days=HORIZONTE - 1),
                                 freq=f"{passo}D"))
    # Mesmos SKUs regulares do teste anterior (selecao no fluxo da loja), para comparar.
    regulares = {o: skus_regulares(matriz, aberta, o) for o in origens}
    todos = sorted({s for lst in regulares.values() for s in lst})
    por_sku = {s: [o for o in origens if s in regulares[o]] for s in todos}

    vendas = (fluxo[fluxo["produto_cod"].isin(todos)]
              .groupby(["emissao", "doc_numero", "produto_cod"], as_index=False)["qtdade"].sum()
              .rename(columns={"qtdade": "q"}))
    vendas = vendas[vendas["q"] > 0]
    print(f"=== {unidade} === {len(todos)} SKUs · {len(origens)} rodadas (origem a cada {passo} "
          f"dia(s)) · encomenda por produto: Iglewicz & Hoaglin, M > {LIMIAR_M} em log1p(venda), "
          f"recalculado por rodada", flush=True)

    # Comparacao com o teste anterior (so a regra da loja): precisa das mesmas origens.
    ant = pd.read_csv(os.path.join(METRICS_DIR, f"sku_tuning_{slug}_previsoes.csv"), sep=";",
                      dtype={"sku": str}, parse_dates=["origem", "data"])
    if set(ant["origem"]) != set(origens):
        raise RuntimeError(f"sku_tuning_{slug}_previsoes.csv tem outras origens: rode antes "
                           f"`sku_regular_tuning --unidade {slug} --passo {passo}`")
    ant = ant[(~ant["data"].isin(fechados)) & (ant["config"].isin(CONFIGS))]

    metas, linhas = {}, []
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(vendas, idx, X, fechados)) as ex:
        ordens = dict(ex.map(_ordens_sku, [(s, o[0]) for s, o in por_sku.items()]))
        print(f"  [ordens] {len(ordens)} SKUs · {time.time() - t0:.0f}s", flush=True)
        metas = {s: {"ordens": {k: (None if v is None else {"order": list(v["order"]),
                                                             "seasonal_order": list(v["seasonal_order"])})
                                for k, v in ords.items()},
                     "limites": []} for s, ords in ordens.items()}
        tarefas = [(s, o, ordens[s]) for s, lst in por_sku.items() for o in lst]
        for n, (sku, limite, lin) in enumerate(ex.map(_rodada_sku, tarefas, chunksize=4), start=1):
            metas[sku]["limites"].append(limite)
            linhas.extend(lin)
            if n % 250 == 0 or n == len(tarefas):
                print(f"  [walk-forward] {n}/{len(tarefas)} SKU-rodadas · {time.time() - t0:.0f}s",
                      flush=True)
    for sku, meta in metas.items():
        ult = meta["limites"][-1]
        print(f"  [{sku}] {nomes.get(sku, '')[:30]:30s} limite na ultima rodada {ult['limite']:7.0f} un. "
              f"· {ult['pct_volume_passado_marcado']:4.1f}% do volume marcado", flush=True)
    prev = pd.DataFrame(linhas)
    aberto = prev[~prev["data"].isin(fechados)]

    met = {}
    print(f"\n[resultado] {unidade} · dias de loja aberta · antes = só regra da loja · depois = + regra por produto")
    print(f"  {'config':12s} {'':6s} {'':5s} {'MASE':>6s} {'÷naive':>7s} {'IC95':>6s} {'sup÷prev':>8s} "
          f"{'larg÷venda':>10s} {'prev/real':>9s}  ok?")
    for k in CONFIGS:
        for rot, d in (("antes", ant[ant["config"] == k]), ("depois", aberto[aberto["config"] == k])):
            met[f"{k}|{rot}"] = _blocos_com_largura(d)
            for hor, chave in (("h1-14", "geral_todos_horizontes"), ("h=1", "operacional_h1")):
                b = met[f"{k}|{rot}"][chave]
                print(f"  {k:12s} {rot:6s} {hor:5s} {b['mase']:6.3f} {b['erro_relativo_naive']:7.3f} "
                      f"{b['cobertura_ic95_pct']:5.1f}% {b['limite_sup_sobre_previsto_mediana']:7.1f}x "
                      f"{b['largura_sobre_venda_media']:9.1f}x {b['previsto_sobre_real_pct']:8.1f}%  "
                      f"{'SIM' if b['passa_criterio_diario'] else 'nao'}")

    # Quanto da venda do produto a nova regra deixa de fora (na janela de teste)
    # h = 1: cada data aparece uma vez, com o limite calculado na vespera.
    teste = aberto[(aberto["config"] == "d1|log1p") & (aberto["horizonte"] == 1)]
    fora = 1 - teste["real"].sum() / teste["real_fluxo_loja"].sum()
    por = (teste.groupby("sku")[["real", "real_fluxo_loja"]].sum()
           .assign(pct_fora=lambda x: (1 - x.real / x.real_fluxo_loja) * 100))
    print(f"\n[volume] a regra por produto tirou {fora:.1%} da venda dos 12 produtos nos dias de teste")
    print(por.assign(nome=[nomes.get(s, '')[:32] for s in por.index])[["nome", "pct_fora"]]
          .round(1).sort_values("pct_fora", ascending=False).to_string())

    base = os.path.join(METRICS_DIR, f"sku_encomenda_produto_{slug}")
    arquivos = gravar_previsoes(prev, base)
    saida = {"unidade": unidade, "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
             "regra": {"metodo": "Iglewicz & Hoaglin (1993), z-score modificado em log1p(venda do produto)",
                       "limiar_M": LIMIAR_M, "cauda": "superior", "recalculo": "por rodada, so passado",
                       "aplicada_apos": "regra da loja (venda > 2.000 un. no documento)"},
             "walk_forward": {"primeira_origem": str(PRIMEIRA_ORIGEM.date()), "passo_origem_dias": passo,
                              "n_rodadas": len(origens), "horizonte_dias": HORIZONTE},
             "volume_tirado_pct_teste": round(fora * 100, 1),
             "volume_tirado_por_sku_pct": por["pct_fora"].round(1).to_dict(),
             "metricas_dias_abertos": met, "por_sku": metas, "arquivos": arquivos}
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)
    print(f"[arquivos] {base}.json · _previsoes.csv · _operacional.csv ({time.time() - t0:.0f}s)", flush=True)
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--unidade", choices=list(UNIDADES), default="itabirito")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--passo", type=int, default=PASSO, help="dias entre origens")
    a = ap.parse_args()
    executar(a.unidade, a.workers, a.passo)


if __name__ == "__main__":
    main()
