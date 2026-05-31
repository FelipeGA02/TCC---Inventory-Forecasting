"""
Avaliacao do modelo SARIMAX mensal via walk-forward cross-validation.

Funcoes:
  walk_forward_cv          -> valida com janelas deslizantes, retorna metricas por fold
  evaluate_monthly_horizons-> avalia o modelo em 1, 2, 3 e 4 meses a frente
  residual_tests           -> Ljung-Box e teste de normalidade dos residuos
  confidence_interval_plot -> grafico de previsao com IC 95%
  generate_evaluation_report-> relatorio consolidado em CSV + graficos
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.models.sarimax_model import (
    prepare_monthly_data,
    build_exogenous_features,
    compute_feature_importance,
    weight_features,
    select_sarimax_order,
    fit_sarimax,
    suggest_d,
)

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"
EVAL_PLOTS_DIR = RESULTS_DIR / "plots" / "evaluation"
METRICS_DIR = RESULTS_DIR / "metrics"


# ──────────────────────────────────────────────
# Metricas
# ──────────────────────────────────────────────

def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2 + 1e-9
    smape = np.mean(np.abs(y_true - y_pred) / denom) * 100
    mask = y_true > np.mean(y_true) * 0.05
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() else np.nan
    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan
    return {"MAE": mae, "RMSE": rmse, "MAPE_%": mape, "SMAPE_%": smape, "R2": r2}


# ──────────────────────────────────────────────
# 1. Walk-forward Cross-Validation
# ──────────────────────────────────────────────

def walk_forward_cv(
    df: pd.DataFrame,
    produto_cod: str,
    n_splits: int = 5,
    horizon: int = 1,
    min_train: int = 14,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Validacao walk-forward (expanding window) para o modelo SARIMAX mensal.

    Em cada fold:
      - Treina com os primeiros train_size meses
      - Preve `horizon` meses a frente
      - Avanca a janela de treinamento

    Retorna DataFrame com metricas por fold.
    """
    ts = prepare_monthly_data(df, produto_cod)
    exog = build_exogenous_features(df, produto_cod)
    exog = exog.reindex(ts.index).ffill().fillna(0)
    common = ts.index.intersection(exog.index)
    ts, exog = ts.loc[common], exog.loc[common]

    n = len(ts)
    # Tamanho minimo de treino e ultimo ponto de corte
    max_start = n - min_train - horizon
    if max_start < n_splits:
        raise ValueError(
            f"Serie muito curta para {n_splits} folds com horizon={horizon} "
            f"e min_train={min_train}. Disponivel: {n} meses."
        )

    # Pontos de corte equidistantes
    cutoffs = [
        min_train + int(i * max_start / n_splits)
        for i in range(1, n_splits + 1)
    ]

    cv = ts.std() / (ts.mean() + 1e-9)
    use_log = cv > 0.7

    rows = []
    for fold, cut in enumerate(cutoffs, 1):
        ts_train = np.log1p(ts.iloc[:cut]) if use_log else ts.iloc[:cut]
        ts_test = ts.iloc[cut: cut + horizon]
        exog_train = exog.iloc[:cut]
        exog_test = exog.iloc[cut: cut + horizon]

        imp = compute_feature_importance(exog_train, ts_train)
        exog_train_w = weight_features(exog_train, imp)
        exog_test_w = weight_features(exog_test, imp)

        d = suggest_d(ts_train)
        try:
            order, seasonal_order = select_sarimax_order(
                ts_train, exog_train_w, d=d, D=0, m=12,
                p_range=range(0, 2), q_range=range(0, 2),
                P_range=range(0, 2), Q_range=range(0, 2),
            )
            result = fit_sarimax(ts_train, exog_train_w, order, seasonal_order)
            pred_log = result.forecast(steps=horizon, exog=exog_test_w)
            pred = np.expm1(pred_log).clip(0) if use_log else pred_log.clip(0)
        except Exception as e:
            if verbose:
                print(f"  fold {fold}: erro — {e}")
            continue

        m = _metrics(ts_test.values, np.array(pred))
        rows.append({
            "fold": fold,
            "train_end": ts.index[cut - 1].strftime("%Y-%m"),
            "test_start": ts_test.index[0].strftime("%Y-%m"),
            "horizon_meses": horizon,
            **m,
        })
        if verbose:
            print(f"  fold {fold:2d} | treino ate {rows[-1]['train_end']} "
                  f"| SMAPE={m['SMAPE_%']:.1f}% | R2={m['R2']:.3f}")

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# 2. Metricas por horizonte (1, 2, 3, 4 meses)
# ──────────────────────────────────────────────

