"""EDA 4 — Separar por unidade e por categoria melhora a previsão?

O L1 prevê uma série por `unidade × categoria` (6 séries). Cada nível de separação só se
justifica se prever a parte com o próprio modelo erra menos do que prever o agregado e
repartir o resultado pela participação recente da parte (top-down) — a alternativa sem
custo de modelo adicional.

Níveis testados (mesmo desenho do `eda_grupos.py`: walk-forward de 26 janelas de 14 dias,
dois previsores, MASE):
  * unidades:   Jardim Canadá e Itabirito × o total da rede
  * categorias: Grama, Flores de corte e Produtos de jardim × o total de cada unidade

Regra fixada antes de rodar, por parte: a separação se justifica se o modelo direto ganha
pelo menos GANHO_MINIMO de MASE da melhor repartição com os DOIS previsores. Também é
reportado se a soma das partes piora o agregado (bottom-up).

Saídas: results/plots/eda/23_separacao_teste_previsao_mase.png e
results/metrics/eda_separacao.json
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import _common as C
from .eda_grupos import (
    GANHO_MINIMO, HORIZONTE, N_FOLDS, PERDA_MAXIMA_TOTAL, _AJUSTES, _agrega, _erros,
    _exog_calendario, _participacoes, _prever_ets, _prever_sarimax,
)

warnings.filterwarnings("ignore")

TOTAL = "Total da rede"


def _series(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Uma série diária por unidade × categoria, mais o total de cada unidade e da rede,
    todas no mesmo calendário (dias sem venda = 0)."""
    d = df[df["categoria"] != C.NAO_PRODUTO].dropna(subset=["data"])
    idx = pd.date_range(d["data"].min().normalize(), d["data"].max().normalize(), freq="D")
    out: dict[str, pd.Series] = {}
    for u in C.UNIDADES:
        for c in C.CATEGORIAS_L1:
            x = d[(d["unidade"] == u) & (d["categoria"] == c)]
            out[f"{u} · {c}"] = x.groupby(x["data"].dt.normalize())["qtdade_n"].sum().reindex(idx, fill_value=0.0)
        out[u] = sum(out[f"{u} · {c}"] for c in C.CATEGORIAS_L1)
    out[TOTAL] = sum(out[u] for u in C.UNIDADES)
    return out


def _previsoes(series: dict[str, pd.Series], previsor: str) -> dict[str, list[dict]]:
    """Previsão de cada série em cada janela (ajusta uma vez, reaproveita nas comparações)."""
    idx = next(iter(series.values())).index
    n = len(idx)
    x_all = _exog_calendario(pd.date_range(idx[0], idx[-1] + pd.Timedelta(days=HORIZONTE), freq="D"))
    out: dict[str, list[dict]] = {k: [] for k in series}
    for i in range(N_FOLDS):
        ini = n - (N_FOLDS - i) * HORIZONTE
        fut = idx[ini:ini + HORIZONTE]
        for k, s in series.items():
            tr = s.iloc[:ini]
            fc = _prever_sarimax(tr, fut, x_all) if previsor == "sarimax" else _prever_ets(tr, fut)
            out[k].append({"fut": fut, "tr": tr, "real": s.iloc[ini:ini + HORIZONTE].clip(lower=0).values, "fc": fc})
    return out


def _janelas_com_data(idx: pd.DatetimeIndex) -> list[bool]:
    """Quais das N_FOLDS janelas de teste contêm dia de data comemorativa (ou os 2 anteriores)."""
    datas = pd.DatetimeIndex(C.datas_comemorativas(range(idx.year.min(), idx.year.max() + 1))["data"]).normalize()
    janela = datas.union(datas - pd.Timedelta(days=1)).union(datas - pd.Timedelta(days=2))
    n = len(idx)
    return [bool(idx[n - (N_FOLDS - i) * HORIZONTE:n - (N_FOLDS - i) * HORIZONTE + HORIZONTE].isin(janela).any())
            for i in range(N_FOLDS)]


