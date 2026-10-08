"""EDA 7 — A regra de encomenda (K × dia típico) contra o filtro de Hampel.

O ADR-012 marca como encomenda a linha de venda cuja quantidade supera K = 5 dias típicos
(mediana do volume diário, dias com venda, seg–sáb) da própria `unidade × categoria`.
Nenhum trabalho publicado usa exatamente esse limiar. Este EDA mede o quanto ele coincide
com o critério robusto clássico da literatura, o identificador de Hampel
(mediana ± t × MAD; Hampel, 1974; Pearson et al., 2016), aplicado ao mesmo contexto.

Regras comparadas (todas por `unidade × categoria`, limiar da base inteira, só descritivo):

  projeto        q > K × mediana(D)                                    K = 5
  hampel_log     log q > mediana(log D) + t × 1,4826 × MAD(log D)       t = 2,5 · 3 · 3,5
  hampel_bruto   q > mediana(D) + t × 1,4826 × MAD(D)                   t = 3
  hampel_linhas  log q > mediana(log L) + t × 1,4826 × MAD(log L)       t = 3

  D = volume diário do par (dias com venda, seg–sáb), a mesma amostra do "dia típico".
  L = quantidade das próprias linhas de venda do par (outra referência possível).

Em escala log, a regra do projeto é log q > log mediana(D) + log 5: uma distância fixa da
mediana. O `hampel_log` é a mesma ideia com a distância proporcional à dispersão do par,
o que dá um "K equivalente" = limiar ÷ mediana(D) para comparar com 5.

Para cada regra alternativa: linhas e volume marcados, sobreposição com a regra do projeto
(linhas nas duas, só numa, Jaccard) e o perfil das linhas de cada grupo (% pagas por boleto,
% de "CONSUMIDOR"), que não entram em nenhuma regra e servem de validação externa.

Saídas: results/plots/eda/28_encomendas_hampel.png e results/metrics/eda_encomendas_hampel.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..preprocessing.encomendas import K_DIAS_TIPICOS, limiares_encomenda, marcar_encomendas
from . import _common as C

ESCALA_MAD = 1.4826          # torna o MAD consistente com o desvio-padrão sob normalidade
T_HAMPEL = (2.5, 3.0, 3.5)   # 3 é o valor clássico; 2,5 é o recomendado por Leys et al. (2013)
T_PADRAO = 3.0


# --------------------------------------------------------------------------- #
# Limiares
# --------------------------------------------------------------------------- #
def _volume_diario(df: pd.DataFrame) -> pd.Series:
    """Mesma amostra de `limiares_encomenda`: volume diário do par, seg–sáb, dias com venda."""
    diario = df.groupby(["unidade", "categoria", df["data"].dt.normalize()])["qtdade_n"].sum()
    diario = diario[diario.index.get_level_values(2).weekday < 6]
    return diario[diario > 0]


def _centro_escala(x: pd.Series) -> tuple[float, float]:
    med = float(x.median())
    return med, ESCALA_MAD * float((x - med).abs().median())


def limiares_hampel(df: pd.DataFrame) -> dict[str, dict[tuple[str, str], float]]:
    """Limiar de quantidade por linha, por regra e por (unidade, categoria)."""
    diario = _volume_diario(df)
    out: dict[str, dict] = {f"hampel_log_t{t:g}": {} for t in T_HAMPEL}
    out["hampel_bruto_t3"], out["hampel_linhas_t3"] = {}, {}
    for (u, c), d in diario.groupby(level=[0, 1]):
        med_log, s_log = _centro_escala(np.log(d))
        for t in T_HAMPEL:
            out[f"hampel_log_t{t:g}"][(u, c)] = float(np.exp(med_log + t * s_log))
        med, s = _centro_escala(d)
        out["hampel_bruto_t3"][(u, c)] = med + T_PADRAO * s
        linhas = df.loc[(df["unidade"] == u) & (df["categoria"] == c) & (df["qtdade_n"] > 0), "qtdade_n"]
        med_l, s_l = _centro_escala(np.log(linhas))
        out["hampel_linhas_t3"][(u, c)] = float(np.exp(med_l + T_PADRAO * s_l))
    return out


# --------------------------------------------------------------------------- #
# Comparação
# --------------------------------------------------------------------------- #
def _perfil(g: pd.DataFrame, m: pd.Series) -> dict:
    if not m.any():
        return {"linhas": 0, "pct_boleto": None, "pct_consumidor": None}
    return {"linhas": int(m.sum()),
            "pct_boleto": round(float(g.loc[m, "_boleto"].mean() * 100), 1),
            "pct_consumidor": round(float(g.loc[m, "_consumidor"].mean() * 100), 1)}


def compara(g: pd.DataFrame, proj: pd.Series, alt: pd.Series) -> dict:
    vol = g["qtdade_n"].clip(lower=0)
    total = vol.sum()
    ambas, uniao = proj & alt, proj | alt
    return {
        "linhas_projeto": int(proj.sum()),
        "linhas_alternativa": int(alt.sum()),
        "linhas_ambas": int(ambas.sum()),
        "linhas_so_projeto": int((proj & ~alt).sum()),
        "linhas_so_alternativa": int((alt & ~proj).sum()),
        "jaccard_linhas": round(float(ambas.sum() / uniao.sum()), 3) if uniao.any() else None,
        "pct_volume_projeto": round(float(vol[proj].sum() / total * 100), 1),
        "pct_volume_alternativa": round(float(vol[alt].sum() / total * 100), 1),
        "pct_volume_ambas_na_uniao": round(float(vol[ambas].sum() / vol[uniao].sum() * 100), 1) if uniao.any() else None,
        "perfil": {"marcadas_projeto": _perfil(g, proj), "marcadas_alternativa": _perfil(g, alt),
                   "ambas": _perfil(g, ambas), "so_projeto": _perfil(g, proj & ~alt),
                   "so_alternativa": _perfil(g, alt & ~proj), "nenhuma": _perfil(g, ~uniao)},
    }


# --------------------------------------------------------------------------- #
# Gráfico
# --------------------------------------------------------------------------- #
def grafico(k_equiv: dict, por_unidade: dict, plt) -> str:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={"width_ratios": [1.6, 1]})

    pares = list(k_equiv)
    x = np.arange(len(pares))
    lo = [k_equiv[p][f"hampel_log_t{T_HAMPEL[0]:g}"] for p in pares]
    hi = [k_equiv[p][f"hampel_log_t{T_HAMPEL[-1]:g}"] for p in pares]
    mid = [k_equiv[p]["hampel_log_t3"] for p in pares]
    ax1.vlines(x, lo, hi, color="#00838F", lw=5, alpha=.35, label=f"Hampel em log, t = {T_HAMPEL[0]:g} a {T_HAMPEL[-1]:g}")
    ax1.scatter(x, mid, color="#00838F", zorder=3, label="Hampel em log, t = 3")
    ax1.scatter(x, [k_equiv[p]["hampel_bruto_t3"] for p in pares], marker="x", color="#6D4C41", zorder=3,
                label="Hampel na escala original, t = 3")
    ax1.axhline(K_DIAS_TIPICOS, color="#D84315", lw=1.2, ls="--", label=f"regra do projeto (K = {K_DIAS_TIPICOS})")
    ax1.set_yscale("log")
    ax1.set_xticks(x, [p.replace(" · ", "\n") for p in pares], fontsize=8)
    ax1.set_ylabel("limiar da linha ÷ dia típico (K equivalente)")
    ax1.set_title("Quantos dias típicos cada regra exige para marcar uma linha")
    ax1.legend(frameon=False, fontsize=8)

    us = list(por_unidade)
    regras = (("hampel_bruto_t3", "Hampel\noriginal"), ("hampel_log_t3", "Hampel\nlog"))
    pos, rot = [], []
    for i, u in enumerate(us):
        for j, (r, nome) in enumerate(regras):
            c = por_unidade[u][r]
            x0 = i * 2.6 + j
            tot = c["_vol_total"]
            amb, sp, sa = (c[k] / tot * 100 for k in ("_vol_ambas", "_vol_so_projeto", "_vol_so_alternativa"))
            primeira = i == 0 and j == 0
            ax2.bar(x0, amb, color="#455A64", label="marcada pelas duas" if primeira else None)
            ax2.bar(x0, sp, bottom=amb, color="#D84315", label="só pela regra do projeto" if primeira else None)
            ax2.bar(x0, sa, bottom=amb + sp, color="#00838F", label="só pelo Hampel (t = 3)" if primeira else None)
            ax2.text(x0, amb + sp + sa + .6, f"J {c['jaccard_linhas']:.2f}", ha="center", fontsize=8)
            pos.append(x0)
            rot.append(f"{nome}\n{u}")
    ax2.set_xticks(pos, rot, fontsize=8)
    ax2.set_ylabel("% do volume da unidade")
    ax2.set_title("Volume marcado como encomenda (J = Jaccard das linhas)")
    ax2.legend(frameon=False, fontsize=8, loc="upper right")

    fig.suptitle("Regra de encomenda do projeto × identificador de Hampel, por unidade × categoria")
    fig.tight_layout()
    return C.savefig(fig, "28_encomendas_hampel.png")


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    df = df[df["categoria"] != C.NAO_PRODUTO].dropna(subset=["data"]).copy()
    df["_boleto"] = df["pagamento"].fillna("").str.upper().str.strip() == "BOLETO"
    df["_consumidor"] = df["cliente_cod"].astype(str).str.strip() == "1"   # "CONSUMIDOR" no ERP

    lim_proj = limiares_encomenda(df)
    proj = marcar_encomendas(df, lim_proj)
    lim_alt = limiares_hampel(df)
    marcas = {r: marcar_encomendas(df, lim) for r, lim in lim_alt.items()}
    dia_tipico = {k: v / K_DIAS_TIPICOS for k, v in lim_proj.items()}

    k_equiv = {f"{u} · {c}": {r: round(lim_alt[r][(u, c)] / dia_tipico[(u, c)], 2) for r in lim_alt}
               for (u, c) in sorted(lim_proj)}
    limiares = {f"{u} · {c}": {"dia_tipico": round(dia_tipico[(u, c)], 1), "projeto": round(lim_proj[(u, c)], 1),
                               **{r: round(lim_alt[r][(u, c)], 1) for r in lim_alt}}
                for (u, c) in sorted(lim_proj)}

    por_par, por_unidade = {}, {}
    for (u, c), g in df.groupby(["unidade", "categoria"]):
        por_par[f"{u} · {c}"] = {r: compara(g, proj.loc[g.index], m.loc[g.index]) for r, m in marcas.items()}
    for u, g in df.groupby("unidade"):
        por_unidade[u] = {}
        vol = g["qtdade_n"].clip(lower=0)
        for r, m in marcas.items():
            p, a = proj.loc[g.index], m.loc[g.index]
            res = compara(g, p, a)
            res.update({"_vol_total": float(vol.sum()), "_vol_ambas": float(vol[p & a].sum()),
                        "_vol_so_projeto": float(vol[p & ~a].sum()), "_vol_so_alternativa": float(vol[a & ~p].sum())})
            por_unidade[u][r] = res

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "parametros": {"K_DIAS_TIPICOS": K_DIAS_TIPICOS, "T_HAMPEL": list(T_HAMPEL), "ESCALA_MAD": ESCALA_MAD,
                       "amostra_dia_tipico": "volume diário da unidade × categoria, dias com venda, seg–sáb",
                       "limiares": "calculados na base inteira (descritivo, como o bloco 1 do EDA 6)"},
        "limiares_por_par": limiares,
        "k_equivalente_por_par": k_equiv,
        "comparacao_por_par": por_par,
        "comparacao_por_unidade": {u: {r: {k: v for k, v in res.items() if not k.startswith("_")}
                                       for r, res in rs.items()} for u, rs in por_unidade.items()},
    }
    resultado["graficos"] = [grafico(k_equiv, por_unidade, plt)]
    path = C.dump_metrics("eda_encomendas_hampel.json", resultado)

    print(f"[eda_hampel] K equivalente (limiar ÷ dia típico); projeto = {K_DIAS_TIPICOS}")
    for par, k in k_equiv.items():
        print(f"[eda_hampel]   {par:<36} " + " · ".join(f"{r} {v:g}" for r, v in k.items()))
    print("[eda_hampel] por unidade: linhas proj/alt/ambas · Jaccard · %vol proj/alt · "
          "% boleto (marcadas proj | marcadas alt | ambas | só proj | só alt | nenhuma)")
    for u, rs in resultado["comparacao_por_unidade"].items():
        for r, v in rs.items():
            pf = v["perfil"]
            print(f"[eda_hampel]   {u:<14}{r:<20} {v['linhas_projeto']:>4}/{v['linhas_alternativa']:>5}/{v['linhas_ambas']:>4} · "
                  f"J {v['jaccard_linhas']} · {v['pct_volume_projeto']}%/{v['pct_volume_alternativa']}% · "
                  + " | ".join(str(pf[k]["pct_boleto"]) for k in
                               ("marcadas_projeto", "marcadas_alternativa", "ambas", "so_projeto", "so_alternativa", "nenhuma")))
    print(f"[eda_hampel] métricas: {path}  ·  gráfico: {resultado['graficos'][0]}")
    return resultado


if __name__ == "__main__":
    main()
