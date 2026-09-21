"""EDA 3 — Granularidade das categorias na desagregação.

Pergunta: a desagregação de cada unidade deve usar 3 categorias
(Grama · Flores de corte · Produtos de jardim) ou abrir "Produtos de jardim" em
"Plantas diversas" e "Insumos e acessórios" (4 categorias)? Este teste roda antes da
decisão de granularidade do L1 (`eda_separacao.py`, ADR-011 §4) — na época, "Produtos de
jardim" ainda era candidata a série L1 própria; a conclusão (não abrir) vale igual agora
que ela mesma é obtida por desagregação da unidade, pois a pergunta é a mesma: abrir mais
um nível ajuda, independente de onde a previsão do nível de cima vem?

  * "Flores de corte"     = as que compõem arranjos e buquês (e os próprios arranjos).
  * "Plantas diversas"    = todas as plantas, exceto flores de corte e árvores
                            (muda, planta em vaso, arbusto, hortaliça e erva).
  * "Insumos e acessórios" = o que resta de "Produtos de jardim" sem as plantas
                            (substrato, adubo, vasos, seixos, ferramentas).

Um grupo só merece um modelo L1 próprio se (i) a série dele sustenta um SARIMAX
(densa, ≥ 180 dias com venda) e (ii) modelá-lo direto erra menos do que obter os números
dele repartindo a previsão do grupo maior pela participação móvel — que é o que a
desagregação L2 já entrega sem custo de modelo adicional.

Blocos:
  1. Viabilidade de cada série candidata (densidade, escala, CV)
  2. O quanto os grupos se comportam de forma diferente (perfil semanal e mensal,
     datas comemorativas, correlação dos resíduos)
  3. Teste de previsão: modelo direto por grupo × repartição da previsão do grupo maior
     (walk-forward, origem móvel, 26 folds, h = 14 dias, dois previsores)
  4. Árvores: viabilidade como categoria própria

Saídas: PNGs em results/plots/eda/ e results/metrics/eda_grupos.json
"""
from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd

from ..preprocessing.taxonomy.categorias import GRUPO_PRODUTO
from . import _common as C
from .eda_series import (
    MIN_OBSERVATIONS_DAYS, _densidade, _distribuicao, _efeito_datas,
    _forca_sazonal_semanal, _perfil_dow, _perfil_mensal, _tendencia,
)

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------- #
# Grupos candidatos (sobre `categoria_fina`, via GRUPO_PRODUTO da taxonomia)
# --------------------------------------------------------------------------- #
GRUPOS = {g: [f for f, gg in GRUPO_PRODUTO.items() if gg == g]
          for g in ("Grama", "Flores de corte", "Plantas diversas", "Insumos e acessórios")}
FIN_PLANTAS = GRUPOS["Plantas diversas"]
FIN_INSUMOS = GRUPOS["Insumos e acessórios"]
PAI = "Produtos de jardim"                      # = Plantas diversas + Insumos e acessórios
FILHOS = ["Plantas diversas", "Insumos e acessórios"]

# Árvores: estimativa por palavra-chave no início do nome (a lista do ERP não está
# disponível). Serve de teto para medir se árvores sustentam uma categoria própria.
ARVORE_RX = re.compile(
    r"^\s*(ARVORES?|IPE|OLIVEIRA|PAINEIRA|SIBIPIRUNA|JACARANDA|EUCALIPTO|LARANJA|LIMAO|"
    r"MEXERICA|GOIABA|MANGA|JABUTICABA|ACEROLA|PITANGA|AMORA|ABACATE|CAJU|CARAMBOLA|"
    r"FRUTIFERAS?|PALMEIRA|CIPRESTE|ESCUMILHA)\b", re.I)

# Teste de previsão
N_FOLDS = 26                # ≥ 4 (CLAUDE.md) — 26 janelas de 14 dias = 1 ano, com todas as datas comemorativas
HORIZONTE = 14
GANHO_MINIMO = 0.05         # ganho relativo de MASE abaixo disso é ruído de amostra
PERDA_MAXIMA_TOTAL = 0.02   # soma dos filhos pode piorar o pai em até 2%
LIMITE_INTERMITENCIA = 12   # % de dias úteis zerados (mesmo limite do veredito de eda_series)