def _compara(prev: dict, parte: str, pai: str, com_data: list[bool]) -> dict:
    """Modelo direto da parte × repartição da previsão do pai (nível e dia da semana)."""
    direto, nivel, dow = [], [], []
    for a, b in zip(prev[parte], prev[pai]):
        direto.append(_erros(a["real"], a["fc"], a["tr"]))
        n, d = _participacoes(b["tr"], a["tr"], a["fut"])
        nivel.append(_erros(a["real"], b["fc"] * n, a["tr"]))
        dow.append(_erros(a["real"], b["fc"] * d, a["tr"]))
    out = {"direto": _agrega(direto), "reparticao_nivel": _agrega(nivel), "reparticao_dow": _agrega(dow)}
    # Mesma comparação só nas janelas com / sem data comemorativa (a melhor repartição no geral)
    melhor = nivel if out["reparticao_nivel"]["mase"] <= out["reparticao_dow"]["mase"] else dow
    for rot, flag in (("janelas_com_data", True), ("janelas_sem_data", False)):
        ids = [i for i, f in enumerate(com_data) if f is flag]
        out[rot] = {"n_janelas": len(ids),
                    "mase_direto": float(np.nanmean([direto[i]["mase"] for i in ids])),
                    "mase_reparticao": float(np.nanmean([melhor[i]["mase"] for i in ids]))}
    return out


def _soma_das_partes(prev: dict, partes: list[str], pai: str) -> dict:
    """Bottom-up: soma dos modelos das partes × modelo do pai, no erro do pai."""
    direto, soma = [], []
    for i, b in enumerate(prev[pai]):
        direto.append(_erros(b["real"], b["fc"], b["tr"]))
        soma.append(_erros(b["real"], sum(prev[p][i]["fc"] for p in partes), b["tr"]))
    return {"direto": _agrega(direto), "soma_das_partes": _agrega(soma)}


def _estrutura() -> list[tuple[str, str, list[str]]]:
    """(nível, pai, partes)."""
    est = [("unidade", TOTAL, list(C.UNIDADES))]
    est += [("categoria", u, [f"{u} · {c}" for c in C.CATEGORIAS_L1]) for u in C.UNIDADES]
    return est


