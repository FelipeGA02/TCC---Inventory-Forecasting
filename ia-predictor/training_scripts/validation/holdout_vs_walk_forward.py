"""Walk-forward (treino de hoje) × holdout com correção, na previsão de 56 dias.

Pergunta
--------
O sistema prevê 14 dias. Se a loja quiser ver mais longe (8 semanas), qual receita acerta
mais: o treino de hoje, só esticando o horizonte, ou um treino validado num holdout do mesmo
tamanho do horizonte e corrigido por ele?

Métodos (todos com a receita de produção: SARIMAX m = 7, d = 0, D = 0, com constante,
exógenas de calendário, janela deslizante de 365 dias, fluxo sem encomendas grandes e o
fator das datas comemorativas do ADR-019)
--------------------------------------------------------------------------------------------
  A   treino de hoje (`trainer.treinar_serie`): ordem por AIC na janela antes da 1ª origem,
      walk-forward de 56 origens andando 1 dia (h = 14) que só AVALIA (dá o status), ajuste
      final nos últimos 365 dias. Aqui o ajuste final prevê 56 dias em vez de 14.
  B   holdout: os últimos V = 56 dias antes do corte ficam de fora; cada ordem do grid é
      ajustada nos 365 dias antes deles e prevê os 56 de uma vez; fica a ordem de menor erro
      absoluto nos dias de loja aberta do holdout ("corrige" a escolha com a validação).
      Depois reajusta essa ordem nos últimos 365 dias (com o holdout) e prevê 56 dias.
  B+c B com correção de nível: o previsto e a faixa × (vendido ÷ previsto) do holdout, nos
      dias de loja aberta, com a ordem escolhida.

Na escolha de ordem do grid, quando a ordem de A e a de B coincidem as previsões de A e B são
idênticas: os dois reajustam a mesma ordem na mesma janela. O walk-forward de A não muda a
previsão; muda só o status.

Teste
-----
Cortes a cada 28 dias, de 01/03/2025 (o 1º com 365 + 56 dias de histórico antes) até
03/01/2026 (o último com 56 dias de venda conhecida depois). Em cada corte, A e B só veem a
venda até o corte; o teste são os 56 dias seguintes, nos dias de loja aberta, por bloco de 14
dias (h 1–14, 15–28, 29–42, 43–56). Tamanho do holdout = horizonte: "o conjunto de teste deve
ser, de preferência, pelo menos do tamanho do maior horizonte de previsão" (Hyndman &
Athanasopoulos, *Forecasting: Principles and Practice*, 3ª ed., §5.8).

Séries: lidas do banco de `DATABASE_URL` como o treino as monta (`servico_previsao._montar_series`).

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.validation.holdout_vs_walk_forward --rodar --workers 14
    python -m training_scripts.validation.holdout_vs_walk_forward --consolidar
Saída: `training_scripts/results/metrics/holdout_vs_walk_forward/` (um JSON + CSV por série e
corte; ao consolidar, `resumo_*.csv`).
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.trainer import ConfigTreino, _ajustes_datas, treinar_serie

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "holdout_vs_walk_forward")

H = 56                      # horizonte avaliado
V = 56                      # holdout de B (= horizonte, FPP3 §5.8)
PASSO_CORTE = 28
PRIMEIRO_CORTE = pd.Timestamp("2025-03-01")
BLOCOS = [(1, 14), (15, 28), (29, 42), (43, 56)]
# as 8 categorias e os produtos de grama de maior volume (classificação SKU a SKU de 04/11/2026)
SERIES = [
    *(f"{loja}:category:{c}" for loja in ("jardim-canada", "itabirito")
      for c in ("grama", "plantas-diversas", "produtos-de-jardim", "flores-de-corte")),
    "jardim-canada:product:147",
    "jardim-canada:product:3",
    "jardim-canada:product:710",
    "jardim-canada:product:166",
    "itabirito:product:00013475",
    "itabirito:product:147",
]


def _nome(chave: str, corte: pd.Timestamp) -> str:
    return f"{chave.replace(':', '_')}_{corte:%Y%m%d}"


def _prever_h(y_treino, X, ordem, sazonal, dias, cfg, y_corte, com_fator, com_queda):
    """Ajusta na janela `y_treino` e prevê `dias`, com o fator das datas (venda até o corte)."""
    res = ajustar(y_treino, X.loc[y_treino.index], ordem, sazonal, cfg.maxiter)
    prev, inf, sup = prever(res, X.loc[dias], cfg.alpha)
    fator, _ = _ajustes_datas(y_corte, X, dias[0], dias, cfg, com_fator, com_queda)
    return prev * fator, inf * fator, sup * fator, res


def _base_teste(chave, y, aberta, corte, cfg) -> pd.DataFrame:
    y_c = y[y.index <= corte]
    janela_final = y_c.iloc[-cfg.janela_dias:]
    teste = pd.date_range(corte + pd.Timedelta(days=1), periods=H, freq="D")
    naive = np.array([janela_final.values[-cfg.m:][i % cfg.m] for i in range(H)])
    escala = float(np.mean(np.abs(janela_final.values[cfg.m:] - janela_final.values[:-cfg.m])))
    return pd.DataFrame({"serie": chave, "corte": corte, "data": teste, "h": np.arange(1, H + 1),
                         "real": y.loc[teste].values, "naive": naive, "escala": escala,
                         "aberta": aberta.loc[teste].values})


def _gravar(nome: str, info: dict, pontos: pd.DataFrame | None) -> str:
    if pontos is not None:
        pontos.to_csv(os.path.join(SAIDA_DIR, nome + ".csv"), index=False, sep=";")
    json.dump(info, open(os.path.join(SAIDA_DIR, nome + ".json"), "w"), ensure_ascii=False, indent=1, default=str)
    return nome


def rodar_caso(args) -> str:
    """Uma tarefa: o método A ou o B (`metodo`) numa série e num corte."""
    metodo, chave, nivel, y, X, aberta, com_fator, com_queda, corte = args
    return (_rodar_a if metodo == "A" else _rodar_b)(chave, nivel, y, X, aberta, com_fator, com_queda, corte)


def _rodar_a(chave, nivel, y, X, aberta, com_fator, com_queda, corte) -> str:
    """A — o treino de hoje (`treinar_serie`), com o ajuste final previsto por H dias."""
    cfg = ConfigTreino()
    nome = _nome(chave, corte) + "_A"
    y_c = y[y.index <= corte]
    janela_final = y_c.iloc[-cfg.janela_dias:]
    info = {"serie": chave, "corte": f"{corte:%Y-%m-%d}"}
    t0 = time.time()
    r = treinar_serie(y_c, X, aberta, cfg, nivel, com_fator=com_fator, com_queda=com_queda)
    if r.ordem is None:
        return _gravar(nome, {**info, "pulado": f"A: {r.status} — {r.motivo}"}, None)
    base = _base_teste(chave, y, aberta, corte, cfg)
    pa, ia, sa, _ = _prever_h(janela_final, X, r.ordem, r.ordem_sazonal, pd.DatetimeIndex(base["data"]), cfg, y_c,
                              com_fator, com_queda)
    info["A"] = {"ordem": [r.ordem, r.ordem_sazonal], "status": r.status, "walk_forward": r.metricas,
                 "segundos": round(time.time() - t0, 1),
                 # os 14 primeiros dias têm de ser os do sistema
                 "confere_14d": bool(np.allclose(pa[:14], r.previsao["previsto"].values, rtol=1e-6, atol=1e-6))}
    return _gravar(nome, info, base.assign(metodo="A", previsto=pa, ic_inf=ia, ic_sup=sa))


def _rodar_b(chave, nivel, y, X, aberta, com_fator, com_queda, corte) -> str:
    """B — holdout de V dias, ordem pelo erro no holdout; B+c com a correção de nível."""
    cfg = ConfigTreino()
    nome = _nome(chave, corte) + "_B"
    y_c = y[y.index <= corte]
    janela_final = y_c.iloc[-cfg.janela_dias:]
    info = {"serie": chave, "corte": f"{corte:%Y-%m-%d}"}
    t1 = time.time()
    hold = pd.date_range(corte - pd.Timedelta(days=V - 1), corte, freq="D")
    treino_b = y_c[y_c.index < hold[0]].iloc[-cfg.janela_dias:]
    y_antes_hold = y_c[y_c.index < hold[0]]
    ab_h = aberta.loc[hold].values
    real_h = y_c.loc[hold].values
    naive_h = np.array([treino_b.values[-cfg.m:][i % cfg.m] for i in range(V)])
    grade = []
    for p, q, P, Q in itertools.product(cfg.grade_pq, cfg.grade_pq, cfg.grade_PQ, cfg.grade_PQ):
        o, so = (p, cfg.d, q), (P, cfg.D, Q, cfg.m)
        try:
            ph, _, _, res = _prever_h(treino_b, X, o, so, hold, cfg, y_antes_hold, com_fator, com_queda)
        except Exception:  # noqa: BLE001
            continue
        if not np.all(np.isfinite(ph)) or not np.isfinite(res.aic):
            continue
        grade.append({"ordem": [o, so], "aic": float(res.aic), "mae": float(np.abs(real_h - ph)[ab_h].mean()),
                      "prev_aberto": float(ph[ab_h].sum())})
    if not grade:
        return _gravar(nome, {**info, "pulado": "B: nenhuma ordem ajustou"}, None)
    melhor = min(grade, key=lambda g: g["mae"])
    pelo_aic = min(grade, key=lambda g: g["aic"])
    o, so = tuple(melhor["ordem"][0]), tuple(melhor["ordem"][1])
    razao = float(real_h[ab_h].sum() / melhor["prev_aberto"]) if melhor["prev_aberto"] > 0 else 1.0
    info["B"] = {"ordem": [o, so], "ordem_aic_mesma_janela": pelo_aic["ordem"],
                 "holdout": {"mae": round(melhor["mae"], 2),
                             "mae_naive": round(float(np.abs(real_h - naive_h)[ab_h].mean()), 2),
                             "erro_relativo_naive": round(melhor["mae"] / float(np.abs(real_h - naive_h)[ab_h].mean()), 3),
                             "razao_vendido_previsto": round(razao, 3)},
                 "ordens_ajustadas": len(grade)}
    base = _base_teste(chave, y, aberta, corte, cfg)
    pb, ib, sb, _ = _prever_h(janela_final, X, o, so, pd.DatetimeIndex(base["data"]), cfg, y_c, com_fator, com_queda)
    info["B"]["segundos"] = round(time.time() - t1, 1)
    return _gravar(nome, info, pd.concat([
        base.assign(metodo="B", previsto=pb, ic_inf=ib, ic_sup=sb),
        base.assign(metodo="B+c", previsto=pb * razao, ic_inf=ib * razao, ic_sup=sb * razao)]))


def carregar_series():
    from backend.infrastructure.database import SessionLocal
    from backend.services import servico_previsao as sp
    sp._registrar = lambda *a, **k: None  # sem job: não grava log
    series, _ = sp._montar_series(SessionLocal(), sp.config_treino(), 0)
    return {s.chave: s for s in series}


def rodar(workers: int) -> None:
    os.makedirs(SAIDA_DIR, exist_ok=True)
    series = carregar_series()
    fim = max(s.y.index.max() for s in series.values())
    cortes = list(pd.date_range(PRIMEIRO_CORTE, fim - pd.Timedelta(days=H), freq=f"{PASSO_CORTE}D"))
    # A (~106 ajustes) antes de B (~37): as tarefas longas primeiro, as curtas preenchem o fim
    tarefas = []
    for metodo in ("A", "B"):
        for chave in SERIES:
            s = series[chave]
            for c in cortes:
                if not os.path.exists(os.path.join(SAIDA_DIR, f"{_nome(chave, c)}_{metodo}.json")):
                    tarefas.append((metodo, chave, s.nivel, s.y, s.X, s.aberta, s.com_fator, s.com_queda, c))
    print(f"{len(cortes)} cortes ({cortes[0]:%d/%m/%Y} a {cortes[-1]:%d/%m/%Y}), {len(tarefas)} tarefas a rodar "
          f"em {workers} processos", flush=True)
    t = time.time()
    # um processo por núcleo e uma thread de BLAS por processo: sem isso os processos disputam os núcleos
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_caso, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


def _metricas(d: pd.DataFrame) -> dict:
    d = d[d["aberta"]]
    e = (d["real"] - d["previsto"]).abs()
    en = (d["real"] - d["naive"]).abs()
    tot = d.groupby("corte")[["previsto", "real"]].sum()
    return {"dias": len(d), "erro_rel_naive": e.sum() / en.sum(), "mase": (e / d["escala"]).mean(),
            "mae": e.mean(), "cobertura_ic95": ((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).mean() * 100,
            "previsto_sobre_real": d["previsto"].sum() / d["real"].sum() * 100,
            "erro_total_bloco": (tot["previsto"] - tot["real"]).abs().sum() / tot["real"].sum() * 100}


def consolidar() -> None:
    pts = pd.concat([pd.read_csv(f, sep=";", parse_dates=["corte", "data"]) for f in glob.glob(os.path.join(SAIDA_DIR, "*_[AB].csv"))])
    por_caso: dict = {}
    for f in glob.glob(os.path.join(SAIDA_DIR, "*_[AB].json")):
        i = json.load(open(f))
        caso = por_caso.setdefault((i["serie"], i["corte"]), {"serie": i["serie"], "corte": i["corte"]})
        caso.update({k: v for k, v in i.items() if k not in ("serie", "corte")})
    infos = [i if "pulado" in i or ("A" in i and "B" in i) else {**i, "pulado": "caso incompleto"}
             for i in por_caso.values()]
    for i in infos:
        if "pulado" not in i:
            i["mesma_ordem"] = i["A"]["ordem"] == i["B"]["ordem"]
    # caso com A ou B pulado sai inteiro, para os métodos serem comparados nos mesmos cortes
    validos = {(i["serie"], i["corte"]) for i in infos if "pulado" not in i}
    pts = pts[[(s, f"{c:%Y-%m-%d}") in validos for s, c in zip(pts["serie"], pts["corte"])]]
    pts["aberta"] = pts["aberta"].astype(bool)
    pts["bloco"] = pd.cut(pts["h"], [0, 14, 28, 42, 56], labels=["1-14", "15-28", "29-42", "43-56"])
    linhas = []
    for (serie, metodo), g in pts.groupby(["serie", "metodo"]):
        for bloco, gb in [("1-56", g)] + list(g.groupby("bloco", observed=True)):
            linhas.append({"serie": serie, "metodo": metodo, "bloco": bloco, **_metricas(gb)})
    res = pd.DataFrame(linhas).round(3)
    res.to_csv(os.path.join(SAIDA_DIR, "resumo_metricas.csv"), index=False, sep=";")

    # vitórias por corte (erro absoluto somado nos 56 dias, loja aberta)
    ab = pts[pts["aberta"]].assign(ae=lambda d: (d["real"] - d["previsto"]).abs())
    por_corte = ab.pivot_table(index=["serie", "corte"], columns="metodo", values="ae", aggfunc="sum")
    por_corte.to_csv(os.path.join(SAIDA_DIR, "resumo_por_corte.csv"), sep=";")

    # validação × teste: o que cada validação prometia e o que o teste deu
    val = []
    for i in infos:
        if "pulado" in i:
            continue
        c = pd.Timestamp(i["corte"])
        g = ab[(ab["serie"] == i["serie"]) & (ab["corte"] == c)]
        en = lambda d: (d["real"] - d["naive"]).abs().sum()  # noqa: E731
        ga, gb = g[g["metodo"] == "A"], g[g["metodo"] == "B"]
        val.append({"serie": i["serie"], "corte": i["corte"], "mesma_ordem": i["mesma_ordem"],
                    "ordem_A": str(i["A"]["ordem"]), "ordem_B": str(i["B"]["ordem"]), "status_A": i["A"]["status"],
                    "A_val_erro_rel_naive_h14": i["A"]["walk_forward"]["erro_relativo_naive"],
                    "A_val_mase": i["A"]["walk_forward"]["mase"],
                    "A_teste_erro_rel_naive_h14": ga[ga["h"] <= 14]["ae"].sum() / en(ga[ga["h"] <= 14]),
                    "A_teste_erro_rel_naive_h56": ga["ae"].sum() / en(ga),
                    "B_val_erro_rel_naive_h56": i["B"]["holdout"]["erro_relativo_naive"],
                    "B_teste_erro_rel_naive_h56": gb["ae"].sum() / en(gb),
                    "B_razao": i["B"]["holdout"]["razao_vendido_previsto"],
                    "confere_14d": i["A"]["confere_14d"]})
    pd.DataFrame(val).round(3).to_csv(os.path.join(SAIDA_DIR, "resumo_validacao.csv"), index=False, sep=";")
    pulados = [(i["serie"], i["corte"], i["pulado"]) for i in infos if "pulado" in i]
    pd.set_option("display.width", 220)
    print(res.pivot_table(index=["serie", "bloco"], columns="metodo", values="erro_rel_naive").round(3))
    print("pulados:", pulados)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.rodar:
        rodar(a.workers)
    if a.consolidar:
        consolidar()


if __name__ == "__main__":
    main()