DIAS_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# --------------------------------------------------------------------------- #
# Séries
# --------------------------------------------------------------------------- #
def _span_unidade(df: pd.DataFrame, unidade: str) -> pd.DatetimeIndex:
    d = df[(df["unidade"] == unidade) & (df["categoria"] != C.NAO_PRODUTO)].dropna(subset=["data"])
    return pd.date_range(d["data"].min().normalize(), d["data"].max().normalize(), freq="D")


def _serie(df: pd.DataFrame, unidade: str, fins: list[str], idx: pd.DatetimeIndex) -> pd.Series:
    d = df[(df["unidade"] == unidade) & df["categoria_fina"].isin(fins)].dropna(subset=["data"])
    s = d.groupby(d["data"].dt.normalize())["qtdade_n"].sum()
    return s.reindex(idx, fill_value=0.0)


def _series_da_unidade(df: pd.DataFrame, unidade: str) -> dict[str, pd.Series]:
    idx = _span_unidade(df, unidade)
    out = {g: _serie(df, unidade, fins, idx) for g, fins in GRUPOS.items()}
    out[PAI] = out["Plantas diversas"] + out["Insumos e acessórios"]
    return out


def _com_nomes(df: pd.DataFrame) -> pd.DataFrame:
    con = C._read_csv_resiliente(C.CONSOLIDATED_CSV, usecols=["produto_cod", "produto_nome"])
    nome = con.dropna(subset=["produto_cod"]).drop_duplicates("produto_cod")
    nome = dict(zip(nome["produto_cod"], nome["produto_nome"]))
    return df.assign(produto_nome=df["produto_cod"].map(nome))


# --------------------------------------------------------------------------- #
# Bloco 1 — viabilidade
# --------------------------------------------------------------------------- #
def _viabilidade(s: pd.Series, df_par: pd.DataFrame, volume_unidade: float) -> dict:
    dens = _densidade(s, df_par)
    dist = _distribuicao(s)
    return {
        "volume_total": float(s.sum()),
        "share_volume_unidade_pct": round(float(s.sum() / volume_unidade * 100), 2),
        "media_diaria": dist["media"],
        "dias_com_venda": dens["dias_com_venda"],
        "pct_dias_com_venda": dens["pct_dias_com_venda"],
        "pct_dias_zero_excl_domingo": dist["pct_dias_zero_excl_domingo"],
        "maior_sequencia_zeros": dens["maior_sequencia_zeros"],
        "cv": dist["cv"],
        "razao_max_media": dist["razao_max_media"],
        "skus_distintos": dens["skus_distintos"],
        "viavel_l1": bool(dens["dias_com_venda"] >= MIN_OBSERVATIONS_DAYS
                          and dist["pct_dias_zero_excl_domingo"] <= LIMITE_INTERMITENCIA),
    }


def bloco_viabilidade(df: pd.DataFrame, series: dict) -> dict:
    out = {}
    for u, ss in series.items():
        vol_u = float(sum(ss[g].sum() for g in GRUPOS))
        out[u] = {}
        for g in [*GRUPOS, PAI]:
            fins = GRUPOS[g] if g in GRUPOS else FIN_PLANTAS + FIN_INSUMOS
            d = df[(df["unidade"] == u) & df["categoria_fina"].isin(fins)]
            out[u][g] = _viabilidade(ss[g], d, vol_u)
    return out


# --------------------------------------------------------------------------- #
# Bloco 2 — o quanto os grupos diferem
# --------------------------------------------------------------------------- #
def _residuo_semanal(s: pd.Series, aberto: pd.Series) -> pd.Series:
    """log1p da série sem a média do dia da semana, só em dias com a loja aberta (seg–sáb
    com venda em algum grupo) — dias de fechamento zeram todos os grupos juntos e
    inflariam a correlação."""
    x = np.log1p(s.clip(lower=0))
    x = x[aberto & (x.index.weekday < 6)]
    return x - x.groupby(x.index.weekday).transform("mean")


def _corr(a: pd.Series, b: pd.Series) -> float:
    return float(pd.concat([a, b], axis=1).dropna().corr().iloc[0, 1])


