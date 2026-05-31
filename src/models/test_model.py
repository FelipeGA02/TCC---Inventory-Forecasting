"""
Teste do modelo SARIMAX em frequencia DIARIA com janelas de 7, 14 e 30 dias.

O modelo mensal e usado para planejamento de longo prazo (1-4 meses).
Este modulo treina um SARIMAX diario (sazonalidade semanal s=7) para previsao
de curto prazo, avaliando o desempenho em janelas de 7, 14 e 30 dias.

Funcoes:
  prepare_daily_series    -> serie diaria de quantidade vendida
  build_daily_exog        -> features exogenas diarias (mercado + calendario)
  run_daily_sarimax       -> pipeline completo diario para um produto
  run_daily_pipeline      -> executa para N produtos e compara janelas
  plot_window_comparison  -> grafico comparativo das 3 janelas
  plot_daily_forecast     -> serie diaria com previsao e IC
"""

import warnings
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"
TEST_PLOTS_DIR = RESULTS_DIR / "plots" / "test"
METRICS_DIR = RESULTS_DIR / "metrics"

HORIZONS = [7, 14, 30]   # janelas de previsao em dias


# ──────────────────────────────────────────────
# Metricas
# ──────────────────────────────────────────────

def _metrics(y_true, y_pred) -> dict:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2 + 1e-9
    smape = np.mean(np.abs(y_true - y_pred) / denom) * 100
    threshold = np.mean(y_true) * 0.05
    mask = y_true > threshold
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() else np.nan
    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan
    return {"MAE": mae, "RMSE": rmse, "MAPE_%": mape, "SMAPE_%": smape, "R2": r2}


# ──────────────────────────────────────────────
# 1. Preparacao dos dados diarios
# ──────────────────────────────────────────────

def prepare_daily_series(df: pd.DataFrame, produto_cod: str) -> pd.Series:
    """Agrega vendas diarias do produto e preenche dias sem venda com 0."""
    mask = df["produto_cod"].astype(str) == str(produto_cod)
    prod = df[mask].copy()
    daily = prod.groupby(prod["emissao"].dt.date)["qtdade"].sum()
    daily.index = pd.to_datetime(daily.index)
    # Reindex para preencher dias faltantes
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_idx, fill_value=0)
    return daily


