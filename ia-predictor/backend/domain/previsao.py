"""Dominio da previsao semanal: series, exogenas, SARIMAX, backtest e metricas.

Logica pura (sem I/O, sem FastAPI/SQLAlchemy/APScheduler — Regra 1 da constituicao). A
orquestracao e a gravacao dos arquivos ficam em `backend/services/forecast_service.py`.

Series previstas, por loja, todas sobre o **fluxo diario** (vendas > 2.000 un. no documento
ficam fora — ADR-013):
  * `loja`      — venda total. E o que a tela da unidade mostra: nao e a soma das
    categorias, porque somar as faixas de 95% as deixa largas demais (experimento
    `disaggregation/categoria_direta_vs_desagregacao.py`, bottom-up);
  * `categoria` — SARIMAX direto em cada `unidade x categoria` (mesmo experimento: passa no
    criterio nas 8 series; a desagregacao, em 1 de 8);
  * `produto`   — SARIMAX direto nos produtos de venda regular: ADI < 1,32 em dias de loja
    aberta (Syntetos, Boylan & Croston, 2005) e >= 180 dias desde a 1a venda.

O modelo nao e guardado em pickle/joblib: guarda-se a especificacao e os parametros; com eles
e os dados, `reaplicar` reconstroi o mesmo modelo sem estimar nada.
"""
from __future__ import annotations

import itertools
import warnings
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #
NIVEL_LOJA, NIVEL_CATEGORIA, NIVEL_PRODUTO = "loja", "categoria", "produto"
CHAVE_LOJA = "total"

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CALENDARIO = ["loja_fechada", "abertura_excepcional"]
COLS_EXOG = [f"dia_{d}" for d in DIAS] + COLS_CALENDARIO

M = 7                      # sazonalidade semanal
GRID_PQ = range(0, 3)      # p, q em 0..2 (CLAUDE.md)
GRID_SPQ = range(0, 2)     # P, Q em 0..1
MAXITER = 200
ALPHA = 0.05               # IC de 95%

# Limiares da constituicao (Principio III / CLAUDE.md "Limiares de Qualidade")
MASE_LIMITE = 1.0
COBERTURA_MIN, COBERTURA_MAX = 90.0, 98.0
TRAINED, LOW_CONFIDENCE, INSUFFICIENT_DATA, ERROR = (
    "trained", "low_confidence", "insufficient_data", "error")


# --------------------------------------------------------------------------- #
# Exogenas de calendario
# --------------------------------------------------------------------------- #
class CalendarioIncompleto(ValueError):
    """O calendario da loja nao cobre todas as datas pedidas."""

    def __init__(self, unidade: str, faltando: pd.DatetimeIndex):
        self.unidade, self.faltando = unidade, faltando
        super().__init__(
            f"O calendário da loja {unidade} não cobre {len(faltando)} dia(s) "
            f"(de {faltando.min().date()} a {faltando.max().date()}). Atualize o calendário "
            f"(período da Etapa 10 do pré-processamento) antes de gerar a previsão.")


def _calendario_da_unidade(calendario: pd.DataFrame, unidade: str) -> pd.DataFrame:
    cal = calendario[calendario["unidade"] == unidade].copy()
    cal["data"] = pd.to_datetime(cal["data"])
    return cal.set_index("data").sort_index()


def matriz_exogenas(calendario: pd.DataFrame, unidade: str,
                    idx: pd.DatetimeIndex) -> pd.DataFrame:
    """6 dummies de dia da semana (domingo = base) + `loja_fechada` + `abertura_excepcional`."""
    cal = _calendario_da_unidade(calendario, unidade)
    faltando = idx.difference(cal.index)
    if len(faltando):
        raise CalendarioIncompleto(unidade, faltando)
    X = pd.DataFrame(index=idx)
    for i, nome in enumerate(DIAS):          # 0 = seg .. 5 = sab; domingo (6) e a base
        X[f"dia_{nome}"] = (idx.weekday == i).astype(float)
    X[COLS_CALENDARIO] = cal.loc[idx, COLS_CALENDARIO].astype(float).values
    return X[COLS_EXOG]


def dias_fechados(calendario: pd.DataFrame, unidade: str) -> set[pd.Timestamp]:
    cal = _calendario_da_unidade(calendario, unidade)
    return set(cal.index[cal["loja_fechada"] == 1])


# --------------------------------------------------------------------------- #
# Series
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Serie:
    unidade: str
    nivel: str
    chave: str          # "total" (loja), nome da categoria ou produto_cod
    nome: str

    @property
    def id(self) -> str:
        return f"{self.unidade}|{self.nivel}|{self.chave}"


def indice_diario(vendas: pd.DataFrame) -> pd.DatetimeIndex:
    """Calendario cheio da base: da 1a a ultima data com venda (qualquer loja)."""
    return pd.date_range(vendas["data"].min(), vendas["data"].max(), freq="D")