def bloco_diferencas(series: dict) -> dict:
    out = {}
    nomes = list(GRUPOS)
    for u, ss in series.items():
        aberto = sum(ss[g].clip(lower=0) for g in nomes) > 0
        res = {g: _residuo_semanal(ss[g], aberto) for g in nomes}
        sem = {g: np.log1p(ss[g].clip(lower=0).resample("W").sum()) for g in nomes}
        perfis = {g: _perfil_dow(ss[g]) for g in nomes}
        mensal = {g: _perfil_mensal(ss[g]) for g in nomes}
        datas = {g: _efeito_datas(ss[g]) for g in nomes}
        forca = {g: _forca_sazonal_semanal(ss[g]) for g in nomes}
        tend = {g: _tendencia(ss[g]) for g in nomes}

        def vec(d: dict, ks) -> np.ndarray:
            return np.array([d[k] if d.get(k) is not None else np.nan for k in ks], dtype=float)

        idx_dow = {g: vec(perfis[g]["indice_dia_semana"], DIAS_PT[:6]) for g in nomes}
        idx_mes = {g: vec(mensal[g]["indice_mes"], range(1, 13)) for g in nomes}

        def corr_vec(a, b) -> float | None:
            ok = ~(np.isnan(a) | np.isnan(b))
            return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 2 else None

        pares = {}
        for i, a in enumerate(nomes):
            for b in nomes[i + 1:]:
                pares[f"{a} × {b}"] = {
                    "corr_residuo_diario": _corr(res[a], res[b]),
                    "corr_total_semanal": _corr(sem[a], sem[b]),
                    "corr_perfil_dia_semana": corr_vec(idx_dow[a], idx_dow[b]),
                    "corr_perfil_mensal": corr_vec(idx_mes[a], idx_mes[b]),
                }
        out[u] = {
            "por_grupo": {
                g: {
                    "indice_dia_semana": perfis[g]["indice_dia_semana"],
                    "dia_pico": perfis[g]["dia_pico"],
                    "forca_sazonal_semanal": forca[g]["forca_sazonal_semanal"],
                    "tendencia_pct_ano": tend[g]["inclinacao_pct_da_media_por_ano"],
                    "mes_pico": mensal[g]["mes_pico"],
                    "datas_razao_vs_media": {k: v["razao_vs_media_geral"] for k, v in datas[g].items()},
                } for g in nomes
            },
            "pares": pares,
            "matriz_corr_residuo": pd.DataFrame(
                {a: {b: (1.0 if a == b else _corr(res[a], res[b])) for b in nomes} for a in nomes}
            ).round(3).to_dict(),
        }
    return out


# --------------------------------------------------------------------------- #
# Bloco 3 — teste de previsão
# --------------------------------------------------------------------------- #
def _exog_calendario(idx: pd.DatetimeIndex) -> pd.DataFrame:
    anos = range(idx.year.min(), idx.year.max() + 2)
    datas = pd.DatetimeIndex(C.datas_comemorativas(anos)["data"]).normalize()
    janela = datas.union(datas - pd.Timedelta(days=1)).union(datas - pd.Timedelta(days=2))
    x = pd.DataFrame(index=idx)
    for i, nome in enumerate(DIAS_PT[:6]):
        x[nome] = (idx.weekday == i).astype(float)
    x["feriado"] = idx.isin(C.feriados_fixos(anos).union(C.feriados_moveis(anos))).astype(float)
    x["janela_data"] = idx.isin(janela).astype(float)
    return x


def _volta_escala(mu: np.ndarray, resid: pd.Series, futuro: pd.DatetimeIndex) -> np.ndarray:
    """Volta de log1p para a escala original com o fator de Duan (smearing) calculado nos
    resíduos de dias abertos, para a soma de previsões de grupos ser comparável à do total.
    Domingos (loja fechada) só levam expm1."""
    resid = resid.iloc[14:]
    resid = resid[resid.index.weekday < 6]
    smear = float(np.mean(np.exp(resid)))
    aberto = futuro.weekday < 6
    return np.clip(np.where(aberto, np.exp(mu) * smear - 1.0, np.expm1(mu)), 0.0, None)


