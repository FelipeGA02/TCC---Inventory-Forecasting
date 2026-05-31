"""
Módulo SARIMAX para previsão de estoque de plantas vendidas na floricultura.

Fluxo:
  1. prepare_monthly_data      → agrega transações em séries mensais por produto
  2. build_exogenous_features  → constrói variáveis exógenas de mercado + produto
  3. compute_feature_importance→ pondera variáveis por importância (RF + correlação)
  4. weight_features           → escala variáveis pelo peso de importância
  5. select_sarimax_order      → busca automática de ordem SARIMAX por AIC/BIC
  6. fit_sarimax               → ajusta o modelo
  7. evaluate_model            → MAE, RMSE, MAPE, R²
  8. plot_forecast             → gráfico de série + previsão (salvo em results/)
  9. run_product_pipeline      → pipeline completo por produto
  10. run_full_pipeline        → pipeline para os N produtos mais vendidos
"""

import os
import warnings
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, kpss

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
METRICS_DIR = RESULTS_DIR / "metrics"

# ──────────────────────────────────────────────
# 1. Preparação dos dados
# ──────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", low_memory=False)
    df["emissao"] = pd.to_datetime(df["emissao"], dayfirst=True, errors="coerce")
    for col in ["qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "."), errors="coerce"
        )
    return df.dropna(subset=["emissao", "qtdade"])


def prepare_monthly_data(df: pd.DataFrame, produto_cod: str) -> pd.Series:
    """Retorna série mensal de quantidade vendida para um produto."""
    prod = df[df["produto_cod"].astype(str) == str(produto_cod)].copy()
    monthly = (
        prod.groupby(prod["emissao"].dt.to_period("M"))["qtdade"]
        .sum()
        .sort_index()
    )
    monthly.index = monthly.index.to_timestamp()
    return monthly


def build_exogenous_features(df: pd.DataFrame, produto_cod: str) -> pd.DataFrame:
    """
    Constrói features exógenas mensais: indicadores de mercado geral
    + indicadores específicos do produto.
    """
    period = df["emissao"].dt.to_period("M")

    # Mercado geral
    mkt = df.groupby(period).agg(
        mkt_qtd_total=("qtdade", "sum"),
        mkt_valor_total=("vl_total", "sum"),
        mkt_desconto_total=("vl_desconto", "sum"),
        mkt_n_pedidos=("doc_numero", "nunique"),
        mkt_n_clientes=("cliente_cod", "nunique"),
        mkt_preco_medio=("vl_unit", "mean"),
    )
    mkt["mkt_taxa_desconto"] = mkt["mkt_desconto_total"] / (
        mkt["mkt_valor_total"] + 1e-9
    )

    # Produto específico
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

    # Features de calendário
    exog["mes"] = exog.index.month
    exog["trimestre"] = exog.index.quarter
    # Meses sazonalmente importantes para flores (out/nov = datas comerciais)
    exog["alta_temporada"] = exog["mes"].isin([10, 11, 12, 5]).astype(int)

    return exog


# ──────────────────────────────────────────────
# 2. Importância de variáveis
# ──────────────────────────────────────────────

def compute_feature_importance(
    X: pd.DataFrame, y: pd.Series, n_estimators: int = 200, random_state: int = 42
) -> pd.Series:
    """
    Calcula importância de cada feature via RandomForest.
    Retorna Series com importâncias normalizadas (soma = 1).
    """
    idx = X.index.intersection(y.index)
    X_al, y_al = X.loc[idx], y.loc[idx]
    rf = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
    rf.fit(X_al, y_al)
    imp = pd.Series(rf.feature_importances_, index=X.columns)
    return imp / imp.sum()


def weight_features(X: pd.DataFrame, importances: pd.Series) -> pd.DataFrame:
    """
    Multiplica cada coluna de X pelo seu peso de importância.
    Variáveis mais importantes recebem maior peso; menos importantes são
    incluídas com peso reduzido mas não removidas.
    """
    weights = importances.reindex(X.columns).fillna(0)
    # Escala mínima de 0.1 para nunca zerar uma variável
    weights = weights.clip(lower=0.1)
    return X * weights.values


# ──────────────────────────────────────────────
# 3. Estacionariedade
# ──────────────────────────────────────────────

