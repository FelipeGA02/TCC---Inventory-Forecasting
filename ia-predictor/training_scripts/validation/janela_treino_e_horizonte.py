"""Qual janela de treino erra menos e até onde a previsão aguenta (doc 11).

Comparação 1 — janela de treino: em cada série que tem previsão (8 categorias + 15 produtos de
grama), o walk-forward com janela deslizante de 90, 180, 270, 365 (produção), 545 dias e com o
histórico inteiro; erro nos 14 dias seguintes a cada corte.
Comparação 2 — horizonte: com a melhor janela de cada série, o erro de 2 semanas a 3 meses à frente.

Protocolo (receita de produção: ADR-017/018/019/020, só a janela muda)
---------------------------------------------------------------------
Cortes semanais (o ritmo da planilha da loja), de 04/01/2025 a 21/02/2026: os 8 primeiros só
aquecem a escolha de d. Em cada corte c, para cada janela W e cada d ∈ {0, 1}, o SARIMAX é ajustado
nos últimos W dias até c e prevê 91 dias, com o fator das datas comemorativas calculado só com venda
até c. A ordem sai por AIC na janela antes da 1ª origem do walk-forward de c, como em produção, a
cada 26 cortes (3 escolhas por série, janela e d). O d de cada corte é o de menor MAE nos 8 cortes
anteriores cujos 14 dias já são conhecidos em c (ADR-020, sem olhar o futuro). O corte em que a série
não seria treinada em produção (`motivo_inelegivel`) fica fora em todas as janelas.

Erro: dias de loja aberta. A escala do MASE e a naïve (repete a última semana) saem sempre dos 365
dias antes do corte, para o denominador não mudar com a janela.

Comparação estatística: Diebold-Mariano (1995) no erro absoluto por dia-alvo, com a variância de
longo prazo pelo estimador EWC e ν = 0,4·T^(2/3) graus de liberdade, com valor crítico t_ν (Lazarus,
Lewis, Stock & Watson, 2018, *JBES*). Janela por validação fora da amostra: Pesaran & Timmermann
(2007), Inoue, Jin & Rossi (2017).

Uso (a partir de `ia-predictor/`, banco local):
    python -m training_scripts.validation.janela_treino_e_horizonte --rodar --workers 4
    python -m training_scripts.validation.janela_treino_e_horizonte --consolidar
Saída: `training_scripts/results/metrics/janela_treino_e_horizonte/`.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace

import numpy as np
import pandas as pd
from scipy import stats

from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import NenhumaOrdemConvergiu, selecionar_ordem
from backend.domain.models.trainer import ConfigTreino, _ajustes_datas, _janela, motivo_inelegivel, origens_walk_forward

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(_RAIZ, "results", "metrics", "janela_treino_e_horizonte")

JANELAS = {"90": 90, "180": 180, "270": 270, "365": 365, "545": 545, "tudo": 100_000}
PRODUCAO = "365"
DS = (0, 1)
H_MAX = 91
H_VALIDACAO = 14
CORTES = pd.date_range("2025-01-04", "2026-02-21", freq="7D")
PRIMEIRO_AVALIADO = pd.Timestamp("2025-03-01")
ULTIMO_COM_14_DIAS = pd.Timestamp("2026-02-14")
BLOCO_ORDEM = 26
CORTES_ESCOLHA = 8        # cortes anteriores que escolhem o d (56 dias, como as 56 origens de produção)
DEFASAGEM = 2             # h = 14 de um corte só é conhecido 2 cortes depois
BANDAS = (("2 sem", 1, 14), ("3 sem", 15, 21), ("4 sem", 22, 28), ("6 sem", 29, 42), ("8 sem", 43, 56), ("3 meses", 57, 91))
ALFA = 0.05


def _arquivo(chave: str, janela: str, d: int) -> str:
    return os.path.join(SAIDA, f"{chave.replace(':', '_')}_j{janela}_d{d}.csv.gz")


def rodar_tarefa(args) -> str:
    chave, nivel, y, X, aberta, com_fator, com_queda, janela, d = args
    base = ConfigTreino()
    cfg = replace(base, janela_dias=JANELAS[janela], d=d)
    quadros, falhas, bloco_atual, escolha = [], 0, None, None
    for i, corte in enumerate(CORTES):
        y_c = y[y.index <= corte]
        if motivo_inelegivel(y_c, base, nivel):
            continue
        if i // BLOCO_ORDEM != bloco_atual or escolha is None:
            pre = _janela(y_c, origens_walk_forward(corte, cfg)[0], cfg.janela_dias)
            try:
                escolha = selecionar_ordem(pre, X.loc[pre.index], d=d, D=cfg.D, m=cfg.m, grade_pq=cfg.grade_pq,
                                           grade_PQ=cfg.grade_PQ, maxiter=cfg.maxiter)
                bloco_atual = i // BLOCO_ORDEM
            except NenhumaOrdemConvergiu:
                falhas += 1
                continue
        treino = y_c.iloc[-cfg.janela_dias:]
        dias = pd.date_range(corte + pd.Timedelta(days=1), min(corte + pd.Timedelta(days=H_MAX), y.index.max()))
        try:
            res = ajustar(treino, X.loc[treino.index], escolha.ordem, escolha.ordem_sazonal, cfg.maxiter)
            prev, inf, sup = prever(res, X.loc[dias], cfg.alpha)
        except Exception:  # noqa: BLE001 — corte que não ajusta fica fora em todas as variantes
            falhas += 1
            continue
        fator, _ = _ajustes_datas(y_c, X, dias[0], dias, base, com_fator, com_queda)
        ano = y_c.iloc[-base.janela_dias:].values
        quadros.append(pd.DataFrame({
            "serie": chave, "janela": janela, "d": d, "corte": corte, "data": dias, "h": np.arange(1, len(dias) + 1),
            "ordem": f"{escolha.ordem}{escolha.ordem_sazonal}", "dias_treino": len(treino), "real": y.loc[dias].values,
            "previsto": prev * fator, "ic_inf": inf * fator, "ic_sup": sup * fator,
            "naive": ano[-base.m:][np.arange(len(dias)) % base.m], "escala": np.mean(np.abs(ano[base.m:] - ano[:-base.m])),
            "aberta": aberta.loc[dias].values}))
    if quadros:
        pd.concat(quadros).to_csv(_arquivo(chave, janela, d), index=False, sep=";", float_format="%.4f")
    return f"{chave} j{janela} d{d}: {len(quadros)} cortes, {falhas} falhas"


def rodar(workers: int, so_serie: str | None, so_janela: str | None) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    os.makedirs(SAIDA, exist_ok=True)
    base = ConfigTreino()
    series = {k: s for k, s in carregar_series().items() if not motivo_inelegivel(s.y, base, s.nivel)}
    with open(os.path.join(SAIDA, "series.json"), "w", encoding="utf-8") as f:
        json.dump({k: {"rotulo": s.rotulo, "nivel": s.nivel} for k, s in series.items()}, f, ensure_ascii=False, indent=1)
    tarefas = [(k, s.nivel, s.y, s.X, s.aberta, s.com_fator, s.com_queda, j, d)
               for k, s in sorted(series.items(), key=lambda kv: (kv[1].nivel != "category", kv[0]))
               for j in JANELAS for d in DS
               if (not so_serie or k == so_serie) and (not so_janela or j == so_janela) and not os.path.exists(_arquivo(k, j, d))]
    print(f"{len(series)} séries, {len(CORTES)} cortes; {len(tarefas)} tarefas em {workers} processos", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_tarefa, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


# ---------------------------------------------------------------- consolidação

def p_dm(dif: pd.Series) -> float:
    """p bilateral de Diebold-Mariano: média da diferença de perdas = 0, com EWC e t_ν (Lazarus et al., 2018)."""
    z = dif.to_numpy(dtype=float)
    T = len(z)
    nu = int(0.4 * T ** (2 / 3))
    if T < 8 or nu < 1:
        return float("nan")
    m = z.mean()
    tempo = (np.arange(1, T + 1) - 0.5) / T
    lam = np.array([np.sqrt(2 / T) * np.sum((z - m) * np.cos(np.pi * j * tempo)) for j in range(1, nu + 1)])
    omega = np.mean(lam ** 2)
    if omega <= 0:
        return float("nan")
    return float(2 * stats.t.sf(abs(np.sqrt(T) * m / np.sqrt(omega)), nu))


def escolha_causal(erro: pd.DataFrame, opcoes: list) -> pd.Series:
    """Por corte, a opção de menor MAE nos `CORTES_ESCOLHA` cortes já conhecidos. `erro`: índice
    corte, colunas (opção, 'ae'|'n'). Empate ou sem dado: a primeira opção."""
    ae = erro["ae"].reindex(CORTES).reindex(columns=opcoes).shift(DEFASAGEM).rolling(CORTES_ESCOLHA, min_periods=1).sum()
    n = erro["n"].reindex(CORTES).reindex(columns=opcoes).shift(DEFASAGEM).rolling(CORTES_ESCOLHA, min_periods=1).sum()
    mae = (ae / n.where(n > 0)).fillna(np.inf).to_numpy()
    return pd.Series([opcoes[i] for i in mae.argmin(axis=1)], index=CORTES)  # argmin: o 1º em empate


def _erro_por_corte(pts: pd.DataFrame, opcao: str) -> pd.DataFrame:
    v = pts[pts["aberta"] & (pts["h"] <= H_VALIDACAO)]
    return v.groupby(["corte", opcao]).agg(ae=("ae", "sum"), n=("ae", "size")).unstack(opcao)


def carregar() -> tuple[pd.DataFrame, dict]:
    with open(os.path.join(SAIDA, "series.json"), encoding="utf-8") as f:
        meta = json.load(f)
    for chave, m in meta.items():  # dois produtos de Jardim Canadá têm o mesmo nome: o código distingue
        if m["nivel"] == "product":
            m["rotulo"] += f" ({chave.rsplit(':', 1)[1]})"
    pts = pd.concat(pd.read_csv(a, sep=";", parse_dates=["corte", "data"]) for a in glob.glob(os.path.join(SAIDA, "*.csv.gz")))
    pts["aberta"] = pts["aberta"].astype(bool)
    n = pts.groupby(["serie", "corte"])[["janela", "d"]].value_counts().groupby(["serie", "corte"]).size()
    ok = n[n == len(JANELAS) * len(DS)].index
    print(f"(série, corte): {len(n)}; com as {len(JANELAS) * len(DS)} variantes: {len(ok)}", flush=True)
    pts = pts.set_index(["serie", "corte"]).loc[ok].reset_index()
    pts["janela"] = pts["janela"].astype(str)
    pts["ae"] = (pts["real"] - pts["previsto"]).abs()
    pts["ae_naive"] = (pts["real"] - pts["naive"]).abs()
    pts["dentro"] = (pts["real"] >= pts["ic_inf"]) & (pts["real"] <= pts["ic_sup"])
    pts["largura"] = pts["ic_sup"] - pts["ic_inf"]
    return pts, meta


def aplicar_d(pts: pd.DataFrame) -> pd.DataFrame:
    """Só as linhas do d escolhido em cada (série, janela, corte), nos cortes avaliados."""
    pedacos = []
    for (_, _), g in pts.groupby(["serie", "janela"]):
        d = escolha_causal(_erro_por_corte(g, "d"), list(DS))
        pedacos.append(g[g["d"].to_numpy() == d.reindex(g["corte"]).to_numpy()])
    sel = pd.concat(pedacos)
    return sel[sel["corte"] >= PRIMEIRO_AVALIADO]


def _metricas(g: pd.DataFrame) -> dict:
    com_escala = g["escala"] > 0
    return {"dias": g["data"].nunique(), "mae": g["ae"].mean(), "wape": g["ae"].sum() / g["real"].sum() * 100,
            "mase": (g.loc[com_escala, "ae"] / g.loc[com_escala, "escala"]).mean(),
            "rel_naive": g["ae"].sum() / g["ae_naive"].sum(), "cobertura": g["dentro"].mean() * 100,
            "largura": g["largura"].mean(), "prev_real": g["previsto"].sum() / g["real"].sum() * 100, "d1_pct": g["d"].mean() * 100}


def _dif_diaria(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    """Diferença de erro por dia-alvo (média das origens do dia), só nos dias comuns."""
    return (a.groupby("data")["ae"].mean() - b.groupby("data")["ae"].mean()).dropna()


def _pct(x: float) -> str:
    return f"{x:+.1f}%".replace(".", ",")


def _num(x: float, casas: int = 1) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def comparacao_janela(sel: pd.DataFrame, meta: dict) -> tuple[dict, str]:
    v = sel[sel["aberta"] & (sel["h"] <= H_VALIDACAO) & (sel["corte"] <= ULTIMO_COM_14_DIAS)]
    linhas = []
    for (serie, janela), g in v.groupby(["serie", "janela"]):
        linhas.append({"serie": serie, "janela": janela, **_metricas(g)})
    r = pd.DataFrame(linhas)
    r["mae_vs_365"] = (r["mae"] / r["serie"].map(r[r["janela"] == PRODUCAO].set_index("serie")["mae"]) - 1) * 100
    r.round(3).to_csv(os.path.join(SAIDA, "comparacao1_por_serie_e_janela.csv"), index=False, sep=";")
    mae = r.pivot(index="serie", columns="janela", values="mae")[list(JANELAS)]
    melhor = mae.idxmin(axis=1).to_dict()

    # janela escolhida a cada corte pelo erro passado, sem olhar o período avaliado
    auto = []
    for serie, g in v.groupby("serie"):
        j = escolha_causal(_erro_por_corte(g, "janela"), [PRODUCAO] + [x for x in JANELAS if x != PRODUCAO])
        auto.append(g[g["janela"].to_numpy() == j.reindex(g["corte"]).to_numpy()])
    auto = pd.concat(auto)
    linhas_tab = []
    resumo = []
    for serie in sorted(mae.index, key=lambda s: (meta[s]["nivel"] != "category", s)):
        m, b = mae.loc[serie], melhor[serie]
        g_b, g_365 = v[(v["serie"] == serie) & (v["janela"] == b)], v[(v["serie"] == serie) & (v["janela"] == PRODUCAO)]
        p = p_dm(_dif_diaria(g_b, g_365)) if b != PRODUCAO else float("nan")
        gan = (m[b] / m[PRODUCAO] - 1) * 100
        ma = auto[auto["serie"] == serie]["ae"].mean()
        res_b = r[(r["serie"] == serie) & (r["janela"] == b)].iloc[0]
        resumo.append({"serie": serie, "melhor": b, "ganho_pct": gan, "p": p, "auto_pct": (ma / m[PRODUCAO] - 1) * 100})
        cels = ["—" if j == PRODUCAO else _pct((m[j] / m[PRODUCAO] - 1) * 100) for j in JANELAS]
        linhas_tab.append(f"| {meta[serie]['rotulo']} | {int(res_b['dias'])} | {_num(m[PRODUCAO])} | " + " | ".join(cels) + f" | **{b}** | "
                          + ("—" if b == PRODUCAO else _pct(gan)) + " | " + ("—" if np.isnan(p) else f"{p:.3f}".replace(".", ",")) + " | "
                          + _pct((ma / m[PRODUCAO] - 1) * 100) + f" | {_num(res_b['mase'], 2)} | {_num(res_b['cobertura'])}% |")
    resumo = pd.DataFrame(resumo)
    resumo.round(4).to_csv(os.path.join(SAIDA, "comparacao1_melhor_janela.csv"), index=False, sep=";")
    # uma janela só para todas: média geométrica da razão ao erro de 365, cada série pesando igual
    razao = mae.div(mae[PRODUCAO], axis=0)
    geo = (np.exp(np.log(razao).mean()) - 1) * 100
    geo_best = (np.exp(np.log(pd.Series({s: razao.loc[s, melhor[s]] for s in razao.index})).mean()) - 1) * 100
    geo_auto = (np.exp(np.log(1 + resumo["auto_pct"] / 100).mean()) - 1) * 100
    cat = [s for s in razao.index if meta[s]["nivel"] == "category"]
    geo_cat = (np.exp(np.log(razao.loc[cat]).mean()) - 1) * 100
    media = "| **Média (cada série pesa igual)** | | | " + " | ".join("—" if j == PRODUCAO else f"**{_pct(geo[j])}**" for j in JANELAS) \
            + f" | | **{_pct(geo_best)}** | | **{_pct(geo_auto)}** | | |\n" \
            + "| **Média das 8 categorias** | | | " + " | ".join("—" if j == PRODUCAO else f"**{_pct(geo_cat[j])}**" for j in JANELAS) \
            + f" | | **{_pct((np.exp(np.log(pd.Series({s: razao.loc[s, melhor[s]] for s in cat})).mean()) - 1) * 100)}** | | " \
            + f"**{_pct((np.exp(np.log(1 + resumo.set_index('serie').loc[cat, 'auto_pct'] / 100).mean()) - 1) * 100)}** | | |"
    jan = " | ".join(("365 (hoje)" if j == PRODUCAO else ("Histórico inteiro" if j == "tudo" else j)) for j in JANELAS)
    tab = (f"| Série | Dias avaliados | MAE 365 dias (un./dia) | {jan} | Melhor | Ganho sobre 365 | p (DM) | Janela escolhida a cada corte | MASE (melhor) | IC 95% (melhor) |\n"
           "| --- | ---: | ---: | " + " | ".join("---:" for _ in JANELAS) + " | :---: | ---: | ---: | ---: | ---: | ---: |\n" + "\n".join(linhas_tab) + "\n" + media)
    print("\n" + tab, flush=True)
    print("\nvitórias por janela:", pd.Series(melhor).value_counts().to_dict())
    print("ganhos com p<0,05:", resumo[(resumo["p"] < ALFA)][["serie", "melhor", "ganho_pct", "p"]].round(3).to_string(index=False))
    return melhor, tab


def comparacao_horizonte(sel: pd.DataFrame, melhor: dict, meta: dict) -> str:
    v = pd.concat(sel[(sel["serie"] == s) & (sel["janela"] == j)] for s, j in melhor.items())
    v = v[v["aberta"]]
    # os mesmos dias-alvo em todas as 13 semanas do horizonte, série a série
    v = v.assign(semana=(v["h"] - 1) // 7 + 1)
    n = v.groupby(["serie", "data"])["semana"].nunique()
    v = v.set_index(["serie", "data"]).loc[n[n == 13].index].reset_index()
    linhas, cumul = [], []
    regra = {}
    sem_avaliacao = {s: "sem nenhum dia vendável nas 13 semanas" for s in melhor if s not in set(v["serie"])}
    for serie, g in v.groupby("serie"):
        b0 = g[g["h"].between(1, 14)]
        if b0["real"].sum() == 0:  # WAPE e erro relativo à naïve indefinidos: não há o que comparar
            sem_avaliacao[serie] = f"{g['data'].nunique()} dias em comum, todos sem venda"
            continue
        ruim, motivo = None, ""
        for rot, lo, hi in BANDAS:
            b = g[g["h"].between(lo, hi)]
            m = _metricas(b)
            p = p_dm(_dif_diaria(b, b0)) if rot != BANDAS[0][0] else float("nan")
            m.update({"serie": serie, "faixa": rot, "p": p})
            linhas.append(m)
            if ruim is None:
                if rot == BANDAS[0][0]:
                    if m["rel_naive"] >= 1:  # já perde da naïve nas 2 primeiras semanas
                        ruim, motivo = rot, "naive"
                elif b["ae"].mean() > b0["ae"].mean() and p < ALFA:
                    ruim, motivo = rot, "dm"
                elif m["rel_naive"] >= 1:
                    ruim, motivo = rot, "naive"
        regra[serie] = (ruim, motivo)
        for H in (14, 21, 28, 42, 56, 91):
            cumul.append({"serie": serie, "H": H, "mae": g[g["h"] <= H].groupby("data")["ae"].mean().mean()})
    r = pd.DataFrame(linhas)
    base = r[r["faixa"] == "2 sem"].set_index("serie")["mae"]
    r["vs_2sem_pct"] = (r["mae"] / r["serie"].map(base) - 1) * 100
    r.round(4).to_csv(os.path.join(SAIDA, "comparacao2_por_serie_e_faixa.csv"), index=False, sep=";")
    c = pd.DataFrame(cumul)
    c["vs_14"] = (c["mae"] / c["serie"].map(c[c["H"] == 14].set_index("serie")["mae"]) - 1) * 100
    c.round(3).to_csv(os.path.join(SAIDA, "comparacao2_acumulado_ate_H.csv"), index=False, sep=";")
    faixas = [b[0] for b in BANDAS]
    tab_l = []
    for serie in sorted(base.index, key=lambda s: (meta[s]["nivel"] != "category", s)):
        q = r[r["serie"] == serie].set_index("faixa")
        cels = []
        for f in faixas[1:]:
            mar = "*" if (q.loc[f, "p"] < ALFA and q.loc[f, "vs_2sem_pct"] > 0) else ""
            nv = " ⚠" if q.loc[f, "rel_naive"] >= 1 else ""
            cels.append(_pct(q.loc[f, "vs_2sem_pct"]) + mar + nv)
        ruim, motivo = regra[serie]
        fim = "não piora até 3 meses" if ruim is None else f"**{ruim}**" + (" (perde da naïve)" if motivo == "naive" else "")
        tab_l.append(f"| {meta[serie]['rotulo']} | {melhor[serie]} | {int(q.loc['2 sem', 'dias'])} | {_num(q.loc['2 sem', 'mae'])} | {_num(q.loc['2 sem', 'wape'], 0)}% | {_num(q.loc['2 sem', 'rel_naive'], 2)} → {_num(q.loc['3 meses', 'rel_naive'], 2)} | " + " | ".join(cels)
                     + f" | {_num(q.loc['2 sem', 'cobertura'], 0)}% → {_num(q.loc['3 meses', 'cobertura'], 0)}% | {fim} |")
    m_rel = r.pivot(index="serie", columns="faixa", values="vs_2sem_pct")[faixas]
    cat = [s for s in m_rel.index if meta[s]["nivel"] == "category"]
    media = ("| **Média (cada série pesa igual)** | | | | | | " + " | ".join(f"**{_pct(m_rel[f].mean())}**" for f in faixas[1:]) + " | | |\n"
             "| **Média das 8 categorias** | | | | | | " + " | ".join(f"**{_pct(m_rel.loc[cat, f].mean())}**" for f in faixas[1:]) + " | | |")
    cab = " | ".join(faixas[1:])
    tab = (f"| Série | Janela | Dias avaliados | MAE até 2 sem (un./dia) | WAPE até 2 sem | Erro ÷ naïve (2 sem → 3 meses) | {cab} | Cobertura IC 95% (2 sem → 3 meses) | Fica ruim a partir de |\n"
           "| --- | :---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: | :---: | --- |\n" + "\n".join(tab_l) + "\n" + media)
    if sem_avaliacao:
        tab += "\n\nFora da tabela (não avaliável): " + "; ".join(f"{meta[s]['rotulo']} — {m}" for s, m in sem_avaliacao.items()) + "."
    print("\n" + tab, flush=True)
    print("\nacumulado até H (média das séries, % sobre 14):", c.groupby("H")["vs_14"].mean().round(1).to_dict())
    print("dias-alvo por série:", v.groupby("serie")["data"].nunique().describe()[["min", "max"]].to_dict())
    print("fica ruim:", pd.Series([x[0] or "nunca" for x in regra.values()]).value_counts().to_dict())
    return tab


def consolidar() -> None:
    pts, meta = carregar()
    sel = aplicar_d(pts)
    melhor, t1 = comparacao_janela(sel, meta)
    t2 = comparacao_horizonte(sel, melhor, meta)
    # o melhor treino de cada série, para levar à produção: janela, e o d e a ordem do último corte
    registro = {}
    for serie, janela in melhor.items():
        g = sel[(sel["serie"] == serie) & (sel["janela"] == janela)]
        u = g[g["corte"] == g["corte"].max()].iloc[0]
        registro[serie] = {"rotulo": meta[serie]["rotulo"], "nivel": meta[serie]["nivel"], "janela": janela,
                           "janela_dias": JANELAS[janela], "ultimo_corte": f"{u['corte']:%Y-%m-%d}", "d": int(u["d"]), "ordem": u["ordem"]}
    with open(os.path.join(SAIDA, "melhor_treino.json"), "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1)
    with open(os.path.join(SAIDA, "tabelas.md"), "w", encoding="utf-8") as f:
        f.write("## Tabela 1\n\n" + t1 + "\n\n## Tabela 2\n\n" + t2 + "\n")
    # descrição das ordens e do d, para o doc
    print("\n% de cortes com d = 1, por janela:", (sel[sel["h"] == 1].groupby("janela")["d"].mean() * 100).round(0).to_dict())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--serie", default=None, help="só esta série (teste)")
    ap.add_argument("--janela", default=None, help="só esta janela (teste)")
    a = ap.parse_args()
    if a.rodar:
        rodar(a.workers, a.serie, a.janela)
    if a.consolidar:
        consolidar()


if __name__ == "__main__":
    main()