def _prever_ets(y: pd.Series, futuro: pd.DatetimeIndex) -> np.ndarray:
    """Holt-Winters aditivo (nível + sazonalidade semanal, sem exógenas) em log1p — família
    de modelo diferente do SARIMAX, para conferir se a conclusão depende do previsor."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    yl = np.log1p(y.clip(lower=0))
    res = ExponentialSmoothing(yl, trend=None, seasonal="add", seasonal_periods=7,
                               initialization_method="estimated").fit()
    return _volta_escala(np.asarray(res.forecast(len(futuro))), res.resid, futuro)


_AJUSTES = {"sarimax": 0, "sem_convergencia": 0}


def _prever_sarimax(y: pd.Series, futuro: pd.DatetimeIndex, x_all: pd.DataFrame) -> np.ndarray:
    """SARIMAX(1,0,1) + exógenas de calendário (dia da semana, feriado, janela de data
    comemorativa) em log1p."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    yl = np.log1p(y.clip(lower=0))
    res = SARIMAX(yl, exog=x_all.loc[y.index], order=(1, 0, 1), trend="c",
                  enforce_stationarity=False, enforce_invertibility=False
                  ).fit(disp=False, maxiter=100)
    _AJUSTES["sarimax"] += 1
    _AJUSTES["sem_convergencia"] += int(not res.mle_retvals.get("converged", True))
    mu = np.asarray(res.get_forecast(steps=len(futuro), exog=x_all.loc[futuro]).predicted_mean)
    return _volta_escala(mu, res.resid, futuro)


def _erros(y_true: np.ndarray, y_hat: np.ndarray, treino: pd.Series) -> dict:
    escala = float(np.mean(np.abs(treino.values[7:] - treino.values[:-7])))
    e = np.abs(y_true - y_hat)
    soma = float(y_true.sum())
    return {
        "mae": float(e.mean()),
        "mase": float(e.mean() / escala) if escala > 0 else np.nan,
        "abs_erro": float(e.sum()),
        "soma_real": soma,
        "erro_acumulado_pct": float((y_hat.sum() - soma) / soma * 100) if soma > 0 else np.nan,
    }


def _participacoes(treino_pai: pd.Series, treino_filho: pd.Series, futuro: pd.DatetimeIndex,
                   semanas: int = 8) -> tuple[float, np.ndarray]:
    """Participação do filho no pai: nível (últimos `semanas`) e por dia da semana."""
    n = 7 * semanas
    p, f = treino_pai.iloc[-n:], treino_filho.iloc[-n:]
    nivel = float(f.sum() / p.sum()) if p.sum() > 0 else 0.0
    por_dow = {}
    for d in range(7):
        pd_, fd = p[p.index.weekday == d].sum(), f[f.index.weekday == d].sum()
        por_dow[d] = float(fd / pd_) if pd_ > 0 else nivel
    return nivel, np.array([por_dow[d.weekday()] for d in futuro])


def _agrega(erros_por_fold: list[dict]) -> dict:
    ab = sum(e["abs_erro"] for e in erros_por_fold)
    sr = sum(e["soma_real"] for e in erros_por_fold)
    return {
        "mase": float(np.nanmean([e["mase"] for e in erros_por_fold])),
        "wape_pct": float(ab / sr * 100) if sr > 0 else np.nan,
        "abs_erro_acumulado_14d_pct": float(np.nanmean(
            [abs(e["erro_acumulado_pct"]) for e in erros_por_fold])),
    }