def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    series = _series(df)
    estrutura = _estrutura()
    com_data = _janelas_com_data(next(iter(series.values())).index)

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "parametros": {"N_FOLDS": N_FOLDS, "HORIZONTE": HORIZONTE, "GANHO_MINIMO": GANHO_MINIMO,
                       "PERDA_MAXIMA_TOTAL": PERDA_MAXIMA_TOTAL,
                       "regra": f"a separação se justifica se o modelo direto ganha ≥ {GANHO_MINIMO:.0%} de MASE "
                                "da melhor repartição do pai, com SARIMAX e com Holt-Winters"},
        "participacao_no_pai_pct": {},
        "por_previsor": {},
    }
    for nivel, pai, partes in estrutura:
        for p in partes:
            resultado["participacao_no_pai_pct"][f"{p} ← {pai}"] = round(float(series[p].sum() / series[pai].sum() * 100), 1)

    for previsor in ("sarimax", "ets"):
        prev = _previsoes(series, previsor)
        r = {}
        for nivel, pai, partes in estrutura:
            r[pai] = {"nivel": nivel,
                      "partes": {p: _compara(prev, p, pai, com_data) for p in partes},
                      "agregado": _soma_das_partes(prev, partes, pai)}
        resultado["por_previsor"][previsor] = r
    resultado["3a_ajustes_sarimax"] = dict(_AJUSTES)

    # Veredito por parte
    veredito = {}
    for nivel, pai, partes in estrutura:
        for p in partes:
            ganhos = {}
            for previsor in ("sarimax", "ets"):
                c = resultado["por_previsor"][previsor][pai]["partes"][p]
                melhor = min(c["reparticao_nivel"]["mase"], c["reparticao_dow"]["mase"])
                ganhos[previsor] = round(float(1 - c["direto"]["mase"] / melhor) * 100, 1)
            veredito[p] = {"pai": pai, "nivel": nivel, "ganho_mase_pct": ganhos,
                           "separar_se_justifica": bool(min(ganhos.values()) >= GANHO_MINIMO * 100)}
    resultado["veredito_por_parte"] = veredito

    # Gráfico: MASE direto × repartição (SARIMAX) por parte
    partes_plot = [(p, v["pai"]) for p, v in veredito.items()]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    x = np.arange(len(partes_plot))
    dir_, rep_ = [], []
    for p, pai in partes_plot:
        c = resultado["por_previsor"]["sarimax"][pai]["partes"][p]
        dir_.append(c["direto"]["mase"]); rep_.append(min(c["reparticao_nivel"]["mase"], c["reparticao_dow"]["mase"]))
    ax.bar(x - .18, dir_, .36, label="modelo próprio da parte", color="#00838F")
    ax.bar(x + .18, rep_, .36, label="previsão do agregado repartida", color="#B0BEC5")
    ax.axhline(1, color="#B71C1C", lw=.8, ls="--")
    ax.set_xticks(x, [p.replace(" · ", "\n") if " · " in p else p for p, _ in partes_plot], fontsize=8)
    ax.set_ylabel("MASE (h = 14 d, 26 folds, SARIMAX)"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("Separar por unidade e por categoria: modelo próprio × repartição do agregado")
    resultado["graficos"] = [C.savefig(fig, "23_separacao_teste_previsao_mase.png")]
    path = C.dump_metrics("eda_separacao.json", resultado)

    print("[eda_separacao] participação da parte no agregado (%)")
    for k, v in resultado["participacao_no_pai_pct"].items():
        print(f"[eda_separacao]   {k:<52}{v:>6}")
    print("[eda_separacao] MASE SARIMAX / Holt-Winters: direto × melhor repartição  → ganho %")
    for p, v in veredito.items():
        s, e = (resultado["por_previsor"][k][v["pai"]]["partes"][p] for k in ("sarimax", "ets"))
        f = lambda c: (c["direto"]["mase"], min(c["reparticao_nivel"]["mase"], c["reparticao_dow"]["mase"]))
        print(f"[eda_separacao] {p:<38} S {f(s)[0]:.3f}×{f(s)[1]:.3f}  H {f(e)[0]:.3f}×{f(e)[1]:.3f}  "
              f"ganho {v['ganho_mase_pct']}  separar={v['separar_se_justifica']}")
    print("[eda_separacao] MASE direto × repartição, janelas COM data comemorativa | SEM (SARIMAX / Holt-Winters)")
    for p, v in veredito.items():
        linha = []
        for k in ("sarimax", "ets"):
            c = resultado["por_previsor"][k][v["pai"]]["partes"][p]
            linha.append(" ".join(f"{c[j]['mase_direto']:.2f}×{c[j]['mase_reparticao']:.2f}" for j in ("janelas_com_data", "janelas_sem_data")))
        n = resultado["por_previsor"]["sarimax"][v["pai"]]["partes"][p]["janelas_com_data"]["n_janelas"]
        print(f"[eda_separacao] {p:<38} (n={n}) S {linha[0]}  H {linha[1]}")
    print("[eda_separacao] agregado: direto × soma das partes (MASE, SARIMAX)")
    for pai, r in resultado["por_previsor"]["sarimax"].items():
        print(f"[eda_separacao]   {pai:<20}{r['agregado']['direto']['mase']:.3f} × {r['agregado']['soma_das_partes']['mase']:.3f}")
    print(f"[eda_separacao] métricas: {path}")
    return resultado


if __name__ == "__main__":
    main()
