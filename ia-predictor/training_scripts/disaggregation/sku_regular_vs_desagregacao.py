"""Previsao diaria dos SKUs de venda regular: SARIMAX no proprio SKU x desagregacao do L1.

Pergunta
--------
Para os produtos que vendem quase todo dia, vale mais ajustar um SARIMAX direto na serie
do produto ou repartir a previsao da loja (L1) pela participacao do produto? E algum dos
dois e bom o bastante no dia a dia (MASE < 1 e faixa de 95% acertando entre 90% e 98%,
os limiares do CLAUDE.md)?

Escopo: SKUs de venda regular
-----------------------------
Um SKU entra no experimento numa rodada se, com os dados ANTERIORES a origem:

  * ADI < 1,32 — intervalo medio entre vendas abaixo do corte de Syntetos, Boylan &
    Croston (2005), o mesmo de `eda/eda_classificacao_sku.py`. ADI = dias de loja aberta
    no span / dias com venda. Duas diferencas para o EDA: (1) so contam dias de loja aberta
    (`loja_fechada = 0` no calendario) — dia fechado nao e um periodo em que a venda
    poderia ocorrer, e com dias de calendario um SKU que vende em todo dia util ja sai com
    ADI ~1,2 so pelos domingos; (2) o span vai da 1a venda ate a vespera da origem (e nao
    ate a ultima venda), para que um produto que parou de vender deixe de ser regular;
  * span >= 180 dias — o minimo de observacoes que o projeto ja exige do L1
    (`MIN_OBSERVATIONS_DAYS`).

O CV2 nao filtra: SKUs "erraticos" (regulares no tempo, tamanho variavel) ficam, como as
series do L1, que tambem sao erraticas.

Fluxo diario (ADR-013)
----------------------
Tudo roda sobre o fluxo diario: vendas com mais de 2.000 unidades no documento saem da
serie, pela mesma regra de `preprocessing/remove_encomendas_06.py`. E a mesma base dos
treinos C e D de Itabirito.

Metodos comparados (por SKU, mesma origem, mesmos 14 dias)
----------------------------------------------------------
  * `sarimax_sku`  — SARIMAX no proprio SKU. Ordem escolhida por AIC (grid do L1) uma vez
    por SKU, com os dados anteriores a primeira rodada em que ele e regular; mesmas
    exogenas de calendario do L1.
  * `desag_8sem`   — previsao L1 da loja (fluxo) x participacao do SKU nas ultimas 8
    semanas (a janela do CLAUDE.md, L2).
  * `desag_hist`   — previsao L1 x participacao do SKU em todo o historico desde a 1a venda
    dele ("proportions of historical averages", Gross & Sohl, 1990).
  * `naive`        — regua: repete os ultimos 7 dias do SKU.

Cada metodo roda com e sem `log1p` (variantes `sem_log` e `log1p`, como os treinos C e D).
Na desagregacao, a faixa de 95% e a do L1 multiplicada pela participacao — uma
aproximacao, e a cobertura medida aqui diz se ela se sustenta.

Protocolo
---------
Walk-forward igual ao dos treinos da loja (`sarimax_itabirito_core`): a origem anda de 1 em
1 dia a partir de 2025-03-02 e cada ajuste preve os 14 dias seguintes, entao toda data
prevista aparece em ate 14 janelas, uma por horizonte h = 1..14. Toda participacao, ordem e
selecao de SKU usa so dados anteriores a origem.

Saidas, no mesmo formato da loja: `*_previsoes.csv` com os 14 horizontes e
`*_operacional.csv` so com h = 1 (a previsao feita com o modelo reajustado na vespera). As
metricas vem em tres blocos: todos os horizontes, `operacional_h1` e `por_horizonte`.

As metricas que decidem sao as dos **dias de loja aberta**. Domingo e feriado (venda 0,
previsao ~0) deixam o MASE menor e a cobertura maior sem dizer nada sobre a previsao.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.disaggregation.sku_regular_vs_desagregacao
    python -m training_scripts.disaggregation.sku_regular_vs_desagregacao --unidade itabirito --passo 14
"""
from __future__ import annotations