def teste_previsao(ss: dict[str, pd.Series], previsor: str) -> dict:
    """Uma unidade × um previsor. Compara, para Plantas diversas, Insumos e acessórios e
    o pai (Produtos de jardim), o modelo direto contra a repartição / soma dos filhos."""
    idx = ss[PAI].index
    n = len(idx)
    x_all = _exog_calendario(pd.date_range(idx[0], idx[-1] + pd.Timedelta(days=HORIZONTE), freq="D"))
    prever = (lambda y, fut: _prever_sarimax(y, fut, x_all)) if previsor == "sarimax" \
        else (lambda y, fut: _prever_ets(y, fut))

    acc = {"direto": {g: [] for g in [PAI, *FILHOS]},
           "reparticao_nivel": {g: [] for g in FILHOS},
           "reparticao_dow": {g: [] for g in FILHOS},
           "soma_dos_filhos": {PAI: []}}
    for i in range(N_FOLDS):
        ini = n - (N_FOLDS - i) * HORIZONTE
        fut = idx[ini:ini + HORIZONTE]
        tr = {g: ss[g].iloc[:ini] for g in [PAI, *FILHOS]}
        real = {g: ss[g].iloc[ini:ini + HORIZONTE].clip(lower=0).values for g in [PAI, *FILHOS]}
        f = {g: prever(tr[g], fut) for g in [PAI, *FILHOS]}
        for g in [PAI, *FILHOS]:
            acc["direto"][g].append(_erros(real[g], f[g], tr[g]))
        for g in FILHOS:
            nivel, dow = _participacoes(tr[PAI], tr[g], fut)
            acc["reparticao_nivel"][g].append(_erros(real[g], f[PAI] * nivel, tr[g]))
            acc["reparticao_dow"][g].append(_erros(real[g], f[PAI] * dow, tr[g]))
        soma = sum(f[g] for g in FILHOS)
        acc["soma_dos_filhos"][PAI].append(_erros(real[PAI], soma, tr[PAI]))

    return {sistema: {g: _agrega(lst) for g, lst in por_g.items()}
            for sistema, por_g in acc.items()}


def _veredito(viab: dict, testes: dict) -> dict:
    """Regra fixada antes de olhar os números: abrir em 4 categorias só se (a) todas as
    séries candidatas forem viáveis em todas as unidades, (b) o modelo direto ganhar pelo
    menos GANHO_MINIMO de MASE da melhor repartição em cada filho e unidade, e (c) a soma
    dos filhos não piorar o pai em mais de PERDA_MAXIMA_TOTAL."""
    viavel = all(viab[u][g]["viavel_l1"] for u in viab for g in FILHOS)
    ganhos, perdas_total = [], []
    detalhe = {}
    for (u, previsor), t in testes.items():
        for g in FILHOS:
            rep = min(t["reparticao_nivel"][g]["mase"], t["reparticao_dow"][g]["mase"])
            ganho = 1 - t["direto"][g]["mase"] / rep
            ganhos.append(ganho)
            detalhe[f"{u} · {previsor} · {g}"] = round(float(ganho) * 100, 1)
        perda = t["soma_dos_filhos"][PAI]["mase"] / t["direto"][PAI]["mase"] - 1
        perdas_total.append(perda)
        detalhe[f"{u} · {previsor} · soma dos filhos vs pai"] = round(float(perda) * 100, 1)
    abrir = bool(viavel and min(ganhos) >= GANHO_MINIMO and max(perdas_total) <= PERDA_MAXIMA_TOTAL)
    return {
        "regra": (f"abrir em 4 categorias se séries viáveis (≥ {MIN_OBSERVATIONS_DAYS} dias e "
                  f"≤ {LIMITE_INTERMITENCIA}% de dias úteis zerados) E modelo direto ganha "
                  f"≥ {GANHO_MINIMO:.0%} de MASE da melhor repartição em cada filho/unidade/previsor "
                  f"E soma dos filhos não piora o pai em mais de {PERDA_MAXIMA_TOTAL:.0%}"),
        "series_viaveis": bool(viavel),
        "ganho_mase_direto_vs_reparticao_pct": detalhe,
        "menor_ganho_pct": round(float(min(ganhos)) * 100, 1),
        "mediana_ganho_pct": round(float(np.median(ganhos)) * 100, 1),
        "abrir_em_4_categorias": abrir,
        "conclusao": ("abrir Produtos de jardim em Plantas diversas e Insumos e acessórios"
                      if abrir else
                      "manter 3 categorias no L1; Plantas diversas e Insumos e acessórios saem "
                      "da desagregação (categoria_fina)"),
    }