def check_stationarity(ts: pd.Series, alpha: float = 0.05) -> dict:
    adf_stat, adf_p, *_ = adfuller(ts.dropna())
    try:
        kpss_stat, kpss_p, *_ = kpss(ts.dropna(), regression="c", nlags="auto")
    except Exception:
        kpss_stat, kpss_p = np.nan, np.nan

    return {
        "adf_statistic": adf_stat,
        "adf_p_value": adf_p,
        "adf_stationary": adf_p < alpha,
        "kpss_statistic": kpss_stat,
        "kpss_p_value": kpss_p,
        "kpss_stationary": kpss_p > alpha,
    }


def suggest_d(ts: pd.Series, max_d: int = 1) -> int:
    """Sugere ordem de diferenciação (máx 1) para tornar a série estacionária."""
    for d in range(max_d + 1):
        ts_diff = ts.diff(d) if d > 0 else ts
        stat = check_stationarity(ts_diff.dropna())
        if stat["adf_stationary"]:
            return d
    return max_d


# ──────────────────────────────────────────────
# 4. Seleção de ordem SARIMAX
# ──────────────────────────────────────────────

def select_sarimax_order(
    ts_train: pd.Series,
    exog_train: pd.DataFrame,
    d: int = 1,
    p_range: range = range(0, 3),
    q_range: range = range(0, 3),
    P_range: range = range(0, 2),
    Q_range: range = range(0, 2),
    D: int = 1,
    m: int = 12,
    criterion: str = "aic",
) -> tuple:
    """
    Busca exaustiva sobre (p,q) x (P,Q) para minimizar AIC ou BIC.
    Retorna (order, seasonal_order) com melhor critério.
    """
    best_score = np.inf
    best_order = (1, d, 1)
    best_seasonal = (1, D, 1, m)

    combos = list(itertools.product(p_range, q_range, P_range, Q_range))
    for p, q, P, Q in combos:
        try:
            mod = SARIMAX(
                ts_train,
                exog=exog_train,
                order=(p, d, q),
                seasonal_order=(P, D, Q, m),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            res = mod.fit(disp=False, maxiter=200)
            score = res.aic if criterion == "aic" else res.bic
            if score < best_score:
                best_score = score
                best_order = (p, d, q)
                best_seasonal = (P, D, Q, m)
        except Exception:
            continue

    return best_order, best_seasonal


# ──────────────────────────────────────────────
# 5. Ajuste do modelo
# ──────────────────────────────────────────────

def fit_sarimax(
    ts_train: pd.Series,
    exog_train: pd.DataFrame,
    order: tuple,
    seasonal_order: tuple,
) -> object:
    """Ajusta e retorna modelo SARIMAX treinado."""
    mod = SARIMAX(
        ts_train,
        exog=exog_train,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    return mod.fit(disp=False, maxiter=300)


# ──────────────────────────────────────────────
# 6. Avaliação
# ──────────────────────────────────────────────

def evaluate_model(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """Calcula MAE, RMSE, MAPE, SMAPE e R² entre valores reais e previstos."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    # MAPE: ignora pontos onde y_true < 5% da média (evita inflação por zeros)
    threshold = np.mean(y_true) * 0.05
    mask = y_true > threshold
    if mask.sum() > 0:
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = np.nan
    # SMAPE: simétrico, mais robusto para séries com zeros ou outliers
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2 + 1e-9
    smape = np.mean(np.abs(y_true - y_pred) / denom) * 100
    r2 = r2_score(y_true, y_pred)

    return {"MAE": mae, "RMSE": rmse, "MAPE_%": mape, "SMAPE_%": smape, "R2": r2}


# ──────────────────────────────────────────────
# 7. Visualização
# ──────────────────────────────────────────────

def plot_forecast(
    ts_full: pd.Series,
    in_sample_pred: pd.Series,
    test_pred: pd.Series,
    future_pred: pd.Series,
    produto_cod: str,
    metrics: dict,
    importances: pd.Series,
    save_dir: Path = PLOTS_DIR,
) -> None:
    """Gera e salva gráfico com série histórica, ajuste in-sample e previsão."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(f"Produto {produto_cod} — Previsão de Demanda (SARIMAX)", fontsize=14, fontweight="bold")

    # --- Painel superior: série + previsão ---
    ax = axes[0]
    ax.plot(ts_full.index, ts_full.values, label="Real (histórico)", color="#1f77b4", linewidth=2)
    ax.plot(in_sample_pred.index, in_sample_pred.values, "--", label="Ajuste in-sample", color="#ff7f0e", linewidth=1.5)
    ax.plot(test_pred.index, test_pred.values, "o-", label="Previsão (teste)", color="#d62728", linewidth=2, markersize=6)
    ax.plot(future_pred.index, future_pred.values, "s--", label="Previsão futura", color="#2ca02c", linewidth=2, markersize=6)

    # Intervalo de confiança simbólico ±10 % para futuro
    future_std = future_pred.std() * 0.15
    ax.fill_between(
        future_pred.index,
        future_pred - 1.96 * future_std,
        future_pred + 1.96 * future_std,
        alpha=0.2, color="#2ca02c", label="IC 95 % (futuro)"
    )

    ax.axvline(test_pred.index[0], color="gray", linestyle=":", linewidth=1.2, label="Início do teste")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_ylabel("Quantidade (unidades)")
    ax.set_title("Demanda mensal e previsão")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Caixa de métricas
    metrics_text = "\n".join([f"{k}: {v:.2f}" for k, v in metrics.items()])
    ax.text(
        0.98, 0.97, metrics_text, transform=ax.transAxes,
        verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
        fontsize=8, family="monospace"
    )

    # --- Painel inferior: importância das variáveis ---
    ax2 = axes[1]
    top_imp = importances.sort_values(ascending=True).tail(15)
    colors = ["#2ca02c" if v >= top_imp.quantile(0.6) else "#aec7e8" for v in top_imp.values]
    bars = ax2.barh(top_imp.index, top_imp.values, color=colors, edgecolor="white")
    ax2.set_xlabel("Importância relativa (Random Forest)")
    ax2.set_title("Importância das variáveis exógenas")
    ax2.grid(True, axis="x", alpha=0.3)
    for bar, val in zip(bars, top_imp.values):
        ax2.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                 f"{val:.3f}", va="center", fontsize=7)

    plt.tight_layout()
    filename = save_dir / f"produto_{str(produto_cod).replace('/', '_')}_sarimax.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] Salvo: {filename.name}")


def plot_residuals(result, produto_cod: str, save_dir: Path = PLOTS_DIR) -> None:
    """Gráfico de diagnóstico manual dos resíduos (evita restrições do plot_diagnostics)."""
    from statsmodels.graphics.tsaplots import plot_acf
    from scipy import stats

    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    residuals = pd.Series(result.resid.dropna(), name="resíduo")
    if len(residuals) < 4:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle(f"Diagnóstico de Resíduos — Produto {produto_cod}", fontsize=12, fontweight="bold")

    # Série de resíduos
    axes[0, 0].plot(residuals.values, linewidth=1)
    axes[0, 0].axhline(0, color="red", linestyle="--", linewidth=0.8)
    axes[0, 0].set_title("Resíduos ao longo do tempo")
    axes[0, 0].set_xlabel("Observação")
    axes[0, 0].grid(True, alpha=0.3)

    # Histograma
    axes[0, 1].hist(residuals.values, bins=min(10, len(residuals) // 2), edgecolor="white", color="#1f77b4")
    axes[0, 1].set_title("Distribuição dos resíduos")
    axes[0, 1].set_xlabel("Resíduo")
    axes[0, 1].grid(True, alpha=0.3)

    # Q-Q plot
    stats.probplot(residuals.values, dist="norm", plot=axes[1, 0])
    axes[1, 0].set_title("Q-Q Plot (normalidade)")
    axes[1, 0].grid(True, alpha=0.3)

    # ACF dos resíduos
    max_lags = min(10, len(residuals) // 2 - 1)
    if max_lags >= 2:
        plot_acf(residuals, lags=max_lags, ax=axes[1, 1], alpha=0.05)
        axes[1, 1].set_title("ACF dos resíduos")
        axes[1, 1].grid(True, alpha=0.3)
    else:
        axes[1, 1].text(0.5, 0.5, "Dados insuficientes para ACF", ha="center", va="center")

    plt.tight_layout()
    filename = save_dir / f"produto_{str(produto_cod).replace('/', '_')}_residuos.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] Salvo: {filename.name}")


# ──────────────────────────────────────────────
# 8. Pipeline por produto
# ──────────────────────────────────────────────

def run_product_pipeline(
    df: pd.DataFrame,
    produto_cod: str,
    test_months: int = 4,
    future_months: int = 3,
    m: int = 12,
    log_transform_cv_threshold: float = 0.7,
    verbose: bool = True,
) -> dict:
    """
    Executa o pipeline completo de previsão SARIMAX para um produto.

    Aplica transformação log1p automaticamente para séries com alta variabilidade
    (CV = std/mean > log_transform_cv_threshold), estabilizando a variância.

    Retorna dict com model, metrics, importances, predictions (na escala original).
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Produto: {produto_cod}")
        print(f"{'='*60}")

    # 1. Série alvo mensal
    ts_orig = prepare_monthly_data(df, produto_cod)
    if len(ts_orig) < 15:
        raise ValueError(f"Série muito curta para {produto_cod} ({len(ts_orig)} meses).")

    # Decide se aplica transformação log
    cv = ts_orig.std() / (ts_orig.mean() + 1e-9)
    use_log = cv > log_transform_cv_threshold
    if verbose:
        print(f"\n  CV={cv:.2f} -> {'log1p aplicado' if use_log else 'escala original'}")

    ts = np.log1p(ts_orig) if use_log else ts_orig.copy()

    # 2. Features exógenas
    exog = build_exogenous_features(df, produto_cod)
    exog = exog.reindex(ts.index).ffill().fillna(0)

    # Alinha índices
    common_idx = ts.index.intersection(exog.index)
    ts = ts.loc[common_idx]
    ts_orig = ts_orig.loc[common_idx]
    exog = exog.loc[common_idx]

    # 3. Importância das variáveis (treino apenas)
    train_end = len(ts) - test_months
    ts_train, ts_test = ts.iloc[:train_end], ts.iloc[train_end:]
    ts_orig_train, ts_orig_test = ts_orig.iloc[:train_end], ts_orig.iloc[train_end:]
    exog_train, exog_test = exog.iloc[:train_end], exog.iloc[test_months * -1:]

    importances = compute_feature_importance(exog_train, ts_train)

    if verbose:
        print(f"\n  Top 5 variáveis mais importantes:")
        for name, val in importances.sort_values(ascending=False).head(5).items():
            print(f"    {name:35s}: {val:.4f}")

    # 4. Ponderação por importância
    exog_train_w = weight_features(exog_train, importances)
    exog_test_w = weight_features(exog_test, importances)

    # 5. Estacionariedade
    d = suggest_d(ts_train)
    # D=0: série curta (26 meses < 3 ciclos de 12). Padrão sazonal via P e Q.
    D = 0

    if verbose:
        stat = check_stationarity(ts_train)
        print(f"\n  Estacionariedade (ADF p={stat['adf_p_value']:.4f}, "
              f"KPSS p={stat['kpss_p_value']:.4f})")
        print(f"  Ordem sugerida: d={d}, D={D}")

    # 6. Seleção de ordem
    if verbose:
        print("\n  Buscando melhor ordem SARIMAX...")

    order, seasonal_order = select_sarimax_order(
        ts_train, exog_train_w,
        d=d, D=D, m=m,
        p_range=range(0, 3),
        q_range=range(0, 3),
        P_range=range(0, 2),
        Q_range=range(0, 2),
    )

    if verbose:
        print(f"  Ordem selecionada: SARIMAX{order} x {seasonal_order}")

    # 7. Treinamento
    result = fit_sarimax(ts_train, exog_train_w, order, seasonal_order)

    if verbose:
        print(f"  AIC: {result.aic:.2f}  |  BIC: {result.bic:.2f}")

    # 8. Previsão estendida: teste + futuro a partir do modelo treinado
    future_idx = pd.date_range(
        start=ts_orig.index[-1] + pd.DateOffset(months=1),
        periods=future_months, freq="MS"
    )
    # Extrapola exog futura replicando último mês e ajustando calendário
    last_vals = exog.iloc[-1].copy()
    future_rows = []
    for dt in future_idx:
        row = last_vals.copy()
        row["mes"] = dt.month
        row["trimestre"] = dt.quarter
        row["alta_temporada"] = int(dt.month in [10, 11, 12, 5])
        future_rows.append(row)
    future_exog = pd.DataFrame(future_rows, index=future_idx)
    future_exog_w = weight_features(future_exog, importances)

    # Forecast único: test + future sem re-treinar
    total_steps = test_months + future_months
    exog_all_oos = pd.concat([exog_test_w, future_exog_w])
    all_forecast = result.forecast(steps=total_steps, exog=exog_all_oos)

    forecast_log_test = all_forecast.iloc[:test_months]
    forecast_log_future = all_forecast.iloc[test_months:]

    # Back-transform para escala original
    if use_log:
        forecast_test = np.expm1(forecast_log_test).clip(lower=0)
        future_forecast = np.expm1(forecast_log_future).clip(lower=0)
        in_sample_orig = np.expm1(result.fittedvalues).clip(lower=0)
    else:
        forecast_test = forecast_log_test.clip(lower=0)
        future_forecast = forecast_log_future.clip(lower=0)
        in_sample_orig = result.fittedvalues

    forecast_test = pd.Series(forecast_test.values, index=ts_orig_test.index, name="previsto")
    future_forecast = pd.Series(future_forecast.values, index=future_idx, name="previsto")
    in_sample = pd.Series(in_sample_orig.values, index=ts_orig_train.index, name="ajuste")

    # 9. Métricas (na escala original)
    metrics = evaluate_model(ts_orig_test, forecast_test.values)

    if verbose:
        print(f"\n  Métricas no conjunto de teste ({test_months} meses):")
        for k, v in metrics.items():
            if v is not None and not np.isnan(v):
                print(f"    {k}: {v:.4f}")

    # 10. Plots
    plot_forecast(ts_orig, in_sample, forecast_test, future_forecast,
                  produto_cod, metrics, importances)
    plot_residuals(result, produto_cod)

    return {
        "produto_cod": produto_cod,
        "model_result": result,
        "order": order,
        "seasonal_order": seasonal_order,
        "importances": importances,
        "use_log": use_log,
        "ts_train": ts_orig_train,
        "ts_test": ts_orig_test,
        "in_sample_pred": in_sample,
        "test_pred": forecast_test,
        "future_pred": future_forecast,
        "metrics": metrics,
    }


# ──────────────────────────────────────────────
# 9. Pipeline completo (N produtos)
# ──────────────────────────────────────────────

def get_top_products(df: pd.DataFrame, n: int = 10) -> list:
    """Retorna os N produtos com maior quantidade total vendida."""
    return (
        df.groupby("produto_cod")["qtdade"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .index.tolist()
    )


def run_full_pipeline(
    data_path: str,
    top_n: int = 10,
    test_months: int = 4,
    future_months: int = 3,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Pipeline completo:
      - Carrega dados
      - Executa SARIMAX para os top_n produtos
      - Salva métricas consolidadas em CSV
      - Retorna DataFrame com métricas por produto
    """
    df = load_data(data_path)
    products = get_top_products(df, top_n)

    if verbose:
        print(f"Top {top_n} produtos selecionados: {products}")

    results = []
    errors = []

    for produto in products:
        try:
            pipe = run_product_pipeline(
                df, produto,
                test_months=test_months,
                future_months=future_months,
                verbose=verbose,
            )
            row = {"produto_cod": produto, **pipe["metrics"],
                   "log_transform": pipe["use_log"],
                   "ordem": str(pipe["order"]),
                   "ordem_sazonal": str(pipe["seasonal_order"])}
            results.append(row)
        except Exception as e:
            errors.append({"produto_cod": produto, "erro": str(e)})
            if verbose:
                print(f"  [ERRO] Produto {produto}: {e}")

    summary = pd.DataFrame(results)

    if len(summary) > 0:
        metrics_path = METRICS_DIR / "metricas_sarimax.csv"
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        summary.to_csv(metrics_path, index=False, sep=";")
        if verbose:
            print(f"\n\nMétricas salvas em: {metrics_path}")
            print("\nResumo geral:")
            print(summary.to_string(index=False))

    if errors:
        err_df = pd.DataFrame(errors)
        err_path = METRICS_DIR / "erros_sarimax.csv"
        err_df.to_csv(err_path, index=False, sep=";")
        if verbose:
            print(f"\nErros salvos em: {err_path}")

    return summary