import argparse
import json
import os

# Um thread de BLAS por processo: os ajustes ja rodam em paralelo (ProcessPoolExecutor),
# e threads aninhados disputam os nucleos e deixam cada ajuste varias vezes mais lento.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import time  # noqa: E402
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from training_scripts.baseline.sarimax_itabirito_core import (
    ALPHA, CALENDARIO, COLS_CALENDARIO, COLS_EXOG, DIAS, HORIZONTE, M, METRICS_DIR,
    PRIMEIRA_ORIGEM, ajustar, destransformar, selecionar_ordem, transformar,
)
from training_scripts.preprocessing.remove_encomendas_06 import (
    CLASSIFIED_CSV, LIMIAR_QTD_VENDA, marcar_encomendas,
)

warnings.filterwarnings("ignore")

UNIDADES = {"itabirito": "Itabirito", "jardim-canada": "Jardim Canadá"}
ADI_CORTE = 1.32              # Syntetos, Boylan & Croston (2005)
MIN_SPAN_DIAS = 180           # MIN_OBSERVATIONS_DAYS do L1 (CLAUDE.md)
JANELA_8SEM = 56              # participacao movel do L2 (CLAUDE.md)
PASSO_PADRAO = 1              # origem anda 1 dia, como nos treinos da loja (A-D)
VARIANTES = {"sem_log": False, "log1p": True}
METODOS = ["sarimax_sku", "desag_8sem", "desag_hist"]


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
def carregar_fluxo(unidade: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Linhas do fluxo diario da unidade (sem servico e sem encomendas) + nomes dos SKUs."""
    cols = ["unidade", "emissao", "doc_numero", "produto_cod", "produto_nome", "qtdade",
            "categoria"]
    df = pd.read_csv(CLASSIFIED_CSV, sep=";", usecols=cols, dtype=str, keep_default_na=False)
    df["qtdade"] = pd.to_numeric(df["qtdade"], errors="coerce").fillna(0.0)
    df["emissao"] = pd.to_datetime(df["emissao"], errors="coerce")
    df = df[(df["categoria"] != "Servico e taxa") & df["emissao"].notna()]
    df = df[df["unidade"] == unidade].copy()
    df["encomenda"] = marcar_encomendas(df, LIMIAR_QTD_VENDA)
    nomes = df.sort_values("emissao").groupby("produto_cod")["produto_nome"].last().to_dict()
    return df[~df["encomenda"]], nomes


def exogenas(unidade: str, idx: pd.DatetimeIndex) -> pd.DataFrame:
    cal = pd.read_csv(CALENDARIO, sep=";")
    cal = cal[cal["unidade"] == unidade].copy()
    cal["data"] = pd.to_datetime(cal["data"])
    cal = cal.set_index("data")[COLS_CALENDARIO].astype(float)
    X = pd.DataFrame(index=idx)
    for i, nome in enumerate(DIAS):
        X[f"dia_{nome}"] = (idx.weekday == i).astype(float)
    X[COLS_CALENDARIO] = cal.reindex(idx)[COLS_CALENDARIO]
    if X.isna().any().any():
        raise ValueError(f"calendario de {unidade} nao cobre todo o periodo")
    return X[COLS_EXOG]


def skus_regulares(matriz: pd.DataFrame, aberta: pd.Series, origem: pd.Timestamp) -> list[str]:
    """SKUs com ADI < 1,32 (em dias de loja aberta) e span >= 180 dias, usando so dados
    anteriores a origem."""
    treino = matriz[matriz.index < origem]
    vendeu = treino > 0
    dias = vendeu.sum()
    tem = dias >= 2
    primeira = vendeu.idxmax()[tem]                      # 1o dia com venda
    span = ((origem - pd.Timedelta(days=1)) - primeira).dt.days + 1
    # Dias de loja aberta da 1a venda ate a vespera da origem.
    abertos_acum = aberta[aberta.index < origem].cumsum()
    abertos = abertos_acum.iloc[-1] - abertos_acum.reindex(primeira.values).values + aberta.reindex(primeira.values).values
    adi = pd.Series(abertos, index=primeira.index) / dias[tem]
    ok = (adi < ADI_CORTE) & (span >= MIN_SPAN_DIAS)
    return sorted(ok[ok].index)


# --------------------------------------------------------------------------- #
# Ajustes (rodam em processos separados)
# --------------------------------------------------------------------------- #
_G: dict = {}


def _init(y_unidade, matriz, X):
    _G["y"], _G["m"], _G["X"] = y_unidade, matriz, X


def _serie_sku(sku: str, ate: pd.Timestamp) -> pd.Series:
    s = _G["m"][sku]
    s = s[s.index < ate]
    return s[s.index >= s[s > 0].index.min()]            # comeca na 1a venda do SKU


def _ordem_sku(args):
    sku, origem = args
    s = _serie_sku(sku, origem)
    try:
        return sku, selecionar_ordem(s, _G["X"].loc[s.index])   # serie crua, como no L1
    except RuntimeError:
        return sku, None


def _prever(y: pd.Series, ordem: dict, futuro: pd.DatetimeIndex, log: bool):
    res = ajustar(transformar(y, log), _G["X"].loc[y.index], ordem["order"],
                  ordem["seasonal_order"])
    fc = res.get_forecast(len(futuro), exog=_G["X"].loc[futuro])
    mu, ic = np.asarray(fc.predicted_mean), np.asarray(fc.conf_int(alpha=ALPHA))
    volta = lambda v: np.clip(destransformar(v, log), 0, None)  # noqa: E731
    return volta(mu), volta(ic[:, 0]), volta(ic[:, 1])


def _rodada(args) -> list[dict]:
    origem, skus, ordens, ordem_l1 = args
    y, m = _G["y"], _G["m"]
    futuro = pd.date_range(origem, periods=HORIZONTE, freq="D")
    treino_u = y[y.index < origem]
    linhas = []

    l1 = {}
    for var, log in VARIANTES.items():
        try:
            l1[var] = _prever(treino_u, ordem_l1, futuro, log)
        except Exception:  # noqa: BLE001
            l1[var] = None

    for sku in skus:
        s = _serie_sku(sku, origem)
        real = m.loc[futuro, sku].values
        ult7 = s.values[-M:]
        naive = np.array([ult7[i % M] for i in range(HORIZONTE)])
        escala = float(np.mean(np.abs(s.values[M:] - s.values[:-M])))
        u8 = treino_u.iloc[-JANELA_8SEM:].sum()
        share = {
            "desag_8sem": float(s.iloc[-JANELA_8SEM:].sum() / u8) if u8 > 0 else 0.0,
            "desag_hist": float(s.sum() / treino_u.loc[s.index].sum()),
        }
        for var, log in VARIANTES.items():
            prev = {}
            if ordens.get(sku):
                try:
                    prev["sarimax_sku"] = _prever(s, ordens[sku], futuro, log)
                except Exception:  # noqa: BLE001
                    pass
            if l1[var] is not None:
                for met, sh in share.items():
                    prev[met] = tuple(v * sh for v in l1[var])
            for met, (p, lo, hi) in prev.items():
                for h in range(HORIZONTE):
                    linhas.append({
                        "origem": origem, "data": futuro[h], "horizonte": h + 1, "sku": sku,
                        "variante": var, "metodo": met, "previsto": p[h], "ic_inf": lo[h],
                        "ic_sup": hi[h], "real": real[h], "naive": naive[h], "escala": escala,
                    })
    return linhas


# --------------------------------------------------------------------------- #
# Metricas
# --------------------------------------------------------------------------- #
def _bloco(d: pd.DataFrame, janela_completa: bool = True) -> dict:
    """Metricas de um conjunto de previsoes.

    `janela_completa=False` e para um recorte por horizonte (h = 1, h = 2, ...): cada
    SKU-rodada tem um dia so, entao `vence_naive_pct` vira "% de dias" e o erro do total de
    14 dias nao existe.
    """
    ae = (d["real"] - d["previsto"]).abs()
    ae_n = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    com_escala = d["escala"] > 0
    # Por SKU e rodada: soma dos 14 dias (o numero que a loja usa para o pedido).
    q = d.assign(ae=ae, ae_n=ae_n).groupby(["origem", "sku"]).agg(
        prev=("previsto", "sum"), real=("real", "sum"), ae=("ae", "sum"), ae_n=("ae_n", "sum"))
    cob = float(dentro.mean() * 100)
    mase = float((ae[com_escala] / d.loc[com_escala, "escala"]).mean())
    b = {
        "n_dias": int(len(d)), "n_sku_rodada": int(len(q)),
        "mae": round(float(ae.mean()), 2),
        "mase": round(mase, 3),
        "erro_relativo_naive": round(float(ae.sum() / ae_n.sum()), 3) if ae_n.sum() else None,
        "vence_naive_pct": round(float((q["ae"] < q["ae_n"]).mean() * 100), 1),
        "cobertura_ic95_pct": round(cob, 1),
        "largura_ic95": round(float((d["ic_sup"] - d["ic_inf"]).mean()), 2),
        "previsto_sobre_real_pct": round(float(d["previsto"].sum() / d["real"].sum() * 100), 1),
        "passa_criterio_diario": bool(mase < 1.0 and 90.0 <= cob <= 98.0),
    }
    if janela_completa:
        b["erro_total_14d_pct"] = round(float((q["prev"] - q["real"]).abs().sum()
                                              / q["real"].sum() * 100), 1)
    return b


def blocos(d: pd.DataFrame) -> dict:
    """Mesmo formato dos treinos da loja: todos os horizontes, h = 1 e cada horizonte."""
    return {
        "geral_todos_horizontes": _bloco(d),
        "operacional_h1": _bloco(d[d["horizonte"] == 1], janela_completa=False),
        "por_horizonte": {int(h): _bloco(g, janela_completa=False)
                          for h, g in d.groupby("horizonte")},
    }


def gravar_previsoes(prev: pd.DataFrame, base: str) -> dict:
    """`_previsoes.csv` com os 14 horizontes e `_operacional.csv` so com h = 1, como na loja."""
    arquivos = {"previsoes": f"{base}_previsoes.csv", "operacional": f"{base}_operacional.csv"}
    prev.to_csv(arquivos["previsoes"], sep=";", index=False, decimal=".")
    prev[prev["horizonte"] == 1].drop(columns="horizonte").to_csv(
        arquivos["operacional"], sep=";", index=False, decimal=".")
    return arquivos


def metricas(prev: pd.DataFrame, fechados: set) -> dict:
    out = {}
    for (var, met), d in prev.groupby(["variante", "metodo"]):
        out[f"{met}|{var}"] = {"dias_abertos": blocos(d[~d["data"].isin(fechados)]),
                               "todos_os_dias": blocos(d)}
    return out


def por_sku(prev: pd.DataFrame, nomes: dict, fechados: set) -> pd.DataFrame:
    """Metricas por SKU, nos dias de loja aberta."""
    linhas = []
    for sku, d in prev[~prev["data"].isin(fechados)].groupby("sku"):
        reg = {"sku": sku, "nome": nomes.get(sku, ""),
               "rodadas": int(d["origem"].nunique()),
               "vendido_nas_rodadas": round(float(d.drop_duplicates(["origem", "data"])["real"].sum()), 1)}
        for (var, met), g in d.groupby(["variante", "metodo"]):
            ok = g["escala"] > 0
            ae = (g["real"] - g["previsto"]).abs()
            reg[f"mase|{met}|{var}"] = round(float((ae[ok] / g.loc[ok, "escala"]).mean()), 3)
            reg[f"cob|{met}|{var}"] = round(float(((g["real"] >= g["ic_inf"]) & (g["real"] <= g["ic_sup"])).mean() * 100), 1)
        mases = {k: v for k, v in reg.items() if k.startswith("mase|")}
        reg["melhor"] = min(mases, key=mases.get).removeprefix("mase|") if mases else ""
        linhas.append(reg)
    return pd.DataFrame(linhas).sort_values("vendido_nas_rodadas", ascending=False)


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def executar(slug: str, passo: int, workers: int) -> dict:
    unidade = UNIDADES[slug]
    t0 = time.time()
    print(f"=== {unidade} === (fluxo diario, origem a cada {passo} dias)", flush=True)
    fluxo, nomes = carregar_fluxo(unidade)

    idx = pd.date_range(fluxo["emissao"].min(), fluxo["emissao"].max(), freq="D")
    y = fluxo.groupby("emissao")["qtdade"].sum().reindex(idx, fill_value=0.0)
    matriz = (fluxo.groupby(["emissao", "produto_cod"])["qtdade"].sum().unstack(fill_value=0.0)
              .reindex(idx, fill_value=0.0))
    X = exogenas(unidade, idx.append(pd.date_range(idx[-1] + pd.Timedelta(days=1),
                                                   periods=HORIZONTE, freq="D")))

    origens = list(pd.date_range(PRIMEIRA_ORIGEM, idx[-1] - pd.Timedelta(days=HORIZONTE - 1),
                                 freq=f"{passo}D"))
    aberta = (X.loc[idx, "loja_fechada"] == 0).astype(int)
    regulares = {o: skus_regulares(matriz, aberta, o) for o in origens}
    todos = sorted({s for lst in regulares.values() for s in lst})
    print(f"[skus] {len(todos)} SKUs regulares em alguma rodada · por rodada: "
          f"{min(map(len, regulares.values()))}–{max(map(len, regulares.values()))}", flush=True)
    matriz = matriz[todos]

    # Ordem do L1 (fluxo, serie crua, antes da 1a origem) — a mesma dos treinos C e D.
    _init(y, matriz, X)
    pre = y[y.index < PRIMEIRA_ORIGEM]
    ordem_l1 = selecionar_ordem(pre, X.loc[pre.index])
    print(f"[L1] ordem {ordem_l1['order']}{ordem_l1['seasonal_order']}", flush=True)

    # Ordem de cada SKU: uma vez, com os dados anteriores a 1a rodada em que ele e regular.
    primeira_rodada = {s: next(o for o in origens if s in regulares[o]) for s in todos}
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(y, matriz, X)) as ex:
        ordens = dict(ex.map(_ordem_sku, primeira_rodada.items()))
        print(f"[ordens] {sum(v is not None for v in ordens.values())}/{len(todos)} SKUs "
              f"com ordem ({time.time() - t0:.0f}s)", flush=True)
        tarefas = [(o, regulares[o], ordens, ordem_l1) for o in origens]
        linhas = [l for lote in ex.map(_rodada, tarefas) for l in lote]
    prev = pd.DataFrame(linhas)
    print(f"[walk-forward] {len(origens)} rodadas · {len(prev):,} linhas "
          f"({time.time() - t0:.0f}s)", flush=True)

    config = {
        "base": "fluxo diario (sem servico e sem vendas > %d unidades no documento)" % LIMIAR_QTD_VENDA,
        "selecao_sku": {"adi_corte": ADI_CORTE, "min_span_dias": MIN_SPAN_DIAS,
                        "adi_em": "dias de loja aberta",
                        "fonte": "Syntetos, Boylan & Croston (2005); MIN_OBSERVATIONS_DAYS do L1"},
        "janela_8sem_dias": JANELA_8SEM, "passo_origem_dias": passo,
        "primeira_origem": str(PRIMEIRA_ORIGEM.date()), "n_rodadas": len(origens),
        "horizonte_dias": HORIZONTE, "variantes": list(VARIANTES), "metodos": METODOS + ["naive"],
        "ordem_l1": {"order": list(ordem_l1["order"]),
                     "seasonal_order": list(ordem_l1["seasonal_order"])},
        "skus_regulares_por_rodada": {str(o.date()): len(v) for o, v in regulares.items()},
    }
    base = os.path.join(METRICS_DIR, f"sku_regular_{slug}")
    os.makedirs(METRICS_DIR, exist_ok=True)
    gravar_previsoes(prev, base)
    saida = relatorio(slug, prev, nomes, config)
    print(f"[tempo] {time.time() - t0:.0f}s\n", flush=True)
    return saida


def fechados_da_unidade(unidade: str) -> set:
    cal = pd.read_csv(CALENDARIO, sep=";", parse_dates=["data"])
    return set(cal.loc[(cal["unidade"] == unidade) & (cal["loja_fechada"] == 1), "data"])


def relatorio(slug: str, prev: pd.DataFrame, nomes: dict, config: dict) -> dict:
    """Metricas, tabela por SKU, JSON e resumo no terminal a partir das previsoes."""
    unidade = UNIDADES[slug]
    fechados = fechados_da_unidade(unidade)
    met = metricas(prev, fechados)
    tab = por_sku(prev, nomes, fechados)
    base = os.path.join(METRICS_DIR, f"sku_regular_{slug}")
    tab.to_csv(f"{base}_por_sku.csv", sep=";", index=False, decimal=".")
    saida = {
        "unidade": unidade,
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "config": config,
        "metricas": met,
        "arquivos": {"previsoes": f"{base}_previsoes.csv",
                     "operacional": f"{base}_operacional.csv", "por_sku": f"{base}_por_sku.csv"},
    }
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)

    print(f"\n[resultado] {unidade} · dias de loja aberta")
    print(f"  {'metodo|variante':24s} {'':5s} {'MASE':>6s} {'÷naive':>7s} {'vence':>6s} {'IC95':>6s} "
          f"{'prev/real':>9s}  diario ok?")
    for k, v in met.items():
        for rot, chave in (("h1-14", "geral_todos_horizontes"), ("h=1", "operacional_h1")):
            b = v["dias_abertos"][chave]
            print(f"  {k:24s} {rot:5s} {b['mase']:6.3f} {b['erro_relativo_naive']:7.3f} "
                  f"{b['vence_naive_pct']:5.1f}% {b['cobertura_ic95_pct']:5.1f}% "
                  f"{b['previsto_sobre_real_pct']:8.1f}%  {'SIM' if b['passa_criterio_diario'] else 'nao'}")
    print(f"\n[por SKU] melhor metodo (menor MASE):\n{tab['melhor'].value_counts().to_string()}")
    print(f"[arquivos] {base}.json · _previsoes.csv · _operacional.csv · _por_sku.csv", flush=True)
    return saida


def recalcular_metricas(slug: str) -> dict:
    """Refaz metricas e JSON a partir do `_previsoes.csv` salvo, sem reajustar nada."""
    base = os.path.join(METRICS_DIR, f"sku_regular_{slug}")
    prev = pd.read_csv(f"{base}_previsoes.csv", sep=";", dtype={"sku": str},
                       parse_dates=["origem", "data"])
    gravar_previsoes(prev, base)
    with open(f"{base}.json", encoding="utf-8") as fh:
        config = json.load(fh)["config"]
    _, nomes = carregar_fluxo(UNIDADES[slug])
    return relatorio(slug, prev, nomes, config)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--unidade", choices=[*UNIDADES, "todas"], default="todas")
    ap.add_argument("--passo", type=int, default=PASSO_PADRAO, help="dias entre origens")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--so-metricas", action="store_true",
                    help="recalcula metricas a partir do _previsoes.csv ja salvo")
    a = ap.parse_args()
    for slug in (UNIDADES if a.unidade == "todas" else [a.unidade]):
        if a.so_metricas:
            recalcular_metricas(slug)
        else:
            executar(slug, a.passo, a.workers)


if __name__ == "__main__":
    main()
