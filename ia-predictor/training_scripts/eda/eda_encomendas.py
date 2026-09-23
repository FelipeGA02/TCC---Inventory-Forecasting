"""EDA 6 — Encomendas grandes: separar do balcão e aplicar teto melhora o L1?

O EDA 2 deixou Itabirito com MASE 1,43 (SARIMAX direto, `eda_separacao`) — pior que a
naïve semanal. A causa são poucas linhas de venda enormes (Grama de obra/paisagismo,
faturada por boleto) que o modelo não tem como antecipar. Este EDA testa a solução do
ADR-012, implementada em `preprocessing/encomendas.py`:

  1. separar as linhas de encomenda (quantidade > K dias típicos da unidade × categoria)
     da venda de balcão, e prever com o L1 só o balcão;
  2. aplicar teto (winsorização no p99 dos dias abertos) à série de balcão do treino.

Blocos:
  1. Quem são as encomendas: linhas, volume, dias, meio de pagamento, concentração de
     clientes (só agregados — nenhum identificador de cliente sai daqui)
  2. Teste de previsão (walk-forward, 26 janelas de 14 dias, SARIMAX e Holt-Winters),
     quatro variantes por unidade:
       original       total → total                (L1 de hoje)
       so_teto        teto(total) → total          (só a camada 2)
       so_separar     balcão → balcão              (só a camada 1)
       separar_teto   teto(balcão) → balcão        (solução combinada)
     mais `separar_teto_vs_total` (a previsão da solução contra o total real, para medir
     o quanto do erro passa a ser da encomenda não prevista) e a sensibilidade a K.
     Limiares e teto saem só do treino de cada janela; o MASE usa a escala da série real
     (sem teto) do treino.
  3. Antes × depois: a bateria de diagnóstico do EDA 2 (`eda_series.analisa_serie`) na
     série total e na de balcão (com e sem teto) — CV, força sazonal, autocorrelação,
     tendência, outliers, classe de Syntetos-Boylan-Croston e veredito

Saídas: results/plots/eda/25_encomendas_series.png, 26_encomendas_mase.png e
results/metrics/eda_encomendas.json
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from ..preprocessing.encomendas import (
    K_DIAS_TIPICOS, QUANTIL_TETO, limiares_encomenda, marcar_encomendas, teto_quantil,
)
from . import _common as C
from .eda_series import analisa_serie
from .eda_grupos import (
    HORIZONTE, N_FOLDS, _agrega, _erros, _exog_calendario, _prever_ets, _prever_sarimax,
)

warnings.filterwarnings("ignore")

K_SENSIBILIDADE = (3, K_DIAS_TIPICOS, 10)
VARIANTES = ("original", "so_teto", "so_separar", "separar_teto")


def _diaria(linhas: pd.DataFrame, idx: pd.DatetimeIndex) -> pd.Series:
    return (linhas.groupby(linhas["data"].dt.normalize())["qtdade_n"].sum()
            .reindex(idx, fill_value=0.0))


# --------------------------------------------------------------------------- #
# Bloco 1 — perfil das encomendas (limiar calculado na base inteira, só descritivo)
# --------------------------------------------------------------------------- #
def bloco_perfil(df: pd.DataFrame) -> dict:
    lim = limiares_encomenda(df)
    enc = marcar_encomendas(df, lim)
    pag = df["pagamento"].fillna("").str.upper().str.strip()
    consumidor = df["cliente_cod"].astype(str).str.strip() == "1"   # "CONSUMIDOR" no ERP
    out = {"k_dias_tipicos": K_DIAS_TIPICOS, "por_par": {}, "por_unidade": {}}
    for (u, c), g in df.groupby(["unidade", "categoria"]):
        m = enc.loc[g.index]
        out["por_par"][f"{u} · {c}"] = {
            "limiar_qtd_linha": round(lim[(u, c)], 1),
            "linhas_encomenda": int(m.sum()),
            "pct_volume_encomenda": round(float(g.loc[m, "qtdade_n"].sum() / g["qtdade_n"].sum() * 100), 1),
            "dias_com_encomenda": int(g.loc[m, "data"].dt.normalize().nunique()),
        }
    for u, g in df.groupby("unidade"):
        m = enc.loc[g.index]
        e = g[m]
        top = e.groupby("cliente_cod")["qtdade_n"].sum().sort_values(ascending=False)
        idx = pd.date_range(g["data"].min().normalize(), g["data"].max().normalize(), freq="D")
        total, balcao = _diaria(g, idx), _diaria(g[~m], idx)
        cv = lambda s: round(float(s.std() / s.mean()), 2)
        out["por_unidade"][u] = {
            "linhas_encomenda": int(m.sum()),
            "pct_volume_encomenda": round(float(e["qtdade_n"].sum() / g["qtdade_n"].sum() * 100), 1),
            "dias_com_encomenda": int(e["data"].dt.normalize().nunique()),
            "clientes_distintos_encomenda": int(e["cliente_cod"].nunique()),
            "pct_volume_encomenda_maior_cliente": round(float(top.iloc[0] / top.sum() * 100), 1) if len(top) else None,
            "pct_linhas_boleto": {"encomenda": round(float((pag[e.index] == "BOLETO").mean() * 100), 1),
                                  "balcao": round(float((pag[g.index[~m.values]] == "BOLETO").mean() * 100), 1)},
            "pct_linhas_consumidor_final": {"encomenda": round(float(consumidor[e.index].mean() * 100), 1),
                                            "balcao": round(float(consumidor[g.index[~m.values]].mean() * 100), 1)},
            "cv": {"total": cv(total), "balcao": cv(balcao), "balcao_teto": cv(teto_quantil(balcao))},
        }
    return out


# --------------------------------------------------------------------------- #
# Bloco 3 — antes × depois: mesmo diagnóstico do EDA 2 na série total e na de balcão
# --------------------------------------------------------------------------- #
def _resumo_serie(s: pd.Series, linhas: pd.DataFrame) -> dict:
    r = analisa_serie(s, linhas)
    d, sz, t, a = r["2_distribuicao"], r["3_sazonalidade_semanal"], r["5_tendencia"], r["7_autocorrelacao"]
    venda = s[s > 0]
    adi = len(s) / len(venda)
    cv2 = float((venda.std() / venda.mean()) ** 2)
    return {
        "media_diaria": d["media"], "cv": d["cv"], "p99": d["p99"], "razao_max_media": d["razao_max_media"],
        "assimetria": d["assimetria_skew"], "curtose": d["curtose"],
        "forca_sazonal_semanal": sz["forca_sazonal_semanal"], "acf_lag7": a["acf_lag7"],
        "ljung_box_lag7_pvalue": a["ljung_box_lag7_pvalue"],
        "tendencia_pct_ano": t["inclinacao_pct_da_media_por_ano"],
        "media_primeiros_90d": t["media_primeiros_90d"], "media_ultimos_90d": t["media_ultimos_90d"],
        "dias_acima_3sigma": r["8_outliers"]["n_dias_acima_3sigma"],
        "adi": adi, "cv2": cv2,
        "classe_sbc": ("suave" if cv2 < 0.49 else "erratico") if adi < 1.32 else ("intermitente" if cv2 < 0.49 else "lumpy"),
        "veredito_sarimax": r["9_veredito_sarimax"]["nivel"],
    }


def bloco_antes_depois(df: pd.DataFrame) -> dict:
    enc = marcar_encomendas(df, limiares_encomenda(df))
    out = {}
    for u in C.UNIDADES:
        g = df[df["unidade"] == u]
        idx = pd.date_range(g["data"].min().normalize(), g["data"].max().normalize(), freq="D")
        balcao = g[~enc.loc[g.index].values]
        s_bal = _diaria(balcao, idx)
        out[u] = {"antes_total": _resumo_serie(_diaria(g, idx), g),
                  "depois_balcao": _resumo_serie(s_bal, balcao),
                  "depois_balcao_teto": _resumo_serie(teto_quantil(s_bal), balcao)}
    return out


# --------------------------------------------------------------------------- #
# Bloco 2 — teste de previsão
# --------------------------------------------------------------------------- #
def _janelas(g: pd.DataFrame, k: float):
    """Para cada janela do walk-forward: limiares só do treino → séries total e balcão."""
    idx = pd.date_range(g["data"].min().normalize(), g["data"].max().normalize(), freq="D")
    total = _diaria(g, idx)
    n = len(idx)
    for i in range(N_FOLDS):
        ini = n - (N_FOLDS - i) * HORIZONTE
        fut = idx[ini:ini + HORIZONTE]
        lim = limiares_encomenda(g[g["data"] < fut[0]], k=k)
        balcao = _diaria(g[~marcar_encomendas(g, lim)], idx)
        yield idx, ini, fut, total, balcao


def teste_previsao(g: pd.DataFrame, previsor: str, variantes=VARIANTES, k: float = K_DIAS_TIPICOS) -> dict:
    x_all = None
    acc = {v: [] for v in variantes}
    if "separar_teto" in variantes:
        acc["separar_teto_vs_total"] = []
    for idx, ini, fut, total, balcao in _janelas(g, k):
        if x_all is None:
            x_all = _exog_calendario(pd.date_range(idx[0], idx[-1] + pd.Timedelta(days=HORIZONTE), freq="D"))
        prever = (lambda y: _prever_sarimax(y, fut, x_all)) if previsor == "sarimax" else (lambda y: _prever_ets(y, fut))
        real = {"total": total.iloc[ini:ini + HORIZONTE].clip(lower=0).values,
                "balcao": balcao.iloc[ini:ini + HORIZONTE].clip(lower=0).values}
        tr = {"total": total.iloc[:ini], "balcao": balcao.iloc[:ini]}
        spec = {"original": ("total", False), "so_teto": ("total", True),
                "so_separar": ("balcao", False), "separar_teto": ("balcao", True)}
        for v in variantes:
            serie, teto = spec[v]
            fc = prever(teto_quantil(tr[serie]) if teto else tr[serie])
            acc[v].append(_erros(real[serie], fc, tr[serie]))
            if v == "separar_teto":
                acc["separar_teto_vs_total"].append(_erros(real["total"], fc, tr["total"]))
    return {v: _agrega(lst) for v, lst in acc.items()}


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
ROTULOS = {"original": "original\n(total → total)", "so_teto": "só teto",
           "so_separar": "só separar", "separar_teto": "separar + teto\n(solução)"}


def graficos(df: pd.DataFrame, testes: dict, plt) -> list[str]:
    figs = []
    lim = limiares_encomenda(df)
    enc = marcar_encomendas(df, lim)

    # 25. Série diária: balcão × encomendas
    fig, axes = plt.subplots(len(C.UNIDADES), 1, figsize=(13, 3.2 * len(C.UNIDADES)))
    for ax, u in zip(np.atleast_1d(axes), C.UNIDADES):
        g = df[df["unidade"] == u]
        idx = pd.date_range(g["data"].min().normalize(), g["data"].max().normalize(), freq="D")
        b, e = _diaria(g[~enc.loc[g.index]], idx), _diaria(g[enc.loc[g.index]], idx)
        ax.plot(idx, b.values, lw=.6, color=C.PALETA[u], label="balcão (o que o L1 prevê)")
        dias = e[e > 0]
        ax.bar(dias.index, dias.values, bottom=b[dias.index].values, width=1.5, color="#D84315",
               label="encomendas grandes (separadas)")
        ax.set_yscale("symlog", linthresh=100)
        ax.set_title(f"{u} — {int(enc.loc[g.index].sum())} linhas de encomenda, "
                     f"{e.sum() / (b.sum() + e.sum()) * 100:.1f}% do volume")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    np.atleast_1d(axes)[0].figure.suptitle(
        f"Venda diária: balcão × encomendas (linha > {K_DIAS_TIPICOS} dias típicos da unidade × categoria) — escala symlog")
    fig.tight_layout()
    figs.append(C.savefig(fig, "25_encomendas_series.png"))

    # 26. MASE por variante
    fig, axes = plt.subplots(1, len(C.UNIDADES), figsize=(6.2 * len(C.UNIDADES), 4), sharey=True)
    for ax, u in zip(np.atleast_1d(axes), C.UNIDADES):
        x = np.arange(len(VARIANTES))
        for j, (prev, cor) in enumerate((("sarimax", "#00838F"), ("ets", "#B0BEC5"))):
            ax.bar(x + (j - .5) * .36, [testes[(u, prev)][v]["mase"] for v in VARIANTES], .36,
                   color=cor, label="SARIMAX" if prev == "sarimax" else "Holt-Winters")
        ax.axhline(1, color="#B71C1C", lw=.8, ls="--")
        ax.set_xticks(x, [ROTULOS[v] for v in VARIANTES], fontsize=8)
        ax.set_title(u)
    np.atleast_1d(axes)[0].set_ylabel("MASE (h = 14 d, 26 folds) — abaixo de 1 bate a naïve semanal")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=8)
    fig.suptitle("L1 por unidade: efeito de separar encomendas e aplicar teto")
    fig.tight_layout()
    figs.append(C.savefig(fig, "26_encomendas_mase.png"))
    return figs


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    df = df[df["categoria"] != C.NAO_PRODUTO].dropna(subset=["data"])

    perfil = bloco_perfil(df)
    testes = {(u, p): teste_previsao(df[df["unidade"] == u], p)
              for u in C.UNIDADES for p in ("sarimax", "ets")}
    sens = {u: {str(k): (testes[(u, "sarimax")]["separar_teto"] if k == K_DIAS_TIPICOS else
                         teste_previsao(df[df["unidade"] == u], "sarimax", ("separar_teto",), k=k)["separar_teto"])
                for k in K_SENSIBILIDADE}
            for u in C.UNIDADES}

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "parametros": {"N_FOLDS": N_FOLDS, "HORIZONTE": HORIZONTE, "K_DIAS_TIPICOS": K_DIAS_TIPICOS,
                       "QUANTIL_TETO": QUANTIL_TETO,
                       "regra_encomenda": "linha com qtdade > K × mediana do volume diário (dias com venda, "
                                          "seg–sáb) da unidade × categoria, calculada no treino",
                       "regra_teto": f"série de balcão do treino limitada ao p{QUANTIL_TETO * 100:.0f} dos dias abertos"},
        "1_perfil": perfil,
        "2_teste_previsao": {f"{u} · {p}": t for (u, p), t in testes.items()},
        "2a_sensibilidade_k_sarimax": sens,
        "3_antes_depois": bloco_antes_depois(df),
    }
    resultado["graficos"] = graficos(df, testes, plt)
    path = C.dump_metrics("eda_encomendas.json", resultado)

    print(f"[eda_encomendas] encomenda = linha > {K_DIAS_TIPICOS} dias típicos da unidade × categoria")
    for par, v in perfil["por_par"].items():
        print(f"[eda_encomendas]   {par:<36} limiar {v['limiar_qtd_linha']:>8.0f} · {v['linhas_encomenda']:>3} linhas · "
              f"{v['pct_volume_encomenda']:>5.1f}% do volume · {v['dias_com_encomenda']:>3} dias")
    for u, v in perfil["por_unidade"].items():
        print(f"[eda_encomendas] {u:<14} {v['pct_volume_encomenda']}% do volume em {v['linhas_encomenda']} linhas · "
              f"{v['clientes_distintos_encomenda']} clientes (maior = {v['pct_volume_encomenda_maior_cliente']}%) · "
              f"boleto {v['pct_linhas_boleto']['encomenda']}% × {v['pct_linhas_boleto']['balcao']}% balcão · "
              f"CV total {v['cv']['total']} → balcão {v['cv']['balcao']} → balcão+teto {v['cv']['balcao_teto']}")
    print("[eda_encomendas] MASE (SARIMAX | Holt-Winters): " + " · ".join(VARIANTES) + " · solução vs total")
    for u in C.UNIDADES:
        for p in ("sarimax", "ets"):
            t = testes[(u, p)]
            print(f"[eda_encomendas]   {u:<14}{p:<8}" + "  ".join(f"{t[v]['mase']:.3f}" for v in VARIANTES)
                  + f"  | {t['separar_teto_vs_total']['mase']:.3f}")
    print("[eda_encomendas] sensibilidade a K (SARIMAX, separar + teto): "
          + " · ".join(f"{u}: " + ", ".join(f"K={k} {v['mase']:.3f}" for k, v in s.items()) for u, s in sens.items()))
    print("[eda_encomendas] antes (total) → depois (balcão) → balcão+teto: CV · Fs · acf7 · tendência %/ano · dias>3σ · classe · veredito")
    for u, v in resultado["3_antes_depois"].items():
        print(f"[eda_encomendas]   {u:<14}" + "  →  ".join(
            f"{r['cv']:.2f} · {r['forca_sazonal_semanal']:.2f} · {r['acf_lag7']:.2f} · {r['tendencia_pct_ano']:+.0f}% · "
            f"{r['dias_acima_3sigma']} · {r['classe_sbc']} · {r['veredito_sarimax']}" for r in v.values()))
    print(f"[eda_encomendas] métricas: {path}  ·  {len(resultado['graficos'])} gráficos")
    return resultado


if __name__ == "__main__":
    main()