def build_daily_exog(df: pd.DataFrame, produto_cod: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Features exogenas diarias:
      - Volume total diario do mercado
      - Numero de pedidos diarios
      - Dia da semana (0=seg ... 6=dom)
      - Dia do mes
      - Flag fim de semana
      - Flag alta temporada (out/nov/dez/mai)
    """
    # Mercado geral (diario)
    mkt = df.groupby(df["emissao"].dt.date).agg(
        mkt_qtd=("qtdade", "sum"),
        mkt_n_pedidos=("doc_numero", "nunique"),
        mkt_valor=("vl_total", "sum"),
    )
    mkt.index = pd.to_datetime(mkt.index)
    mkt = mkt.reindex(index, fill_value=0)

    exog = pd.DataFrame(index=index)
    exog["mkt_qtd"] = mkt["mkt_qtd"]
    exog["mkt_n_pedidos"] = mkt["mkt_n_pedidos"]
    exog["mkt_valor"] = mkt["mkt_valor"]
    exog["dia_semana"] = index.dayofweek
    exog["dia_mes"] = index.day
    exog["fim_semana"] = index.dayofweek.isin([5, 6]).astype(int)
    exog["alta_temporada"] = index.month.isin([10, 11, 12, 5]).astype(int)
    # Media movel de 7 dias da demanda de mercado (lags para nao vazar futuro)
    exog["mkt_qtd_ma7"] = exog["mkt_qtd"].shift(1).rolling(7, min_periods=1).mean().fillna(0)

    return exog


# ──────────────────────────────────────────────
# 2. Importancia e ponderacao de features
# ──────────────────────────────────────────────

def _compute_importance(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    imp = pd.Series(rf.feature_importances_, index=X.columns)
    return imp / imp.sum()


def _weight(X: pd.DataFrame, imp: pd.Series) -> pd.DataFrame:
    w = imp.reindex(X.columns).fillna(0).clip(lower=0.1)
    return X * w.values


# ──────────────────────────────────────────────
# 3. Selecao de ordem diaria
# ──────────────────────────────────────────────

def _select_daily_order(
    ts: pd.Series,
    exog: pd.DataFrame,
    d: int = 0,
    m: int = 7,
) -> tuple:
    """Grid search sobre ordens baixas (desempenho aceitavel com series longas)."""
    best_aic = np.inf
    best_order = (1, d, 1)
    best_seasonal = (1, 0, 0, m)

    for p, q, P, Q in itertools.product(range(0, 3), range(0, 3),
                                         range(0, 2), range(0, 2)):
        try:
            mod = SARIMAX(
                ts, exog=exog,
                order=(p, d, q),
                seasonal_order=(P, 0, Q, m),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            res = mod.fit(disp=False, maxiter=200)
            if res.aic < best_aic:
                best_aic = res.aic
                best_order = (p, d, q)
                best_seasonal = (P, 0, Q, m)
        except Exception:
            continue

    return best_order, best_seasonal


# ──────────────────────────────────────────────
# 4. Pipeline diario por produto
# ──────────────────────────────────────────────

def run_daily_sarimax(
    df: pd.DataFrame,
    produto_cod: str,
    horizons: list = None,
    min_obs: int = 90,
    verbose: bool = True,
) -> dict:
    """
    Treina e testa um SARIMAX diario para o produto com janelas de previsao
    de 7, 14 e 30 dias.

    Estrategia:
      - Treino: todos os dias menos max(horizons)
      - Teste: ultimos max(horizons) dias
      - Para cada horizonte h: preve os proximos h dias a partir do fim do treino
      - Calcula MAE, RMSE, SMAPE, R2 para cada janela

    Retorna dict com metricas por horizonte, modelos e previsoes.
    """
    if horizons is None:
        horizons = HORIZONS

    if verbose:
        print(f"\n{'='*55}")
        print(f"  Produto (diario): {produto_cod}")
        print(f"{'='*55}")

    ts = prepare_daily_series(df, produto_cod)

    if len(ts) < min_obs:
        raise ValueError(
            f"Produto {produto_cod} tem apenas {len(ts)} dias (min={min_obs})."
        )

    exog = build_daily_exog(df, produto_cod, ts.index)

    # Transformacao log se CV alto
    cv = ts.std() / (ts.mean() + 1e-9)
    use_log = cv > 1.0
    ts_model = np.log1p(ts) if use_log else ts.copy()

    if verbose:
        print(f"  {len(ts)} dias | CV={cv:.2f} | log={use_log}")

    # Treina com todos menos max(horizons) dias
    max_h = max(horizons)
    cut = len(ts) - max_h
    ts_train = ts_model.iloc[:cut]
    exog_train = exog.iloc[:cut]

    # Importancia das features
    imp = _compute_importance(exog_train, ts_train)
    exog_train_w = _weight(exog_train, imp)

    if verbose:
        top3 = imp.sort_values(ascending=False).head(3)
        print(f"  Top features: {dict(top3.round(3))}")

    # Estacionariedade
    adf_p = adfuller(ts_train.dropna())[1]
    d = 1 if adf_p > 0.05 else 0
    if verbose:
        print(f"  ADF p={adf_p:.4f} -> d={d}")

    # Selecao de ordem
    if verbose:
        print("  Selecionando ordem SARIMAX(p,d,q)(P,0,Q,7)...")
    order, seasonal_order = _select_daily_order(ts_train, exog_train_w, d=d, m=7)
    if verbose:
        print(f"  Ordem: SARIMAX{order} x {seasonal_order}")

    # Ajuste
    mod = SARIMAX(
        ts_train, exog=exog_train_w,
        order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    result = mod.fit(disp=False, maxiter=300)
    if verbose:
        print(f"  AIC={result.aic:.2f}")

    # Avaliacao por horizonte
    horizon_metrics = {}
    horizon_preds = {}

    for h in sorted(horizons):
        ts_test = ts.iloc[cut: cut + h]   # escala original
        exog_test = exog.iloc[cut: cut + h]
        exog_test_w = _weight(exog_test, imp)

        try:
            pred_log = result.forecast(steps=h, exog=exog_test_w)
            pred = np.expm1(pred_log).clip(0) if use_log else pred_log.clip(0)
            pred = pd.Series(pred.values, index=ts_test.index)

            m = _metrics(ts_test.values, pred.values)
            horizon_metrics[h] = m
            horizon_preds[h] = {"real": ts_test, "previsto": pred}

            if verbose:
                print(f"  Janela {h:2d} dias | MAE={m['MAE']:7.1f} | "
                      f"SMAPE={m['SMAPE_%']:5.1f}% | R2={m['R2']:6.3f}")
        except Exception as e:
            if verbose:
                print(f"  Janela {h} dias: erro — {e}")

    return {
        "produto_cod": str(produto_cod),
        "model": result,
        "order": order,
        "seasonal_order": seasonal_order,
        "use_log": use_log,
        "importances": imp,
        "ts_train": ts.iloc[:cut],
        "horizon_metrics": horizon_metrics,
        "horizon_preds": horizon_preds,
    }


# ──────────────────────────────────────────────
# 5. Visualizacao
# ──────────────────────────────────────────────

def plot_daily_forecast(
    pipe: dict,
    save_dir: Path = TEST_PLOTS_DIR,
    context_days: int = 60,
) -> None:
    """
    Grafico das previsoes das 3 janelas sobrepostas na serie diaria.
    Mostra os ultimos `context_days` dias de historico + as janelas de teste.
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    prod = pipe["produto_cod"]
    ts_train = pipe["ts_train"]
    colors = {7: "#2ca02c", 14: "#ff7f0e", 30: "#d62728"}

    fig, ax = plt.subplots(figsize=(14, 5))

    # Historico recente
    hist = ts_train.iloc[-context_days:]
    ax.plot(hist.index, hist.values, color="#1f77b4", linewidth=1.5, label="Historico")

    # Linha de corte
    ax.axvline(ts_train.index[-1], color="gray", linestyle=":", linewidth=1.2, label="Inicio do teste")

    # Previsoes por janela
    for h, color in colors.items():
        if h not in pipe["horizon_preds"]:
            continue
        real = pipe["horizon_preds"][h]["real"]
        prev = pipe["horizon_preds"][h]["previsto"]
        m = pipe["horizon_metrics"][h]

        ax.plot(real.index, real.values, "o-", color=color, linewidth=1.5,
                markersize=4, alpha=0.7)
        ax.plot(prev.index, prev.values, "s--", color=color, linewidth=2,
                markersize=5, label=f"Prev. {h}d | SMAPE={m['SMAPE_%']:.1f}%")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%b"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_ylabel("Quantidade diaria")
    ax.set_title(f"Previsao diaria — Produto {prod} | SARIMAX{pipe['order']} x {pipe['seasonal_order']}",
                 fontsize=11)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    fname = save_dir / f"daily_{str(prod).replace('/', '_')}_forecast.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {fname.name}")