# --------------------------------------------------------------------------- #
# Bloco 4 — árvores
# --------------------------------------------------------------------------- #
def bloco_arvores(df: pd.DataFrame, series: dict) -> dict:
    d = _com_nomes(df)
    eh_arvore = d["categoria_fina"].isin(FIN_PLANTAS) & \
        d["produto_nome"].fillna("").str.contains(ARVORE_RX)
    arv = d[eh_arvore]
    top = (arv.groupby(["produto_cod", "produto_nome"])["qtdade_n"].sum()
              .sort_values(ascending=False).head(10))
    out = {"skus_estimados": int(arv["produto_cod"].nunique()),
           "top10_skus": {f"{c} · {n}": float(v) for (c, n), v in top.items()},
           "nota": "estimativa por palavra-chave no início do nome; lista oficial do ERP indisponível"}
    for u, ss in series.items():
        idx = ss[PAI].index
        s = _serie(d.assign(categoria_fina=np.where(eh_arvore, "__arvore__", d["categoria_fina"])),
                   u, ["__arvore__"], idx)
        dv = _viabilidade(s, arv[arv["unidade"] == u], float(sum(ss[g].sum() for g in GRUPOS)))
        dv["share_de_plantas_diversas_pct"] = round(float(s.sum() / ss["Plantas diversas"].sum() * 100), 2)
        out[u] = dv
    return out


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
CORES_GRUPOS = {"Grama": "#2E7D32", "Flores de corte": "#C2185B",
                "Plantas diversas": "#F9A825", "Insumos e acessórios": "#5D4037"}