def series_da_unidade(vendas: pd.DataFrame, unidade: str, idx: pd.DatetimeIndex
                      ) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """(loja, categorias, produtos) do fluxo diario. Dia sem venda vira 0."""
    v = vendas[vendas["unidade"] == unidade]
    loja = v.groupby("data")["qtd_fluxo"].sum().reindex(idx, fill_value=0.0)
    cat = (v.groupby(["data", "categoria"])["qtd_fluxo"].sum().unstack(fill_value=0.0)
           .reindex(idx, fill_value=0.0))
    prod = (v.groupby(["data", "produto_cod"])["qtd_fluxo"].sum().unstack(fill_value=0.0)
            .reindex(idx, fill_value=0.0))
    return loja.rename("qtd"), cat.sort_index(axis=1), prod


def desde_primeira_venda(s: pd.Series, ate: pd.Timestamp) -> pd.Series:
    """Serie de um produto antes de `ate`, comecando na 1a venda dele."""
    s = s[s.index < ate]
    vendeu = s[s > 0]
    return s.iloc[0:0] if vendeu.empty else s[s.index >= vendeu.index.min()]


def produtos_regulares(produtos: pd.DataFrame, aberta: pd.Series, origem: pd.Timestamp,
                       adi_corte: float, min_span_dias: int) -> list[str]:
    """Produtos com ADI < `adi_corte` e span >= `min_span_dias`, so com dados < origem.

    ADI = dias de loja aberta da 1a venda ate a vespera da origem / dias com venda. O span
    vai ate a vespera (nao ate a ultima venda), para que um produto que parou de vender
    deixe de ser regular.
    """
    treino = produtos[produtos.index < origem]
    vendeu = treino > 0
    dias = vendeu.sum()
    tem = dias >= 2
    if not tem.any():
        return []
    primeira = vendeu.idxmax()[tem]
    span = ((origem - pd.Timedelta(days=1)) - primeira).dt.days + 1
    acum = aberta[aberta.index < origem].astype(int).cumsum()
    abertos = (acum.iloc[-1] - acum.reindex(primeira.values).values
               + aberta.reindex(primeira.values).astype(int).values)
    adi = pd.Series(abertos, index=primeira.index) / dias[tem]
    ok = (adi < adi_corte) & (span >= min_span_dias)
    return sorted(ok[ok].index)


# --------------------------------------------------------------------------- #
# SARIMAX: ajuste, ordem por AIC, previsao
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Especificacao:
    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    aic: float | None = None

    @property
    def tendencia(self) -> str:
        # Com d = 1 a diferenciacao ja remove o nivel: constante viraria tendencia linear.
        return "c" if self.order[1] == 0 else "n"

    def para_dict(self) -> dict:
        d = asdict(self)
        d["order"], d["seasonal_order"] = list(self.order), list(self.seasonal_order)
        return d

    @classmethod
    def de_dict(cls, d: dict) -> "Especificacao":
        return cls(tuple(d["order"]), tuple(d["seasonal_order"]), d.get("aic"))


def _modelo(y: pd.Series, X: pd.DataFrame, spec: Especificacao) -> SARIMAX:
    return SARIMAX(y, exog=X, order=spec.order, seasonal_order=spec.seasonal_order,
                   trend=spec.tendencia, enforce_stationarity=False,
                   enforce_invertibility=False)


def ajustar(y: pd.Series, X: pd.DataFrame, spec: Especificacao, maxiter: int = MAXITER):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _modelo(y, X, spec).fit(disp=False, maxiter=maxiter)


