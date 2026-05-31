"""
Funções de análise estatística e visualização exploratória para o TCC.

Funções disponíveis:
  plot_monthly_series          → séries mensais de quantidade vendida
  plot_demand_distribution     → distribuição e boxplots de demanda
  plot_demand_cv_analysis      → coeficiente de variação (identifica demanda irregular)
  plot_correlation_with_target → correlação de Pearson de variáveis exógenas com a demanda
  plot_correlation_heatmap     → mapa de calor entre todas as variáveis
  plot_stationarity_report     → tabela e gráfico dos testes ADF e KPSS
  plot_feature_importance      → importância das variáveis via Random Forest
  plot_seasonal_profile        → perfil sazonal médio por mês
  plot_market_overview         → visão geral do mercado (volume, receita, clientes)
  run_full_analysis            → executa toda a análise estatística e salva os gráficos
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.stattools import adfuller, kpss

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots" / "statistical_analysis"


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _save(fig: plt.Figure, name: str, save_dir: Path) -> None:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {path.name}")


def _monthly_ts(df: pd.DataFrame, produto_cod: str) -> pd.Series:
    mask = df["produto_cod"].astype(str) == str(produto_cod)
    ts = (
        df[mask]
        .groupby(df.loc[mask, "emissao"].dt.to_period("M"))["qtdade"]
        .sum()
        .sort_index()
    )
    ts.index = ts.index.to_timestamp()
    return ts


def _exog_features(df: pd.DataFrame, produto_cod: str) -> pd.DataFrame:
    period = df["emissao"].dt.to_period("M")
    mkt = df.groupby(period).agg(
        mkt_qtd_total=("qtdade", "sum"),
        mkt_valor_total=("vl_total", "sum"),
        mkt_desconto_total=("vl_desconto", "sum"),
        mkt_n_pedidos=("doc_numero", "nunique"),
        mkt_n_clientes=("cliente_cod", "nunique"),
        mkt_preco_medio=("vl_unit", "mean"),
    )
    mkt["mkt_taxa_desconto"] = mkt["mkt_desconto_total"] / (mkt["mkt_valor_total"] + 1e-9)

    prod = df[df["produto_cod"].astype(str) == str(produto_cod)]
    prod_feat = prod.groupby(period).agg(
        prod_preco_medio=("vl_unit", "mean"),
        prod_desconto_medio=("vl_desconto", "mean"),
        prod_n_clientes=("cliente_cod", "nunique"),
        prod_n_pedidos=("doc_numero", "nunique"),
    )
    prod_feat["prod_taxa_desconto"] = (
        prod_feat["prod_desconto_medio"] / (prod_feat["prod_preco_medio"] + 1e-9)
    )
    exog = mkt.join(prod_feat, how="left").fillna(0)
    exog.index = exog.index.to_timestamp()
    exog["mes"] = exog.index.month
    exog["trimestre"] = exog.index.quarter
    exog["alta_temporada"] = exog["mes"].isin([10, 11, 12, 5]).astype(int)
    return exog


def _stationarity(ts: pd.Series) -> dict:
    adf_stat, adf_p, *_ = adfuller(ts.dropna())
    try:
        kpss_stat, kpss_p, *_ = kpss(ts.dropna(), regression="c", nlags="auto")
    except Exception:
        kpss_stat, kpss_p = np.nan, np.nan
    return {
        "adf_stat": adf_stat, "adf_p": adf_p, "adf_estac": adf_p < 0.05,
        "kpss_stat": kpss_stat, "kpss_p": kpss_p, "kpss_estac": kpss_p > 0.05,
    }


# ──────────────────────────────────────────────
# 1. Séries mensais
# ──────────────────────────────────────────────

def plot_monthly_series(
    df: pd.DataFrame,
    products: list,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Painel de séries mensais de quantidade vendida para cada produto."""
    n = len(products)
    ncols = 2
    nrows = (n + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 4))
    axes = axes.flatten()

    for i, prod in enumerate(products):
        ts = _monthly_ts(df, prod)
        ax = axes[i]
        ax.plot(ts.index, ts.values, marker="o", markersize=3, linewidth=1.5, color="#1f77b4")
        ax.fill_between(ts.index, ts.values, alpha=0.1, color="#1f77b4")
        ax.set_title(f"Produto {prod}", fontsize=10, fontweight="bold")
        ax.set_ylabel("Qtd vendida")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        ax.grid(True, alpha=0.3)

        mean_val = ts.mean()
        ax.axhline(mean_val, color="red", linestyle="--", linewidth=0.8,
                   label=f"Media={mean_val:.0f}")
        ax.legend(fontsize=7, loc="upper left")

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Séries mensais de quantidade vendida — Top produtos", fontsize=13, fontweight="bold")
    plt.tight_layout()
    _save(fig, "01_series_mensais.png", save_dir)


