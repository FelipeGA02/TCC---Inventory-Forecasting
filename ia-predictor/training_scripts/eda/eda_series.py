"""EDA 2b — Análise da série de desagregação `unidade × categoria`.

Objeto: as séries diárias `unidade × categoria` (soma de `qtdade` por dia,
reindexada no calendário contínuo). **Revisão 2026-09-21 (ADR-011, `eda_separacao.py`):**
essas 6 séries não são mais o alvo direto do L1 — o teste de separação mostrou que
modelar cada categoria com SARIMAX próprio não erra menos do que repartir a previsão da
unidade (`eda_series_unidade.py`, o alvo real do L1 agora). Este módulo continua existindo
porque os blocos abaixo (perfil de dia da semana, efeito de datas, tendência) são
exatamente o que a desagregação `unidade → categoria` precisa — o mesmo "participação
móvel × perfil de dia-da-semana" que a L2 já usa de `categoria → SKU`, um nível acima.

Responde: como cada categoria se comporta dentro de sua unidade — insumo direto da
desagregação, não mais parâmetros de um SARIMAX próprio. Cada bloco alimenta uma decisão
concreta da L2 estendida (Fase 1 do plano de experimentos).

Blocos por par (unidade × categoria):
  1. Densidade / cobertura (dias com venda, zeros, maior sequência de zeros)
  2. Distribuição de qtdade diária → log1p se CV > LOG_CV_THRESHOLD (0.7)
  3. Sazonalidade semanal (perfil por dia da semana, força do ciclo m=7)
  4. Sazonalidade anual / mensal + efeito de datas comemorativas
  5. Tendência (inclinação OLS, variação início vs fim)
  6. Estacionariedade: ADF + KPSS → sugestão de d
  7. Autocorrelação: ACF/PACF nos lags 1, 7, 14; Ljung-Box (informativo)
  8. Outliers (dias > média + 3σ; regra IQR)

Bloco transversal:
  9. Esparsidade e estabilidade de share por SKU dentro da categoria → L2

Saídas: PNGs em results/plots/eda/ e results/metrics/eda_series.json
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import _common as C

warnings.filterwarnings("ignore")

LOG_CV_THRESHOLD = 0.7          # CLAUDE.md — acima disso, aplicar log1p
MIN_OBSERVATIONS_DAYS = 180     # CLAUDE.md — mínimo p/ treinar L1
SEASONAL_PERIOD = 7


# --------------------------------------------------------------------------- #
def _adf_kpss(s: pd.Series) -> dict:
    from statsmodels.tsa.stattools import adfuller, kpss
    from statsmodels.tools.sm_exceptions import InterpolationWarning
    out = {}
    x = s.astype(float).values
    try:
        out["adf_pvalue"] = float(adfuller(x, autolag="AIC")[1])
    except Exception as e:                       # noqa: BLE001
        out["adf_pvalue"] = None
        out["adf_erro"] = str(e)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InterpolationWarning)
            kp = float(kpss(x, regression="c", nlags="auto")[1])
        # p-value vem "clipado" em [0.01, 0.10]; registra que é limite da tabela
        out["kpss_pvalue"] = kp
        out["kpss_pvalue_no_limite_da_tabela"] = kp in (0.01, 0.10)
    except Exception as e:                       # noqa: BLE001
        out["kpss_pvalue"] = None
        out["kpss_erro"] = str(e)
    adf_ok = out["adf_pvalue"] is not None and out["adf_pvalue"] < 0.05
    kpss_ok = out["kpss_pvalue"] is not None and out["kpss_pvalue"] > 0.05
    if adf_ok and kpss_ok:
        out["sugestao_d"] = 0
        out["leitura"] = "estacionária (ADF rejeita raiz unitária, KPSS não rejeita)"
    elif not adf_ok and not kpss_ok:
        out["sugestao_d"] = 1
        out["leitura"] = "não-estacionária pelos dois testes → testar d=1"
    else:
        out["sugestao_d"] = 0
        out["leitura"] = "testes divergem → começar com d=0, revisar por resíduo"
    return out


def _acf_pacf(s: pd.Series) -> dict:
    from statsmodels.tsa.stattools import acf, pacf
    from statsmodels.stats.diagnostic import acorr_ljungbox
    x = s.astype(float).values
    n_lag = min(21, len(x) // 2 - 1)
    a = acf(x, nlags=n_lag, fft=True)
    p = pacf(x, nlags=n_lag)
    lb = acorr_ljungbox(x, lags=[7, 14], return_df=True)
    return {
        "acf_lag1": float(a[1]),
        "acf_lag7": float(a[7]) if len(a) > 7 else None,
        "acf_lag14": float(a[14]) if len(a) > 14 else None,
        "pacf_lag1": float(p[1]),
        "pacf_lag7": float(p[7]) if len(p) > 7 else None,
        "ljung_box_lag7_pvalue": float(lb["lb_pvalue"].iloc[0]),
        "ljung_box_lag14_pvalue": float(lb["lb_pvalue"].iloc[1]),
        "autocorrelacao_significativa": bool(lb["lb_pvalue"].iloc[0] < 0.05),
    }


def _forca_sazonal_semanal(s: pd.Series) -> dict:
    """Força do ciclo m=7 via STL: Fs = max(0, 1 - Var(resid)/Var(resid+season))."""
    from statsmodels.tsa.seasonal import STL
    try:
        res = STL(s.astype(float), period=SEASONAL_PERIOD, robust=True).fit()
        var_r = np.nanvar(res.resid)
        var_rs = np.nanvar(res.resid + res.seasonal)
        var_rt = np.nanvar(res.resid + res.trend)
        fs = max(0.0, 1 - var_r / var_rs) if var_rs > 0 else 0.0
        ft = max(0.0, 1 - var_r / var_rt) if var_rt > 0 else 0.0
        return {"forca_sazonal_semanal": float(fs), "forca_tendencia": float(ft)}
    except Exception as e:                       # noqa: BLE001
        return {"forca_sazonal_semanal": None, "forca_tendencia": None,
                "stl_erro": str(e)}


def _perfil_dow(s: pd.Series) -> dict:
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    by = s.groupby(s.index.weekday).mean().reindex(range(7))
    media = s.mean()
    seg_sab = by.iloc[:6]                       # amplitude só entre dias abertos
    return {
        "media_por_dia_semana": {dias_pt[i]: float(by.get(i, np.nan)) for i in range(7)},
        "indice_dia_semana": {dias_pt[i]: (float(by.get(i, np.nan) / media)
                                          if media else None) for i in range(7)},
        "dia_pico": dias_pt[int(np.nanargmax(by.values))],
        "dia_vale_aberto": dias_pt[int(np.nanargmin(seg_sab.values))],
        "amplitude_pico_vale_seg_a_sab": float(np.nanmax(seg_sab.values) /
                                               np.nanmin(seg_sab.values))
        if np.nanmin(seg_sab.values) > 0 else None,
        "domingo_pct_da_media": float(by.get(6, np.nan) / media) if media else None,
        "sabado_pct_da_media": float(by.get(5, np.nan) / media) if media else None,
    }


def _perfil_mensal(s: pd.Series) -> dict:
    by = s.groupby(s.index.month).mean().reindex(range(1, 13))
    media = s.mean()
    # Um pico mensal só é sazonalidade se se repete: há apenas ~2 ciclos anuais, então o
    # índice é também aberto por ano e recalculado sem o maior dia da série.
    por_ano = s.groupby([s.index.year, s.index.month]).mean() / media
    s2 = s.copy()
    s2[s.idxmax()] = s.median()
    by2 = s2.groupby(s2.index.month).mean().reindex(range(1, 13)) / s2.mean()
    return {
        "indice_mes": {int(m): (float(v / media) if media else None)
                       for m, v in by.items()},
        "mes_pico": int(by.idxmax()),
        "mes_vale": int(by.idxmin()),
        "indice_mes_por_ano": {int(a): {int(m): float(v) for (_, m), v in g.items()}
                               for a, g in por_ano.groupby(level=0)},
        "indice_mes_sem_maior_dia": {int(m): float(v) for m, v in by2.items()},
        "mes_pico_sem_maior_dia": int(by2.idxmax()),
    }


def _efeito_datas(s: pd.Series) -> dict:
    anos = range(s.index.year.min(), s.index.year.max() + 1)
    dc = C.datas_comemorativas(anos)
    base = s.mean()
    out = {}
    for evento, grp in dc.groupby("evento"):
        dias = pd.DatetimeIndex(grp["data"]).normalize()
        janela = dias.union(dias - pd.Timedelta(days=1)).union(dias - pd.Timedelta(days=2))
        janela = janela.intersection(s.index)
        if len(janela) == 0:
            continue
        out[evento] = {
            "n_ocorrencias_janela": int(len(janela)),
            "razao_vs_media_geral": float(s.loc[janela].mean() / base) if base else None,
        }
    return out


def _tendencia(s: pd.Series) -> dict:
    x = np.arange(len(s), dtype=float)
    y = s.astype(float).values
    b1, b0 = np.polyfit(x, y, 1)
    ini = y[:90].mean()
    fim = y[-90:].mean()
    return {
        "inclinacao_unid_por_dia": float(b1),
        "inclinacao_pct_da_media_por_ano": float(b1 * 365 / y.mean() * 100)
        if y.mean() else None,
        "media_primeiros_90d": float(ini),
        "media_ultimos_90d": float(fim),
        "variacao_90d_ini_vs_fim_pct": float((fim - ini) / ini * 100) if ini else None,
    }


def _distribuicao(s: pd.Series) -> dict:
    from scipy import stats
    x = s.astype(float).values
    nz = x[x > 0]
    cv = float(x.std() / x.mean()) if x.mean() else None
    aberto = s[s.index.weekday < 6].values          # exclui domingos (loja fechada)
    return {
        "media": float(x.mean()),
        "desvio_padrao": float(x.std()),
        "cv": cv,
        "min": float(x.min()), "max": float(x.max()),
        "razao_max_media": float(x.max() / x.mean()) if x.mean() else None,
        "p50": float(np.percentile(x, 50)),
        "p90": float(np.percentile(x, 90)),
        "p99": float(np.percentile(x, 99)),
        "assimetria_skew": float(stats.skew(x)),
        "curtose": float(stats.kurtosis(x)),
        "pct_dias_zero": float((x == 0).mean() * 100),
        "pct_dias_zero_excl_domingo": float((aberto == 0).mean() * 100),
        "cv_somente_dias_com_venda": float(nz.std() / nz.mean())
        if len(nz) and nz.mean() else None,
        "aplicar_log1p": bool(cv is not None and cv > LOG_CV_THRESHOLD),
    }


def _densidade(s: pd.Series, df_par: pd.DataFrame) -> dict:
    zero = (s.values == 0)
    # maior sequência de zeros
    maxrun = cur = 0
    for z in zero:
        cur = cur + 1 if z else 0
        maxrun = max(maxrun, cur)
    dias_venda = int((~zero).sum())
    return {
        "primeiro_dia": s.index.min(),
        "ultimo_dia": s.index.max(),
        "dias_calendario": int(len(s)),
        "dias_com_venda": dias_venda,
        "pct_dias_com_venda": float(dias_venda / len(s) * 100),
        "maior_sequencia_zeros": int(maxrun),
        "atende_min_180d": bool(dias_venda >= MIN_OBSERVATIONS_DAYS),
        "linhas_transacao": int(len(df_par)),
        "skus_distintos": int(df_par["produto_cod"].nunique()),
    }


def _outliers(s: pd.Series, df_par: pd.DataFrame) -> dict:
    x = s.astype(float)
    z = (x - x.mean()) / x.std()
    q1, q3 = x.quantile(.25), x.quantile(.75)
    iqr = q3 - q1
    lim = q3 + 3 * iqr
    top = x[z > 3].sort_values(ascending=False).head(5)
    out = {
        "n_dias_acima_3sigma": int((z > 3).sum()),
        "n_dias_acima_iqr3": int((x > lim).sum()),
        "top5_dias": {d.date().isoformat(): float(v) for d, v in top.items()},
    }
    if len(top):
        # Composição do maior dia: pedido grande (poucos documentos, linhas enormes) ou
        # erro de registro? Uma linha de milhares de unidades de um mesmo item é pedido real.
        d = df_par[df_par["data"].dt.normalize() == top.index[0]]
        docs = d["doc_numero"].astype(str) + "|" + d["doc_tipo"].astype(str)
        maior = float(d["qtdade_n"].max())
        out["maior_dia"] = {
            "data": top.index[0].date().isoformat(),
            "qtd": float(top.iloc[0]),
            "documentos": int(docs.nunique()),
            "linhas": int(len(d)),
            "maior_linha_qtd": maior,
            "maior_linha_pct_do_dia": round(maior / float(top.iloc[0]) * 100, 1),
        }
    return out


def _verdito(dens, dist, saz, acp, est, tend) -> dict:
    motivos = []
    if not dens["atende_min_180d"]:
        motivos.append("< 180 dias com venda (insufficient_data)")
    if dens["dias_com_venda"] < 400:
        motivos.append(f"histórico curto ({dens['dias_com_venda']} dias) — sem ciclo anual completo")
    if dist["pct_dias_zero_excl_domingo"] > 12:
        motivos.append(f"{dist['pct_dias_zero_excl_domingo']:.0f}% de dias úteis zerados "
                       "(intermitência além dos domingos)")
    if (dist["razao_max_media"] or 0) > 30:
        motivos.append(f"cauda extrema (dia pico = {dist['razao_max_media']:.0f}× a média) "
                       "— pedidos B2B pontuais dominam a variância")
    if saz.get("forca_sazonal_semanal") is not None and saz["forca_sazonal_semanal"] < 0.1:
        motivos.append("ciclo semanal fraco na variância (Fs < 0.1) — dummies de dia da semana "
                       "farão mais que os termos SARIMA sazonais")
    if not acp["autocorrelacao_significativa"]:
        motivos.append("sem autocorrelação significativa até lag 7 (Ljung-Box) — parte ARIMA "
                       "quase inócua; exógenas de calendário carregam o modelo")
    if abs(tend.get("inclinacao_pct_da_media_por_ano") or 0) > 40:
        motivos.append(f"tendência forte ({tend['inclinacao_pct_da_media_por_ano']:+.0f}%/ano) "
                       "— avaliar d=1 ou termo de nível/deriva")
    nivel = "ok"
    if any("insufficient_data" in m for m in motivos):
        nivel = "insuficiente"
    elif motivos:
        nivel = "atencao"
    return {"nivel": nivel, "observacoes": motivos or ["sem ressalvas para o L1"]}


# --------------------------------------------------------------------------- #
def analisa_serie(s: pd.Series, df_serie: pd.DataFrame) -> dict:
    """Bateria completa de diagnóstico (blocos 1–9) para qualquer série diária de
    demanda + o recorte transacional que a origina — reaproveitada por `analisa_par()`
    (série `unidade × categoria`, este módulo) e por `eda_series_unidade.analisa_unidade()`
    (série `unidade`, o alvo real do L1)."""
    dens = _densidade(s, df_serie)
    dist = _distribuicao(s)
    saz_sem = _perfil_dow(s) | _forca_sazonal_semanal(s)
    saz_ano = _perfil_mensal(s)
    datas = _efeito_datas(s)
    tend = _tendencia(s)
    est = _adf_kpss(s)
    acp = _acf_pacf(s)
    out = _outliers(s, df_serie)
    return {
        "1_densidade": dens,
        "2_distribuicao": dist,
        "3_sazonalidade_semanal": saz_sem,
        "4_sazonalidade_anual": saz_ano,
        "4b_datas_comemorativas": datas,
        "5_tendencia": tend,
        "6_estacionariedade": est,
        "7_autocorrelacao": acp,
        "8_outliers": out,
        "9_veredito_sarimax": _verdito(dens, dist, saz_sem, acp, est, tend),
    }


def analisa_par(df: pd.DataFrame, unidade: str, categoria: str) -> dict:
    s = C.serie_diaria(df, unidade, categoria, span="par")
    df_par = df[(df["unidade"] == unidade) & (df["categoria"] == categoria)]
    return analisa_serie(s, df_par)


def bloco_sku_dentro_categoria(df: pd.DataFrame) -> dict:
    """Justifica a L2 em dois passos: quantos SKUs por par, quão concentrado,
    e quão estável é a participação semanal dos SKUs líderes ao longo do tempo."""
    out = {}
    for (u, c) in C.pares_l1(df):
        d = df[(df["unidade"] == u) & (df["categoria"] == c)].copy()
        q = d.groupby("produto_cod")["qtdade_n"].sum().sort_values(ascending=False)
        q = q[q > 0]
        if q.empty:
            continue
        cum = q.cumsum() / q.sum()
        # estabilidade de share: CV da participação MENSAL dos top-10 SKUs
        # (janela alinhada com a média móvel de 4–8 semanas da L2; a versão
        # semanal infla o CV com semanas estruturalmente zeradas do SKU).
        d["mes"] = d["data"].dt.to_period("M")
        mk = d.pivot_table(index="mes", columns="produto_cod",
                           values="qtdade_n", aggfunc="sum", fill_value=0.0)
        if len(mk) >= 6:
            share = mk.div(mk.sum(axis=1).replace(0, np.nan), axis=0).dropna(how="all")
            top10 = q.head(10).index
            cvs = [float(share[s].std() / share[s].mean())
                   for s in top10 if s in share and share[s].mean() > 0]
            cv_share_top10 = float(np.mean(cvs)) if cvs else None
        else:
            cv_share_top10 = None
        out[f"{u} · {c}"] = {
            "n_skus": int(len(q)),
            "skus_para_80pct_volume": int((cum <= .8).sum()) + 1,
            "share_top1_pct": round(float(q.iloc[0] / q.sum()) * 100, 1),
            "share_top5_pct": round(float(cum.iloc[min(4, len(q) - 1)]) * 100, 1),
            "cv_medio_share_mensal_top10": cv_share_top10,
            "leitura_share": ("participação estável — média móvel de 4–8 semanas serve"
                              if (cv_share_top10 or 1) < 0.5
                              else "participação instável — janela mais longa / fallback L2 load-bearing"),
        }
    return out


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def _grade(pares: list) -> tuple[int, int]:
    """Uma linha por unidade, uma coluna por categoria (os pares formam grade completa)."""
    n_u = len({u for u, _ in pares})
    return n_u, len(pares) // n_u


def _estilo_unidade(pares: list) -> dict:
    """Categoria define a cor; unidade define o traço (sólido / tracejado)."""
    unidades = sorted({u for u, _ in pares})
    return {u: ("-", "--", ":")[i % 3] for i, u in enumerate(unidades)}


def graficos(df: pd.DataFrame, series: dict, plt) -> list[str]:
    figs = []
    pares = C.pares_l1(df)
    n_lin, n_col = _grade(pares)
    traco = _estilo_unidade(pares)

    # 1. Séries diárias + média móvel 28d
    fig, axes = plt.subplots(n_lin, n_col, figsize=(5 * n_col, 3 * n_lin + 0.5), sharex=True)
    for ax, (u, c) in zip(axes.ravel(), pares):
        s = series[(u, c)]
        ax.plot(s.index, s.values, lw=.5, color="#B0BEC5")
        ax.plot(s.index, s.rolling(28, min_periods=7).mean(), lw=1.4,
                color=C.PALETA.get(c, "#333"))
        ax.set_title(f"{u} · {c}  (CV={s.std()/s.mean():.2f})", fontsize=9)
    fig.suptitle(f"Série diária L1 (cinza) + média móvel 28d — {len(pares)} pares unidade × categoria")
    fig.tight_layout()
    figs.append(C.savefig(fig, "10_series_l1_paineis.png"))

    # 2. Perfil de dia da semana (índice vs média)
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for (u, c) in pares:
        s = series[(u, c)]
        by = s.groupby(s.index.weekday).mean().reindex(range(7)) / s.mean()
        ax.plot(dias_pt, by.values, marker="o", lw=1, ls=traco[u],
                label=f"{u} · {c}", color=C.PALETA.get(c, "#333"), alpha=.8)
    ax.axhline(1, color="#999", lw=.8, ls=":")
    ax.set_title("Índice de demanda por dia da semana (1.0 = média do par)")
    ax.set_ylabel("demanda relativa"); ax.legend(fontsize=7, ncol=2, frameon=False)
    figs.append(C.savefig(fig, "11_perfil_dia_semana_l1.png"))

    # 3. Perfil mensal (sazonalidade anual)
    fig, ax = plt.subplots(figsize=(9, 5))
    for (u, c) in pares:
        s = series[(u, c)]
        by = s.groupby(s.index.month).mean().reindex(range(1, 13)) / s.mean()
        ax.plot(range(1, 13), by.values, marker="o", lw=1, ls=traco[u],
                label=f"{u} · {c}", color=C.PALETA.get(c, "#333"), alpha=.8)
    ax.axhline(1, color="#999", lw=.8, ls=":")
    ax.axvline(5, color="#B71C1C", lw=.7, ls="--", alpha=.5)   # maio - Dia das Mães
    ax.axvline(11, color="#B71C1C", lw=.7, ls="--", alpha=.5)  # nov - Finados
    ax.set_title("Índice de demanda por mês (1.0 = média do par) — tracejado vermelho: maio / nov")
    ax.set_xlabel("mês"); ax.set_ylabel("demanda relativa")
    ax.legend(fontsize=7, ncol=2, frameon=False)
    figs.append(C.savefig(fig, "12_perfil_mensal_l1.png"))

    # 4. ACF das séries
    from statsmodels.graphics.tsaplots import plot_acf
    fig, axes = plt.subplots(n_lin, n_col, figsize=(5 * n_col, 3 * n_lin + 0.5))
    for ax, (u, c) in zip(axes.ravel(), pares):
        plot_acf(series[(u, c)].astype(float).values, lags=21, ax=ax, alpha=.05)
        ax.set_title(f"{u} · {c}", fontsize=9)
    fig.suptitle("ACF (lags 0–21) — pico em múltiplos de 7 ⇒ sazonalidade semanal")
    fig.tight_layout()
    figs.append(C.savefig(fig, "13_acf_l1_paineis.png"))

    # 5. Distribuição de qtdade diária (hist)
    fig, axes = plt.subplots(n_lin, n_col, figsize=(5 * n_col, 3 * n_lin + 0.5))
    for ax, (u, c) in zip(axes.ravel(), pares):
        s = series[(u, c)]
        ax.hist(s.values, bins=40, color=C.PALETA.get(c, "#333"), alpha=.8)
        ax.axvline(s.mean(), color="#000", lw=1, ls="--")
        ax.set_title(f"{u} · {c}  (skew={float(_skew(s)):.1f})", fontsize=9)
    fig.suptitle("Distribuição da quantidade diária — assimetria à direita ⇒ log1p")
    fig.tight_layout()
    figs.append(C.savefig(fig, "14_dist_qtd_diaria_l1.png"))

    # 6. STL de um par denso representativo (maior volume)
    from statsmodels.tsa.seasonal import STL
    u, c = max(pares, key=lambda p: series[p].sum())
    res = STL(series[(u, c)].astype(float), period=7, robust=True).fit()
    fig, axes = plt.subplots(4, 1, figsize=(13, 9), sharex=True)
    for ax, comp, nome in zip(axes, [res.observed, res.trend, res.seasonal, res.resid],
                              ["observado", "tendência", "sazonal (m=7)", "resíduo"]):
        ax.plot(series[(u, c)].index, comp, lw=.8, color="#37474F")
        ax.set_ylabel(nome)
    fig.suptitle(f"Decomposição STL — {u} · {c} (par de maior volume)")
    fig.tight_layout()
    figs.append(C.savefig(fig, "15_stl_par_denso.png"))

    return figs


def _skew(s):
    from scipy import stats
    return stats.skew(s.astype(float).values)


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    pares = C.pares_l1(df)
    series = {p: C.serie_diaria(df, p[0], p[1], span="par") for p in pares}

    por_par = {}
    for (u, c) in pares:
        por_par[f"{u} · {c}"] = analisa_par(df, u, c)

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "parametros": {
            "LOG_CV_THRESHOLD": LOG_CV_THRESHOLD,
            "MIN_OBSERVATIONS_DAYS": MIN_OBSERVATIONS_DAYS,
            "SEASONAL_PERIOD": SEASONAL_PERIOD,
        },
        "n_pares_l1": len(pares),
        "por_par": por_par,
        "10_sku_dentro_categoria_L2": bloco_sku_dentro_categoria(df),
    }

    # sumário executivo
    resumo = []
    for nome, r in por_par.items():
        resumo.append({
            "par": nome,
            "dias_com_venda": r["1_densidade"]["dias_com_venda"],
            "pct_dias_com_venda": round(r["1_densidade"]["pct_dias_com_venda"], 1),
            "cv": round(r["2_distribuicao"]["cv"], 2) if r["2_distribuicao"]["cv"] else None,
            "log1p": r["2_distribuicao"]["aplicar_log1p"],
            "Fs_semanal": round(r["3_sazonalidade_semanal"]["forca_sazonal_semanal"], 2)
            if r["3_sazonalidade_semanal"]["forca_sazonal_semanal"] is not None else None,
            "sugestao_d": r["6_estacionariedade"]["sugestao_d"],
            "acf_lag7": round(r["7_autocorrelacao"]["acf_lag7"], 2)
            if r["7_autocorrelacao"]["acf_lag7"] is not None else None,
            "veredito": r["9_veredito_sarimax"]["nivel"],
        })
    resultado["sumario"] = resumo
    resultado["graficos"] = graficos(df, series, plt)
    path = C.dump_metrics("eda_series.json", resultado)

    print(f"[eda_series] {len(pares)} pares L1")
    print(f"[eda_series] {'par':<34}{'d.venda':>8}{'%d':>6}{'CV':>7}{'log1p':>7}"
          f"{'Fs':>6}{'d':>3}{'acf7':>7}  veredito")
    for r in resumo:
        print(f"[eda_series] {r['par']:<34}{r['dias_com_venda']:>8}{r['pct_dias_com_venda']:>6}"
              f"{r['cv']!s:>7}{str(r['log1p']):>7}{r['Fs_semanal']!s:>6}{r['sugestao_d']:>3}"
              f"{r['acf_lag7']!s:>7}  {r['veredito']}")
    print(f"[eda_series] métricas: {path}  ·  {len(resultado['graficos'])} gráficos")
    return resultado


if __name__ == "__main__":
    main()