def reaplicar(y: pd.Series, X: pd.DataFrame, spec: Especificacao, params: dict):
    """Mesmo modelo com parametros ja estimados (sem nova estimacao)."""
    mod = _modelo(y, X, spec)
    vetor = np.array([params[n] for n in mod.param_names], dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return mod.smooth(vetor)


def parametros(res) -> dict[str, float]:
    return {str(k): float(v) for k, v in res.params.items()}


def selecionar_ordem(y: pd.Series, X: pd.DataFrame, d: int, m: int = M,
                     grid_pq=GRID_PQ, grid_spq=GRID_SPQ) -> Especificacao | None:
    """Melhor (p,d,q)(P,0,Q,m) por AIC; None se nenhuma ordem convergir. `d` e `D` ficam
    fora do grid: o AIC nao compara modelos com diferenciacao diferente."""
    melhor = None
    for p, q, P, Q in itertools.product(grid_pq, grid_pq, grid_spq, grid_spq):
        spec = Especificacao((p, d, q), (P, 0, Q, m))
        try:
            res = ajustar(y, X, spec)
        except Exception:  # noqa: BLE001 — ordem que nao converge fica de fora
            continue
        if np.isfinite(res.aic) and (melhor is None or res.aic < melhor.aic):
            melhor = Especificacao(spec.order, spec.seasonal_order, float(res.aic))
    return melhor


def prever(res, X_futuro: pd.DataFrame, alpha: float = ALPHA) -> pd.DataFrame:
    """Previsao pontual e IC 95% nas datas de `X_futuro`, truncados em 0 (venda >= 0)."""
    fc = res.get_forecast(len(X_futuro), exog=X_futuro)
    ic = np.asarray(fc.conf_int(alpha=alpha))
    return pd.DataFrame({
        "previsto": np.clip(np.asarray(fc.predicted_mean), 0, None),
        "ic_inf": np.clip(ic[:, 0], 0, None),
        "ic_sup": np.clip(ic[:, 1], 0, None),
    }, index=X_futuro.index)


# --------------------------------------------------------------------------- #
# Calendario das cargas e do backtest
# --------------------------------------------------------------------------- #
def proxima_data_de_carga(origem: pd.Timestamp, dia_semana_carga: int) -> pd.Timestamp:
    """Primeiro dia `dia_semana_carga` (0 = segunda) em ou depois de `origem`."""
    return origem + pd.Timedelta(days=(dia_semana_carga - origem.weekday()) % 7)


def origens_backtest(origem: pd.Timestamp, horizonte: int, n: int) -> list[pd.Timestamp]:
    """As `n` ultimas datas do mesmo dia da semana da origem com `horizonte` dias de
    realizado antes da origem (o + horizonte - 1 <= ultimo dia com dado)."""
    ultima = origem - pd.Timedelta(days=horizonte)
    ultima -= pd.Timedelta(days=(ultima.weekday() - origem.weekday()) % 7)
    return list(pd.date_range(end=ultima, periods=n, freq="7D"))


# --------------------------------------------------------------------------- #
# Metricas, residuos e status
# --------------------------------------------------------------------------- #
def naive_sazonal(treino: pd.Series, horizonte: int, m: int = M) -> np.ndarray:
    """Repete os ultimos `m` dias do treino em ciclo."""
    ult = treino.values[-m:]
    return np.array([ult[i % m] for i in range(horizonte)], dtype=float)


def escala_mase(treino: pd.Series, m: int = M) -> float:
    """Erro medio da naive sazonal DENTRO do treino (denominador do MASE)."""
    v = treino.values
    return float(np.mean(np.abs(v[m:] - v[:-m]))) if len(v) > m else float("nan")


def metricas(d: pd.DataFrame) -> dict | None:
    """`d`: uma linha por (origem, data) com real, previsto, ic_inf, ic_sup, naive, escala.

    Alem do MASE, o erro relativo a naive (razao das somas), as rodadas em que o modelo
    vence a naive, a cobertura e a largura do IC (CLAUDE.md, "Comparacao entre experimentos").
    """
    if d.empty:
        return None
    ae = (d["real"] - d["previsto"]).abs()
    ae_n = (d["real"] - d["naive"]).abs()
    ok = d["escala"] > 0
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    q = d.assign(ae=ae, ae_n=ae_n).groupby("origem")[["ae", "ae_n"]].sum()
    return {
        "n_dias": int(len(d)),
        "n_origens": int(len(q)),
        "venda_media_dia": round(float(d["real"].mean()), 2),
        "mae": round(float(ae.mean()), 2),
        "mase": round(float((ae[ok] / d.loc[ok, "escala"]).mean()), 3) if ok.any() else None,
        "erro_relativo_naive": round(float(ae.sum() / ae_n.sum()), 3) if ae_n.sum() else None,
        "vence_naive_pct": round(float((q["ae"] < q["ae_n"]).mean() * 100), 1),
        "cobertura_ic95_pct": round(float(dentro.mean() * 100), 1),
        "largura_ic95": round(float((d["ic_sup"] - d["ic_inf"]).mean()), 2),
        "previsto_sobre_real_pct": round(float(d["previsto"].sum() / d["real"].sum() * 100), 1)
        if d["real"].sum() else None,
    }


def status(m: dict | None) -> str:
    """MASE < 1 e cobertura do IC 95% em [90%, 98%] -> `trained`; senao `low_confidence`."""
    if not m or m["mase"] is None:
        return LOW_CONFIDENCE
    ok = m["mase"] < MASE_LIMITE and COBERTURA_MIN <= m["cobertura_ic95_pct"] <= COBERTURA_MAX
    return TRAINED if ok else LOW_CONFIDENCE


def diagnostico_residuos(res, m: int = M) -> dict:
    """Ljung-Box com 2m defasagens (Hyndman & Athanasopoulos, FPP3, §5.4: lag = 2m para
    series sazonais) e Shapiro-Wilk. So registro: nao bloqueiam o status (CLAUDE.md)."""
    r = np.asarray(res.resid)[res.loglikelihood_burn:]
    r = r[np.isfinite(r)]
    saida = {"ljung_box_p": None, "shapiro_p": None}
    if len(r) > 2 * m + 1:
        lb = acorr_ljungbox(r, lags=[2 * m], return_df=True)
        saida["ljung_box_p"] = round(float(lb["lb_pvalue"].iloc[0]), 4)
    if len(r) >= 3:
        saida["shapiro_p"] = round(float(stats.shapiro(r[-5000:]).pvalue), 4)
    return saida