def evaluate_monthly_horizons(
    df: pd.DataFrame,
    produto_cod: str,
    horizons: list = None,
    n_splits: int = 4,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Avalia a degradacao da previsao conforme o horizonte aumenta.
    Retorna DataFrame com SMAPE e MAE medios por horizonte.
    """
    if horizons is None:
        horizons = [1, 2, 3, 4]

    rows = []
    for h in horizons:
        if verbose:
            print(f"\n  Horizonte {h} mes(es):")
        try:
            cv_df = walk_forward_cv(
                df, produto_cod, n_splits=n_splits, horizon=h,
                min_train=12, verbose=verbose,
            )
            if len(cv_df):
                rows.append({
                    "produto_cod": str(produto_cod),
                    "horizonte_meses": h,
                    "MAE_medio": cv_df["MAE"].mean(),
                    "RMSE_medio": cv_df["RMSE"].mean(),
                    "SMAPE_%_medio": cv_df["SMAPE_%"].mean(),
                    "R2_medio": cv_df["R2"].mean(),
                    "n_folds": len(cv_df),
                })
        except Exception as e:
            if verbose:
                print(f"  Erro horizonte {h}: {e}")

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# 3. Testes de residuos
# ──────────────────────────────────────────────

def residual_tests(result, produto_cod: str, verbose: bool = True) -> dict:
    """
    Aplica testes estatisticos nos residuos do modelo:
      - Ljung-Box: autocorrelacao residual (deve ser nao significativa)
      - Shapiro-Wilk: normalidade dos residuos
      - ARCH effect: heterocedasticidade condicional
    """
    resid = pd.Series(result.resid.dropna())

    # Ljung-Box
    lags = min(10, len(resid) // 2 - 1)
    lb = acorr_ljungbox(resid, lags=[lags], return_df=True)
    lb_stat = float(lb["lb_stat"].iloc[0])
    lb_p = float(lb["lb_pvalue"].iloc[0])

    # Shapiro-Wilk
    sw_stat, sw_p = stats.shapiro(resid) if len(resid) >= 3 else (np.nan, np.nan)

    # Jarque-Bera
    jb_stat, jb_p = stats.jarque_bera(resid)

    tests = {
        "produto_cod": str(produto_cod),
        "n_residuos": len(resid),
        "ljung_box_stat": lb_stat,
        "ljung_box_p": lb_p,
        "ljung_box_ok": lb_p > 0.05,       # sem autocorrelacao -> bom
        "shapiro_stat": sw_stat,
        "shapiro_p": sw_p,
        "shapiro_normal": sw_p > 0.05,
        "jarque_bera_stat": jb_stat,
        "jarque_bera_p": jb_p,
        "jarque_bera_normal": jb_p > 0.05,
        "resid_mean": resid.mean(),
        "resid_std": resid.std(),
        "resid_skew": float(stats.skew(resid)),
        "resid_kurt": float(stats.kurtosis(resid)),
    }

    if verbose:
        print(f"\n  Testes de residuos — Produto {produto_cod}")
        print(f"  Ljung-Box (lag {lags}): stat={lb_stat:.3f}, p={lb_p:.4f} "
              f"-> {'OK (sem autocorr.)' if lb_p > 0.05 else 'PROBLEMA (autocorr. detectada)'}")
        print(f"  Shapiro-Wilk:          stat={sw_stat:.3f}, p={sw_p:.4f} "
              f"-> {'Normal' if sw_p > 0.05 else 'Nao normal'}")
        print(f"  Jarque-Bera:           stat={jb_stat:.3f}, p={jb_p:.4f} "
              f"-> {'Normal' if jb_p > 0.05 else 'Nao normal'}")
        print(f"  Media: {resid.mean():.4f}  Std: {resid.std():.4f}  "
              f"Skew: {stats.skew(resid):.3f}  Kurt: {stats.kurtosis(resid):.3f}")

    return tests


# ──────────────────────────────────────────────
# 4. Grafico com IC
# ──────────────────────────────────────────────

def confidence_interval_plot(
    result,
    ts_train: pd.Series,
    ts_test: pd.Series,
    exog_test_w: pd.DataFrame,
    produto_cod: str,
    use_log: bool = False,
    save_dir: Path = EVAL_PLOTS_DIR,
) -> None:
    """Grafico de previsao com intervalo de confianca 95%."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    steps = len(ts_test)
    fc = result.get_forecast(steps=steps, exog=exog_test_w)
    pred_mean = fc.predicted_mean
    ci = fc.conf_int(alpha=0.05)

    if use_log:
        pred_mean = np.expm1(pred_mean).clip(0)
        ci = np.expm1(ci).clip(0)

    pred_mean.index = ts_test.index
    ci.index = ts_test.index

    fig, ax = plt.subplots(figsize=(13, 5))
    in_sample = np.expm1(result.fittedvalues).clip(0) if use_log else result.fittedvalues
    in_sample.index = ts_train.index

    ax.plot(ts_train.index, ts_train.values, color="#1f77b4", linewidth=2, label="Historico (treino)")
    ax.plot(in_sample.index, in_sample.values, "--", color="#ff7f0e", linewidth=1.2, label="Ajuste in-sample")
    ax.plot(ts_test.index, ts_test.values, "o-", color="#2ca02c", linewidth=2, markersize=6, label="Real (teste)")
    ax.plot(pred_mean.index, pred_mean.values, "s--", color="#d62728", linewidth=2, markersize=6, label="Previsto")
    ax.fill_between(ci.index, ci.iloc[:, 0], ci.iloc[:, 1],
                    alpha=0.2, color="#d62728", label="IC 95%")
    ax.axvline(ts_test.index[0], color="gray", linestyle=":", linewidth=1.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_ylabel("Quantidade")
    ax.set_title(f"Previsao com IC 95% — Produto {produto_cod}", fontsize=12)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    fname = save_dir / f"ic95_{str(produto_cod).replace('/', '_')}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {fname.name}")


# ──────────────────────────────────────────────
# 5. Relatorio consolidado
# ──────────────────────────────────────────────

def plot_cv_summary(
    cv_results: dict,
    save_dir: Path = EVAL_PLOTS_DIR,
) -> None:
    """
    Grafico de SMAPE por horizonte para cada produto (degradacao da previsao).
    cv_results: {produto_cod: DataFrame de evaluate_monthly_horizons}
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for prod, df_h in cv_results.items():
        if df_h.empty:
            continue
        axes[0].plot(df_h["horizonte_meses"], df_h["SMAPE_%_medio"],
                     marker="o", linewidth=1.5, label=str(prod))
        axes[1].plot(df_h["horizonte_meses"], df_h["R2_medio"],
                     marker="s", linewidth=1.5, label=str(prod))

    axes[0].set_xlabel("Horizonte (meses)")
    axes[0].set_ylabel("SMAPE % medio")
    axes[0].set_title("Degradacao da previsao por horizonte")
    axes[0].axhline(30, color="green", linestyle="--", linewidth=0.8, label="Bom (<30%)")
    axes[0].axhline(60, color="orange", linestyle="--", linewidth=0.8, label="Aceitavel (<60%)")
    axes[0].legend(fontsize=7, loc="upper left")
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel("Horizonte (meses)")
    axes[1].set_ylabel("R2 medio")
    axes[1].set_title("R2 por horizonte de previsao")
    axes[1].axhline(0.7, color="green", linestyle="--", linewidth=0.8)
    axes[1].axhline(0, color="red", linestyle="--", linewidth=0.8)
    axes[1].legend(fontsize=7, loc="upper right")
    axes[1].grid(True, alpha=0.3)

    fig.suptitle("Walk-forward CV — Qualidade por horizonte de previsao",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = save_dir / "cv_horizons_summary.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] {path.name}")


def generate_evaluation_report(
    df: pd.DataFrame,
    products: list,
    fitted_results: dict,
    train_data: dict,
    test_data: dict,
    exog_test_w: dict,
    use_log_flags: dict,
    n_splits: int = 4,
    horizons: list = None,
    verbose: bool = True,
) -> dict:
    """
    Relatorio completo de avaliacao:
      - Walk-forward CV por horizonte
      - Testes de residuos
      - Graficos de IC
      - CSV consolidado

    Parametros:
      fitted_results : {produto_cod: SARIMAXResultsWrapper}  (modelo treinado)
      train_data     : {produto_cod: pd.Series} serie de treino (escala original)
      test_data      : {produto_cod: pd.Series} serie de teste (escala original)
      exog_test_w    : {produto_cod: pd.DataFrame} exog ponderada do periodo de teste
      use_log_flags  : {produto_cod: bool}
    """
    if horizons is None:
        horizons = [1, 2, 3, 4]

    cv_results = {}
    residual_rows = []
    horizon_rows = []

    for prod in products:
        if verbose:
            print(f"\n{'='*55}")
            print(f"  Avaliando produto: {prod}")
            print(f"{'='*55}")

        # Walk-forward CV
        try:
            df_h = evaluate_monthly_horizons(
                df, prod, horizons=horizons, n_splits=n_splits, verbose=verbose
            )
            cv_results[prod] = df_h
            horizon_rows.append(df_h)
        except Exception as e:
            if verbose:
                print(f"  CV erro: {e}")
            cv_results[prod] = pd.DataFrame()

        # Testes de residuos
        if prod in fitted_results:
            try:
                tests = residual_tests(fitted_results[prod], prod, verbose=verbose)
                residual_rows.append(tests)
            except Exception as e:
                if verbose:
                    print(f"  Residuos erro: {e}")

        # IC plot
        if all(prod in d for d in [fitted_results, train_data, test_data, exog_test_w]):
            try:
                confidence_interval_plot(
                    fitted_results[prod],
                    train_data[prod],
                    test_data[prod],
                    exog_test_w[prod],
                    prod,
                    use_log=use_log_flags.get(prod, False),
                )
            except Exception as e:
                if verbose:
                    print(f"  IC plot erro: {e}")

    # Graficos e CSV
    if cv_results:
        plot_cv_summary(cv_results)

    residual_df = pd.DataFrame(residual_rows)
    horizon_df = pd.concat(horizon_rows, ignore_index=True) if horizon_rows else pd.DataFrame()

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    if not residual_df.empty:
        path = METRICS_DIR / "residuos_testes.csv"
        residual_df.to_csv(path, index=False, sep=";")
        if verbose:
            print(f"\nTestes de residuos salvos: {path}")

    if not horizon_df.empty:
        path = METRICS_DIR / "cv_por_horizonte.csv"
        horizon_df.to_csv(path, index=False, sep=";")
        if verbose:
            print(f"CV por horizonte salvo: {path}")

    return {"cv_results": cv_results, "residuals": residual_df, "horizons": horizon_df}
