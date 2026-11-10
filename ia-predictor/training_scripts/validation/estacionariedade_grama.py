"""**Substituído por `estacionariedade_fiel_ao_modelo.py`** (doc 10 §3.1): este script testa o resíduo
só dos dias de loja aberta, emendados e sem `loja_fechada`, e não a série que o SARIMAX diferencia
(todos os dias, com as exógenas do modelo). Fica como registro da 1ª versão do doc 10.

Estacionariedade das séries de grama (categoria e produtos, por loja) — d = 0 ou d = 1?

O treino de produção usa d = 0 (ADR-017), apoiado no ADF das 12 séries da época. As variantes de
`variantes_nivel_sazonal.py` mostraram d = 1 errando menos na família Grama (categoria de Jardim Canadá
−9,5%, produtos −2,6%). Aqui o teste de raiz unitária é refeito nas séries que o sistema treina hoje.

Mesma série que o treino recebe (`servico_previsao._montar_series`: fluxo diário, sem encomendas grandes).
Cada série é testada em 3 formas, como em `disaggregation/estacionariedade_categoria_sku.py`:

  * `crua`     — a série diária no calendário cheio;
  * `sem_cal`  — só dias de loja aberta, sem o efeito do calendário (resíduo de OLS nas exógenas do
                 modelo: 6 dummies de dia da semana e abertura excepcional). É o que a parte ARMA vê;
  * `dif1`     — a 1ª diferença de `sem_cal`, para detectar sobrediferenciação.

ADF (H0: raiz unitária) e KPSS de nível (H0: estacionária), α = 5%:
  ADF rejeita e KPSS não → I(0), d = 0 basta; o contrário → I(1); os dois rejeitam → ambíguo (nível que anda
  devagar, em geral); nenhum → a amostra não decide.

Duas amostras: o histórico inteiro e a janela de 365 dias que o modelo usa. Na janela, o teste é repetido nos
52 cortes semanais de 01/03/2025 a 21/02/2026 (os mesmos das variantes) e conta-se em quantos cada teste rejeita.

Sobrediferenciação: autocorrelação de lag 1 da diferença < −0,5 ou variância que sobe ao diferenciar.
Deriva: amplitude da média móvel de 56 dias de loja aberta ÷ média.

Uso (a partir de `ia-predictor/`, com o banco de DATABASE_URL):
    python -m training_scripts.validation.estacionariedade_grama
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

from backend.domain.models.trainer import ConfigTreino, motivo_inelegivel

warnings.simplefilter("ignore", InterpolationWarning)
warnings.simplefilter("ignore", FutureWarning)

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(_RAIZ, "results", "metrics", "estacionariedade_grama")
ALPHA = 0.05
JANELA = 365
CORTES = pd.date_range("2025-03-01", "2026-02-21", freq="7D")


def _adf(x) -> float | None:
    try:
        return float(adfuller(np.asarray(x, float), regression="c", autolag="AIC")[1])
    except Exception:  # noqa: BLE001
        return None


def _kpss(x) -> float | None:
    try:
        return float(kpss(np.asarray(x, float), regression="c", nlags="auto")[1])
    except Exception:  # noqa: BLE001
        return None


def _veredito(pa, pk) -> str:
    if pa is None or pk is None:
        return "indeterminado"
    a, k = pa < ALPHA, pk < ALPHA
    return {(True, False): "I(0)", (False, True): "I(1)", (True, True): "ambíguo",
            (False, False): "não decide"}[(a, k)]


def _sem_calendario(y: pd.Series, X: pd.DataFrame, aberta: pd.Series) -> pd.Series:
    idx = y.index[aberta.reindex(y.index).fillna(False).astype(bool).values]
    cols = [c for c in X.columns if c != "loja_fechada" and X.loc[idx, c].std() > 0]
    A = np.column_stack([np.ones(len(idx)), X.loc[idx, cols].values.astype(float)])
    b, *_ = np.linalg.lstsq(A, y.loc[idx].values.astype(float), rcond=None)
    return pd.Series(y.loc[idx].values - A @ b, index=idx)


def _formas(y, X, aberta) -> dict[str, pd.Series]:
    r = _sem_calendario(y, X, aberta)
    return {"crua": y, "sem_cal": r, "dif1": r.diff().dropna()}


def analisar(s) -> dict:
    y = s.y.astype(float)
    y = y[y.index >= y[y > 0].index.min()]
    reg = {"serie": s.chave, "nome": s.rotulo, "nivel": s.nivel, "dias": len(y),
           "venda_dia": round(float(y[s.aberta.reindex(y.index).fillna(False).astype(bool)].mean()), 1),
           "zeros_aberta_pct": round(float((y[s.aberta.reindex(y.index).fillna(False).astype(bool)] == 0).mean() * 100), 1)}
    f = _formas(y, s.X, s.aberta)
    for nome, x in f.items():
        pa, pk = _adf(x), _kpss(x)
        reg |= {f"adf_p_{nome}": pa, f"kpss_p_{nome}": pk, f"veredito_{nome}": _veredito(pa, pk)}
    r, d1 = f["sem_cal"], f["dif1"]
    reg["acf1_dif1"] = round(float(d1.autocorr(1)), 3)
    reg["var_dif_sobre_var"] = round(float(d1.var() / r.var()), 2)
    ya = y[s.aberta.reindex(y.index).fillna(False).astype(bool)]
    mm = ya.rolling(56).mean().dropna()
    reg["deriva_56d"] = round(float((mm.max() - mm.min()) / ya.mean()), 2) if ya.mean() else None
    # janelas de 365 dias dos 52 cortes
    vered = []
    for c in CORTES:
        yc = y[(y.index <= c)].iloc[-JANELA:]
        if len(yc) < JANELA:
            continue
        rc = _sem_calendario(yc, s.X, s.aberta)
        vered.append(_veredito(_adf(rc), _kpss(rc)))
    v = pd.Series(vered, dtype=object)
    reg["janelas"] = len(v)
    for k in ("I(0)", "I(1)", "ambíguo", "não decide"):
        reg[f"jan_{k}"] = int((v == k).sum())
    return reg


def main() -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    series = carregar_series()
    grama = [s for s in series.values()
             if (s.nivel == "category" and s.category_id == "grama")
             or (s.nivel == "product" and not motivo_inelegivel(s.y, ConfigTreino(), s.nivel))]
    linhas = [analisar(s) for s in grama]
    df = pd.DataFrame(linhas).sort_values(["nivel", "venda_dia"], ascending=[True, False])
    os.makedirs(SAIDA, exist_ok=True)
    df.to_csv(os.path.join(SAIDA, "estacionariedade_grama.csv"), sep=";", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(df[["serie", "nome", "venda_dia", "zeros_aberta_pct", "deriva_56d"]].to_string(index=False))
    print()
    print(df[["serie", "adf_p_crua", "kpss_p_crua", "veredito_crua", "adf_p_sem_cal", "kpss_p_sem_cal",
              "veredito_sem_cal", "adf_p_dif1", "kpss_p_dif1", "veredito_dif1"]].round(4).to_string(index=False))
    print()
    print(df[["serie", "acf1_dif1", "var_dif_sobre_var", "janelas", "jan_I(0)", "jan_I(1)", "jan_ambíguo",
              "jan_não decide"]].to_string(index=False))


if __name__ == "__main__":
    main()