def plot_window_comparison(
    summary: pd.DataFrame,
    save_dir: Path = TEST_PLOTS_DIR,
) -> None:
    """
    Grafico comparativo de SMAPE e R2 por janela (7, 14, 30 dias) para cada produto.
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    horizons = sorted(summary["horizonte_dias"].unique())
    products = summary["produto_cod"].unique()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    colors = plt.cm.tab10(np.linspace(0, 1, len(products)))
    x = np.arange(len(horizons))
    bar_w = 0.8 / len(products)

    for i, (prod, color) in enumerate(zip(products, colors)):
        sub = summary[summary["produto_cod"] == prod].sort_values("horizonte_dias")
        offset = (i - len(products) / 2 + 0.5) * bar_w
        axes[0].bar(x + offset, sub["SMAPE_%"], bar_w, label=str(prod),
                    color=color, alpha=0.8, edgecolor="white")
        axes[1].bar(x + offset, sub["R2"].clip(lower=-1), bar_w,
                    color=color, alpha=0.8, edgecolor="white")

    for ax, ylabel, title, ref in [
        (axes[0], "SMAPE (%)", "SMAPE por janela de previsao", 30),
        (axes[1], "R2", "R2 por janela de previsao", 0.7),
    ]:
        ax.set_xticks(x)
        ax.set_xticklabels([f"{h} dias" for h in horizons])
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.axhline(ref, color="green", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.grid(True, axis="y", alpha=0.3)

    axes[0].legend(fontsize=7, loc="upper left", ncol=2)
    axes[0].axhline(60, color="orange", linestyle="--", linewidth=0.8, alpha=0.7)

    fig.suptitle("Comparacao de janelas de previsao (7 / 14 / 30 dias)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()

    path = save_dir / "comparacao_janelas.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {path.name}")


def plot_smape_heatmap(
    summary: pd.DataFrame,
    save_dir: Path = TEST_PLOTS_DIR,
) -> None:
    """Heatmap de SMAPE: produtos x janelas."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    import seaborn as sns
    pivot = summary.pivot(index="produto_cod", columns="horizonte_dias", values="SMAPE_%")
    pivot.columns = [f"{c} dias" for c in pivot.columns]

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        pivot, annot=True, fmt=".1f", cmap="RdYlGn_r",
        vmin=0, vmax=100, ax=ax, linewidths=0.5,
        cbar_kws={"label": "SMAPE (%)"},
    )
    ax.set_title("SMAPE (%) por produto e janela de previsao", fontsize=11)
    ax.set_xlabel("Janela")
    ax.set_ylabel("Produto")
    plt.tight_layout()

    path = save_dir / "heatmap_smape_janelas.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {path.name}")