def graficos(series: dict, diferencas: dict, testes: dict, plt) -> list[str]:
    figs = []
    unidades = list(series)

    # 1. Perfil de dia da semana dos 4 grupos, por unidade
    fig, axes = plt.subplots(1, len(unidades), figsize=(6 * len(unidades), 4), sharey=True)
    for ax, u in zip(np.atleast_1d(axes), unidades):
        for g in GRUPOS:
            idx = diferencas[u]["por_grupo"][g]["indice_dia_semana"]
            ax.plot(DIAS_PT, [idx[d] for d in DIAS_PT], marker="o", lw=1.2, label=g,
                    color=CORES_GRUPOS[g])
        ax.axhline(1, color="#999", lw=.8, ls=":")
        ax.set_title(u)
    np.atleast_1d(axes)[0].set_ylabel("demanda relativa (1.0 = média do grupo)")
    np.atleast_1d(axes)[-1].legend(frameon=False, fontsize=8)
    fig.suptitle("Índice de demanda por dia da semana — grupos candidatos do L1")
    fig.tight_layout()
    figs.append(C.savefig(fig, "20_grupos_perfil_dia_semana.png"))

    # 2. Correlação dos resíduos (sem perfil semanal) entre os grupos
    fig, axes = plt.subplots(1, len(unidades), figsize=(5.2 * len(unidades), 4.4))
    nomes = list(GRUPOS)
    for ax, u in zip(np.atleast_1d(axes), unidades):
        m = pd.DataFrame(diferencas[u]["matriz_corr_residuo"]).loc[nomes, nomes].values
        im = ax.imshow(m, vmin=-0.2, vmax=1, cmap="YlGnBu")
        ax.set_xticks(range(len(nomes)), [n.replace(" ", "\n", 1) for n in nomes], fontsize=8)
        ax.set_yticks(range(len(nomes)), nomes, fontsize=8)
        for i in range(len(nomes)):
            for j in range(len(nomes)):
                ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if m[i, j] > .6 else "black")
        ax.set_title(u); ax.grid(False)
    fig.suptitle("Correlação diária entre grupos, sem o perfil de dia da semana "
                 "(dias abertos, seg–sáb, log1p)")
    fig.tight_layout()
    figs.append(C.savefig(fig, "21_grupos_correlacao_residuos.png"))

    # 3. MASE: modelo direto × melhor repartição (SARIMAX), por unidade
    fig, axes = plt.subplots(1, len(unidades), figsize=(6 * len(unidades), 4), sharey=True)
    for ax, u in zip(np.atleast_1d(axes), unidades):
        t = testes[(u, "sarimax")]
        rotulos = FILHOS + [PAI]
        direto = [t["direto"][g]["mase"] for g in rotulos]
        outro = [min(t["reparticao_nivel"][g]["mase"], t["reparticao_dow"][g]["mase"]) for g in FILHOS] \
            + [t["soma_dos_filhos"][PAI]["mase"]]
        x = np.arange(len(rotulos))
        ax.bar(x - .18, direto, .36, label="modelo direto", color="#00838F")
        ax.bar(x + .18, outro, .36, label="repartição do pai / soma dos filhos", color="#B0BEC5")
        ax.axhline(1, color="#B71C1C", lw=.8, ls="--")
        ax.set_xticks(x, [r.replace(" ", "\n", 1) for r in rotulos], fontsize=8)
        ax.set_ylim(0, 1.3)
        ax.set_title(u)
    np.atleast_1d(axes)[0].set_ylabel("MASE (h = 14 d, 26 folds) — abaixo de 1 bate a naïve semanal")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    fig.suptitle("Previsão por grupo: modelo direto × repartição da previsão do grupo maior")
    fig.tight_layout()
    figs.append(C.savefig(fig, "22_grupos_teste_previsao_mase.png"))
    return figs


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    df = df[df["categoria"] != C.NAO_PRODUTO]
    unidades = [u for u in C.UNIDADES if u in set(df["unidade"])]
    series = {u: _series_da_unidade(df, u) for u in unidades}

    viab = bloco_viabilidade(df, series)
    dif = bloco_diferencas(series)
    testes = {(u, p): teste_previsao(series[u], p) for u in unidades for p in ("sarimax", "ets")}
    verd = _veredito(viab, {k: v for k, v in testes.items() if k[1] == "sarimax"})
    verd_robustez = _veredito(viab, {k: v for k, v in testes.items() if k[1] == "ets"})

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "parametros": {"N_FOLDS": N_FOLDS, "HORIZONTE": HORIZONTE, "GANHO_MINIMO": GANHO_MINIMO,
                       "PERDA_MAXIMA_TOTAL": PERDA_MAXIMA_TOTAL,
                       "LIMITE_INTERMITENCIA_PCT": LIMITE_INTERMITENCIA,
                       "previsor_principal": "SARIMAX(1,0,1) + dia da semana, feriado e janela de "
                                             "data comemorativa, log1p com smearing",
                       "previsor_robustez": "Holt-Winters aditivo (nível + sazonalidade semanal), "
                                            "log1p com smearing"},
        "grupos": {g: fins for g, fins in GRUPOS.items()} | {PAI: FIN_PLANTAS + FIN_INSUMOS},
        "1_viabilidade": viab,
        "2_diferencas": dif,
        "3_teste_previsao": {f"{u} · {p}": t for (u, p), t in testes.items()},
        "3a_ajustes_sarimax": dict(_AJUSTES),
        "3b_veredito": verd,
        "3c_veredito_robustez_ets": verd_robustez,
        "4_arvores": bloco_arvores(df, series),
    }
    resultado["graficos"] = graficos(series, dif, testes, plt)
    path = C.dump_metrics("eda_grupos.json", resultado)

    print("[eda_grupos] viabilidade (dias com venda · % dias úteis zerados · CV)")
    for u in unidades:
        for g in [*GRUPOS, PAI]:
            v = viab[u][g]
            print(f"[eda_grupos] {u:<14}{g:<22}{v['dias_com_venda']:>5} d · "
                  f"{v['pct_dias_zero_excl_domingo']:>5.1f}% zero · CV {v['cv']:.2f} · "
                  f"{v['share_volume_unidade_pct']:>5.1f}% do volume")
    print("[eda_grupos] MASE (SARIMAX): direto | repartição nível | repartição dia-da-semana")
    for u in unidades:
        t = testes[(u, "sarimax")]
        for g in FILHOS:
            print(f"[eda_grupos] {u:<14}{g:<22}{t['direto'][g]['mase']:.3f} | "
                  f"{t['reparticao_nivel'][g]['mase']:.3f} | {t['reparticao_dow'][g]['mase']:.3f}")
        print(f"[eda_grupos] {u:<14}{PAI:<22}direto {t['direto'][PAI]['mase']:.3f} | "
              f"soma dos filhos {t['soma_dos_filhos'][PAI]['mase']:.3f}")
    print(f"[eda_grupos] veredito (SARIMAX): {verd['conclusao']}  "
          f"(menor ganho {verd['menor_ganho_pct']}%, mediana {verd['mediana_ganho_pct']}%)")
    print(f"[eda_grupos] veredito (Holt-Winters, robustez): {verd_robustez['conclusao']}")
    print(f"[eda_grupos] métricas: {path}  ·  {len(resultado['graficos'])} gráficos")
    return resultado


if __name__ == "__main__":
    main()