# ──────────────────────────────────────────────
# 2. Distribuição da demanda
# ──────────────────────────────────────────────

def plot_demand_distribution(
    df: pd.DataFrame,
    products: list,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Boxplots e histogramas da distribuição mensal de demanda por produto."""
    data = {}
    for prod in products:
        ts = _monthly_ts(df, prod)
        data[str(prod)] = ts.values

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Boxplot
    bp = axes[0].boxplot(
        [data[str(p)] for p in products],
        labels=[str(p) for p in products],
        patch_artist=True,
        notch=False,
        medianprops=dict(color="red", linewidth=1.5),
    )
    colors = plt.cm.tab10(np.linspace(0, 1, len(products)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    axes[0].set_xticklabels([str(p) for p in products], rotation=45, ha="right")
    axes[0].set_ylabel("Quantidade mensal")
    axes[0].set_title("Distribuição da demanda mensal por produto")
    axes[0].grid(True, axis="y", alpha=0.3)

    # Média vs Desvio padrão
    means = [np.mean(data[str(p)]) for p in products]
    stds = [np.std(data[str(p)]) for p in products]
    x = range(len(products))
    axes[1].bar(x, means, color=colors, alpha=0.7, label="Média", edgecolor="white")
    axes[1].errorbar(x, means, yerr=stds, fmt="none", color="black", capsize=5, linewidth=1.5)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([str(p) for p in products], rotation=45, ha="right")
    axes[1].set_ylabel("Quantidade")
    axes[1].set_title("Média ± Desvio Padrão por produto")
    axes[1].grid(True, axis="y", alpha=0.3)

    fig.suptitle("Análise de distribuição da demanda", fontsize=13, fontweight="bold")
    plt.tight_layout()
    _save(fig, "02_distribuicao_demanda.png", save_dir)


# ──────────────────────────────────────────────
# 3. Coeficiente de variação (CV)
# ──────────────────────────────────────────────

def plot_demand_cv_analysis(
    df: pd.DataFrame,
    products: list,
    cv_threshold: float = 0.7,
    save_dir: Path = PLOTS_DIR,
) -> pd.DataFrame:
    """
    Calcula e visualiza o Coeficiente de Variação (CV = std/mean) de cada produto.
    CV > threshold indica demanda irregular (lumpy demand) onde SARIMAX pode não ser adequado.
    Retorna DataFrame com estatísticas por produto.
    """
    rows = []
    for prod in products:
        ts = _monthly_ts(df, prod)
        mean = ts.mean()
        std = ts.std()
        cv = std / (mean + 1e-9)
        rows.append({
            "produto_cod": str(prod),
            "media": mean,
            "std": std,
            "cv": cv,
            "min": ts.min(),
            "max": ts.max(),
            "n_meses": len(ts),
            "tipo": "Irregular (lumpy)" if cv > cv_threshold else "Regular",
        })

    stats = pd.DataFrame(rows).sort_values("cv", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    colors = ["#d62728" if cv > cv_threshold else "#2ca02c" for cv in stats["cv"]]
    axes[0].barh(stats["produto_cod"], stats["cv"], color=colors, edgecolor="white")
    axes[0].axvline(cv_threshold, color="orange", linestyle="--", linewidth=1.5,
                    label=f"Limite (CV={cv_threshold})")
    axes[0].set_xlabel("Coeficiente de Variacao (CV = std/media)")
    axes[0].set_title("CV por produto — identifica demanda irregular")
    axes[0].legend()
    axes[0].grid(True, axis="x", alpha=0.3)

    # Scatter media vs std
    sc_colors = ["#d62728" if cv > cv_threshold else "#2ca02c" for cv in stats["cv"]]
    sc = axes[1].scatter(stats["media"], stats["std"], c=sc_colors, s=120, zorder=5, edgecolors="white")
    for _, row in stats.iterrows():
        axes[1].annotate(row["produto_cod"], (row["media"], row["std"]),
                         textcoords="offset points", xytext=(5, 5), fontsize=7)
    x_range = np.linspace(0, stats["media"].max() * 1.1, 100)
    axes[1].plot(x_range, x_range * cv_threshold, "k--", linewidth=1, label=f"CV={cv_threshold}")
    axes[1].set_xlabel("Media mensal")
    axes[1].set_ylabel("Desvio padrao mensal")
    axes[1].set_title("Media vs Desvio Padrao (dispersao da demanda)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.suptitle("Analise de variabilidade da demanda (Coeficiente de Variacao)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    _save(fig, "03_cv_analise.png", save_dir)

    return stats


# ──────────────────────────────────────────────
# 4. Correlação variáveis exógenas vs demanda
# ──────────────────────────────────────────────

def plot_correlation_with_target(
    df: pd.DataFrame,
    produto_cod: str,
    save_dir: Path = PLOTS_DIR,
) -> pd.Series:
    """Correlação de Pearson entre variáveis exógenas e a demanda mensal do produto."""
    ts = _monthly_ts(df, produto_cod)
    exog = _exog_features(df, produto_cod).reindex(ts.index).ffill().fillna(0)

    merged = exog.copy()
    merged["target_qtd"] = ts
    corr = merged.corr()["target_qtd"].drop("target_qtd").sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#2ca02c" if v > 0.1 else "#d62728" if v < -0.1 else "#aec7e8"
              for v in corr.values]
    bars = corr.plot(kind="barh", ax=ax, color=colors, edgecolor="white")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axvline(0.3, color="green", linestyle=":", linewidth=1, alpha=0.6, label="Corr. moderada (0.3)")
    ax.axvline(-0.3, color="red", linestyle=":", linewidth=1, alpha=0.6)
    ax.set_title(f"Correlacao com demanda mensal — Produto {produto_cod}", fontsize=12)
    ax.set_xlabel("Correlacao de Pearson")
    ax.legend(fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    for i, (val, bar) in enumerate(zip(corr.values, ax.patches)):
        ax.text(val + 0.01 if val >= 0 else val - 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", ha="left" if val >= 0 else "right", fontsize=7)

    plt.tight_layout()
    _save(fig, f"04_correlacao_{str(produto_cod)}.png", save_dir)
    return corr


# ──────────────────────────────────────────────
# 5. Heatmap de correlações
# ──────────────────────────────────────────────

def plot_correlation_heatmap(
    df: pd.DataFrame,
    produto_cod: str,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Mapa de calor de correlações entre todas as variáveis (exógenas + demanda)."""
    ts = _monthly_ts(df, produto_cod)
    exog = _exog_features(df, produto_cod).reindex(ts.index).ffill().fillna(0)
    merged = exog.copy()
    merged["demanda"] = ts

    fig, ax = plt.subplots(figsize=(14, 11))
    mask = np.triu(np.ones_like(merged.corr(), dtype=bool))
    sns.heatmap(
        merged.corr(), annot=True, fmt=".2f", cmap="coolwarm",
        center=0, ax=ax, annot_kws={"size": 7}, linewidths=0.5,
        mask=mask,
    )
    ax.set_title(f"Mapa de correlacao — Produto {produto_cod}", fontsize=12)
    plt.tight_layout()
    _save(fig, f"05_heatmap_{str(produto_cod)}.png", save_dir)


# ──────────────────────────────────────────────
# 6. Testes de estacionariedade
# ──────────────────────────────────────────────

def plot_stationarity_report(
    df: pd.DataFrame,
    products: list,
    save_dir: Path = PLOTS_DIR,
) -> pd.DataFrame:
    """
    Calcula ADF e KPSS para cada produto e gera tabela + gráfico de p-valores.
    Retorna DataFrame com resultados.
    """
    rows = []
    for prod in products:
        ts = _monthly_ts(df, prod)
        stat = _stationarity(ts)
        stat_diff = _stationarity(ts.diff().dropna())
        rows.append({
            "produto": str(prod),
            "n_obs": len(ts),
            "adf_p_original": round(stat["adf_p"], 4),
            "kpss_p_original": round(stat["kpss_p"], 4),
            "estac_original": stat["adf_estac"] and stat["kpss_estac"],
            "adf_p_diff1": round(stat_diff["adf_p"], 4),
            "kpss_p_diff1": round(stat_diff["kpss_p"], 4),
            "estac_diff1": stat_diff["adf_estac"] and stat_diff["kpss_estac"],
        })

    report = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    x = range(len(report))
    w = 0.35
    adf_colors = ["#2ca02c" if p < 0.05 else "#d62728" for p in report["adf_p_original"]]
    axes[0].bar([i - w / 2 for i in x], report["adf_p_original"], w,
                label="ADF p-valor", color=adf_colors, alpha=0.8, edgecolor="white")
    axes[0].bar([i + w / 2 for i in x], report["kpss_p_original"], w,
                label="KPSS p-valor", color="#1f77b4", alpha=0.5, edgecolor="white")
    axes[0].axhline(0.05, color="red", linestyle="--", linewidth=1, label="sig=0.05")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(report["produto"], rotation=45, ha="right")
    axes[0].set_ylabel("p-valor")
    axes[0].set_title("Testes ADF e KPSS — serie original")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, axis="y", alpha=0.3)

    adf_d_colors = ["#2ca02c" if p < 0.05 else "#d62728" for p in report["adf_p_diff1"]]
    axes[1].bar([i - w / 2 for i in x], report["adf_p_diff1"], w,
                label="ADF p-valor (diff)", color=adf_d_colors, alpha=0.8, edgecolor="white")
    axes[1].bar([i + w / 2 for i in x], report["kpss_p_diff1"], w,
                label="KPSS p-valor (diff)", color="#1f77b4", alpha=0.5, edgecolor="white")
    axes[1].axhline(0.05, color="red", linestyle="--", linewidth=1, label="sig=0.05")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(report["produto"], rotation=45, ha="right")
    axes[1].set_ylabel("p-valor")
    axes[1].set_title("Testes ADF e KPSS — 1a diferenca")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, axis="y", alpha=0.3)

    fig.suptitle("Teste de Estacionariedade (ADF e KPSS)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    _save(fig, "06_estacionariedade.png", save_dir)

    return report


# ──────────────────────────────────────────────
# 7. Importância das variáveis (Random Forest)
# ──────────────────────────────────────────────

def plot_feature_importance(
    df: pd.DataFrame,
    produto_cod: str,
    test_months: int = 4,
    save_dir: Path = PLOTS_DIR,
) -> pd.Series:
    """
    Calcula e plota a importância das variáveis exógenas via Random Forest.
    Usa apenas dados de treino (exclui os últimos test_months meses).
    """
    ts = _monthly_ts(df, produto_cod)
    exog = _exog_features(df, produto_cod).reindex(ts.index).ffill().fillna(0)
    common = ts.index.intersection(exog.index)
    ts, exog = ts.loc[common], exog.loc[common]

    ts_train = ts.iloc[:-test_months]
    exog_train = exog.iloc[:-test_months]

    rf = RandomForestRegressor(n_estimators=200, random_state=42)
    rf.fit(exog_train, ts_train)
    importances = pd.Series(rf.feature_importances_, index=exog.columns)
    importances = importances / importances.sum()
    importances = importances.sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    threshold = importances.quantile(0.6)
    colors = ["#2ca02c" if v >= threshold else "#aec7e8" for v in importances.values]
    bars = ax.barh(importances.index, importances.values, color=colors, edgecolor="white")
    ax.axvline(importances.mean(), color="red", linestyle="--", linewidth=1,
               label=f"Media ({importances.mean():.3f})")
    ax.set_xlabel("Importancia relativa (RF)")
    ax.set_title(f"Importancia das variaveis exogenas — Produto {produto_cod}", fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    for bar, val in zip(bars, importances.values):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=7)

    plt.tight_layout()
    _save(fig, f"07_importancia_{str(produto_cod)}.png", save_dir)
    return importances.sort_values(ascending=False)


# ──────────────────────────────────────────────
# 8. Perfil sazonal
# ──────────────────────────────────────────────

def plot_seasonal_profile(
    df: pd.DataFrame,
    products: list,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Perfil sazonal médio: quantidade média vendida por mês do ano."""
    MONTH_NAMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    n = len(products)
    ncols = 2
    nrows = (n + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 4))
    axes = axes.flatten()

    for i, prod in enumerate(products):
        ts = _monthly_ts(df, prod)
        profile = ts.groupby(ts.index.month).mean()
        ax = axes[i]
        colors = ["#d62728" if m in [10, 11, 12, 5] else "#1f77b4" for m in profile.index]
        ax.bar(profile.index, profile.values, color=colors, edgecolor="white", alpha=0.8)
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(MONTH_NAMES, rotation=45, ha="right", fontsize=8)
        ax.set_title(f"Produto {prod}", fontsize=10, fontweight="bold")
        ax.set_ylabel("Qtd media")
        ax.axhline(profile.mean(), color="black", linestyle="--", linewidth=0.8, label="Media geral")
        ax.legend(fontsize=7)
        ax.grid(True, axis="y", alpha=0.3)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    red_patch = plt.Rectangle((0, 0), 1, 1, fc="#d62728", alpha=0.8)
    blue_patch = plt.Rectangle((0, 0), 1, 1, fc="#1f77b4", alpha=0.8)
    fig.legend([red_patch, blue_patch], ["Alta temporada", "Outros meses"],
               loc="lower right", fontsize=9)
    fig.suptitle("Perfil sazonal medio por mes do ano", fontsize=13, fontweight="bold")
    plt.tight_layout()
    _save(fig, "08_perfil_sazonal.png", save_dir)


# ──────────────────────────────────────────────
# 9. Visão geral do mercado
# ──────────────────────────────────────────────

def plot_market_overview(
    df: pd.DataFrame,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Painel com evolucao mensal de volume total, receita, clientes e preco medio."""
    period = df["emissao"].dt.to_period("M")
    mkt = df.groupby(period).agg(
        qtd_total=("qtdade", "sum"),
        valor_total=("vl_total", "sum"),
        n_clientes=("cliente_cod", "nunique"),
        n_pedidos=("doc_numero", "nunique"),
        preco_medio=("vl_unit", "mean"),
    )
    mkt.index = mkt.index.to_timestamp()

    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)

    panels = [
        ("qtd_total", "Volume total (unidades)", "#1f77b4"),
        ("valor_total", "Receita total (R$)", "#2ca02c"),
        ("n_clientes", "Clientes unicos", "#ff7f0e"),
        ("preco_medio", "Preco medio (R$)", "#9467bd"),
    ]

    for ax, (col, label, color) in zip(axes.flatten(), panels):
        ax.plot(mkt.index, mkt[col], color=color, linewidth=2)
        ax.fill_between(mkt.index, mkt[col], alpha=0.1, color=color)
        ax.set_ylabel(label)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        ax.grid(True, alpha=0.3)

        # Linha de tendencia linear
        x_num = np.arange(len(mkt))
        coef = np.polyfit(x_num, mkt[col], 1)
        trend = np.poly1d(coef)(x_num)
        ax.plot(mkt.index, trend, "r--", linewidth=1, label=f"Tendencia: {coef[0]:+.1f}/mes")
        ax.legend(fontsize=7)

    fig.suptitle("Visao geral do mercado — evolucao mensal", fontsize=13, fontweight="bold")
    plt.tight_layout()
    _save(fig, "09_mercado_overview.png", save_dir)


# ──────────────────────────────────────────────
# 10. Pipeline completo de análise
# ──────────────────────────────────────────────

def run_full_analysis(
    df: pd.DataFrame,
    products: list,
    ref_product: str = None,
    test_months: int = 4,
    save_dir: Path = PLOTS_DIR,
    verbose: bool = True,
) -> dict:
    """
    Executa toda a análise estatística exploratória e salva os gráficos.

    Retorna dict com:
      - cv_stats: DataFrame com CV por produto
      - stationarity: DataFrame com testes ADF/KPSS por produto
      - correlations: Series com correlacoes do produto de referencia
      - importances: Series com importancias RF do produto de referencia
    """
    if ref_product is None:
        ref_product = products[0]

    if verbose:
        print(f"Analise estatistica — {len(products)} produtos")
        print(f"Produto de referencia: {ref_product}")
        print(f"Graficos em: {Path(save_dir)}\n")

    if verbose:
        print("1/6 Series mensais...")
    plot_monthly_series(df, products, save_dir)

    if verbose:
        print("2/6 Distribuicao da demanda...")
    plot_demand_distribution(df, products, save_dir)

    if verbose:
        print("3/6 Coeficiente de variacao...")
    cv_stats = plot_demand_cv_analysis(df, products, save_dir=save_dir)

    if verbose:
        print(f"4/6 Estacionariedade...")
    stationarity = plot_stationarity_report(df, products, save_dir)

    if verbose:
        print(f"5/6 Perfil sazonal...")
    plot_seasonal_profile(df, products, save_dir)

    if verbose:
        print("6/6 Visao geral do mercado...")
    plot_market_overview(df, save_dir)

    # Análises focadas no produto de referência
    if verbose:
        print(f"\nAnalisando produto de referencia: {ref_product}")
        print("  Correlacoes...")
    correlations = plot_correlation_with_target(df, ref_product, save_dir)

    if verbose:
        print("  Heatmap...")
    plot_correlation_heatmap(df, ref_product, save_dir)

    if verbose:
        print("  Importancia de variaveis...")
    importances = plot_feature_importance(df, ref_product, test_months, save_dir)

    if verbose:
        print("\nAnalise concluida.")
        print(f"\nCV por produto:")
        print(cv_stats[["produto_cod", "media", "std", "cv", "tipo"]].to_string(index=False))
        print(f"\nEstacionariedade:")
        print(stationarity[["produto", "adf_p_original", "kpss_p_original", "estac_original"]].to_string(index=False))

    return {
        "cv_stats": cv_stats,
        "stationarity": stationarity,
        "correlations": correlations,
        "importances": importances,
    }