# ──────────────────────────────────────────────
# 6. Pipeline completo (N produtos)
# ──────────────────────────────────────────────

def run_daily_pipeline(
    df: pd.DataFrame,
    products: list,
    horizons: list = None,
    min_obs: int = 90,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Executa o pipeline diario para todos os produtos e retorna DataFrame
    com metricas por produto x janela.

    Tambem salva os graficos e o CSV de metricas em results/.
    """
    if horizons is None:
        horizons = HORIZONS

    all_rows = []
    all_pipes = {}
    errors = []

    for prod in products:
        try:
            pipe = run_daily_sarimax(df, prod, horizons=horizons,
                                     min_obs=min_obs, verbose=verbose)
            all_pipes[prod] = pipe

            for h, m in pipe["horizon_metrics"].items():
                all_rows.append({
                    "produto_cod": str(prod),
                    "horizonte_dias": h,
                    **m,
                    "ordem": str(pipe["order"]),
                    "ordem_sazonal": str(pipe["seasonal_order"]),
                    "log_transform": pipe["use_log"],
                })

            plot_daily_forecast(pipe, TEST_PLOTS_DIR)

        except Exception as e:
            errors.append({"produto_cod": str(prod), "erro": str(e)})
            if verbose:
                print(f"  [ERRO] {prod}: {e}")

    summary = pd.DataFrame(all_rows)

    if not summary.empty:
        # Graficos comparativos
        plot_window_comparison(summary, TEST_PLOTS_DIR)
        plot_smape_heatmap(summary, TEST_PLOTS_DIR)

        # CSV
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        path = METRICS_DIR / "metricas_diarias_janelas.csv"
        summary.to_csv(path, index=False, sep=";")
        if verbose:
            print(f"\nMetricas diarias salvas: {path}")

            print("\n=== RESUMO — Metricas diarias por janela ===")
            pivot = summary.pivot_table(
                index="produto_cod", columns="horizonte_dias",
                values="SMAPE_%", aggfunc="mean"
            )
            pivot.columns = [f"SMAPE_{c}d" for c in pivot.columns]
            print(pivot.round(1).to_string())

    if errors:
        err_df = pd.DataFrame(errors)
        err_path = METRICS_DIR / "erros_diarios.csv"
        err_df.to_csv(err_path, index=False, sep=";")
        if verbose:
            print(f"\nErros: {err_path}")
            for e in errors:
                print(f"  {e}")

    return summary
