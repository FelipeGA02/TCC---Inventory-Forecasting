"""Fator multiplicativo das datas comemorativas: SARIMAX de produção com e sem o fator.

Pergunta
--------
Na semana do Dia da Mulher, do Dia das Mães, do Dia dos Namorados e do Natal, Flores de corte
vende várias vezes uma semana comum nas 2 lojas; na semana de Finados, Itabirito vende mais
em Grama, Plantas diversas e Produtos de jardim (`--eda`). O SARIMAX do sistema só conhece o
dia da semana, a loja fechada e a abertura excepcional. Multiplicar a previsão dos dias da
semana da data por um fator aprendido na ocorrência do outro ano melhora a previsão?

Fator
-----
De uma ocorrência (loja, série, data): venda dos dias de 6 dias antes até o dia ÷ base dos
mesmos dias. Base = mediana do mesmo dia da semana nas 4 semanas antes e nas 4 depois, só com
dias normais (loja aberta, sem feriado, sem abertura excepcional, fora de 7 dias antes a 3
depois de outra data e de 20/12 a 10/01). Entram só os dias de loja aberta sem abertura
excepcional: o dia da abertura excepcional (Mães e Finados em Itabirito) a exógena
`abertura_excepcional` já explica.

Na previsão, o previsto e os limites do IC 95% desses mesmos dias são multiplicados pelo
fator. Variantes: `sem` (o sistema), `cheio` (o fator) e `meio` (1 + (fator − 1) / 2: com uma
ocorrência só, o fator muda até 2× de um ano para o outro, e a metade encolhe para 1).

Protocolo
---------
Receita de produção (ADR-017, `ConfigTreino()`): SARIMAX m = 7, d = 0, D = 0, com constante,
ordem por AIC na janela de 365 dias antes da 1ª origem, janela deslizante de 365 dias,
exógenas de calendário; fluxo sem encomendas grandes (média + 4 desvios, ADR-018). Por
ocorrência, 20 origens andando 1 dia, de 19 dias antes da data até a data, h = 14: cada dia
da semana da data é previsto em vários horizontes, e as 8 origens de 13 a 6 dias antes têm a
semana inteira à frente (erro do total da semana).

Testáveis: as ocorrências com 180 dias de histórico antes da 1ª origem — as de 2025 e o Natal
e Finados de 2024. O fator de 2025 vem de 2024, como o sistema faria; o de 2024 vem de 2025
(`fora_de_ordem`: o fator usa o futuro, o SARIMAX não), só para ter mais uma ocorrência.
Flores de corte de Itabirito em Finados treina sem fator: entra só no total da loja.

Execução (a partir de `ia-predictor/`) — um processo por ocorrência, porque o pool de
processos não sobrevive a treinos longos no proot de desenvolvimento:
    python -m training_scripts.datas_comemorativas.fator_multiplicativo --eda
    python -m training_scripts.datas_comemorativas.fator_multiplicativo --preparar
    python -m training_scripts.datas_comemorativas.fator_multiplicativo --listar
    python -m training_scripts.datas_comemorativas.fator_multiplicativo --caso 0
    python -m training_scripts.datas_comemorativas.fator_multiplicativo --consolidar
Saída: `results/metrics/fator_datas_comemorativas/` (EDA, um JSON + CSV por ocorrência) e, ao
consolidar, `results/metrics/fator_datas_comemorativas.csv`.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np
import pandas as pd

from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import selecionar_ordem
from backend.domain.models.trainer import NIVEL_CATEGORIA, ConfigTreino
from training_scripts.encomendas.treino_por_limiar import CALENDARIO_CSV, CATEGORIAS, SLUG, carregar, montar

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "fator_datas_comemorativas")
CONSOLIDADO_CSV = os.path.join(_RAIZ, "results", "metrics", "fator_datas_comemorativas.csv")

EVENTOS = ["Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Dia dos Pais", "Finados", "Natal"]
PRESENTE = ["Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Natal"]
# série → datas testadas; as do EDA com efeito levam fator, Flores de Itabirito em Finados não
CASOS = {
    "jardim-canada:category:Flores de corte": PRESENTE,
    "itabirito:category:Flores de corte": PRESENTE + ["Finados"],
    "itabirito:category:Grama": ["Finados"],
    "itabirito:category:Plantas diversas": ["Finados"],
    "itabirito:category:Produtos de jardim": ["Finados"],
}
SEM_FATOR = {("itabirito:category:Flores de corte", "Finados")}
DIAS_ANTES = 6        # janela da data: 6 dias antes até o dia
ORIGENS_ANTES = 19    # 1ª origem: o último dia da janela ainda cabe no horizonte de 14 dias
SEMANAS_BASE = 4      # base: mesmo dia da semana, 4 semanas antes e 4 depois
VARIANTES = {"sem": 0.0, "meio": 0.5, "cheio": 1.0}


# --------------------------------------------------------------------------- #
# Calendário, base e fator
# --------------------------------------------------------------------------- #
def calendario(unidade: str) -> pd.DataFrame:
    cal = pd.read_csv(CALENDARIO_CSV, sep=";", parse_dates=["data"])
    return cal[cal["unidade"] == unidade].set_index("data").sort_index()


def datas_do_evento(cal: pd.DataFrame, evento: str, ate: pd.Timestamp) -> list[pd.Timestamp]:
    return [d for d in cal.index[cal["data_comemorativa"] == evento] if d <= ate]


def dias_normais(cal: pd.DataFrame) -> pd.Series:
    """Dias que entram na base: loja aberta, sem feriado nem abertura excepcional, longe de
    datas comemorativas e do fim de ano."""
    perto = pd.Series(False, index=cal.index)
    for d in cal.index[cal["data_comemorativa"].isin(EVENTOS)]:
        perto |= (cal.index >= d - pd.Timedelta(days=7)) & (cal.index <= d + pd.Timedelta(days=3))
    mes, dia = cal.index.month, cal.index.day
    fim_de_ano = ((mes == 12) & (dia >= 20)) | ((mes == 1) & (dia <= 10))
    return ((cal["loja_fechada"] == 0) & cal["nome_feriado"].isna() & (cal["abertura_excepcional"] == 0)
            & ~perto & ~fim_de_ano)


def base_mesmo_dia(y: pd.Series, normal: pd.Series) -> pd.Series:
    """Mediana do mesmo dia da semana nas `SEMANAS_BASE` semanas antes e depois (só dias
    normais); NaN com menos de `SEMANAS_BASE` semanas disponíveis."""
    yn = y.where(normal.reindex(y.index, fill_value=False))
    passos = [7 * k for k in range(1, SEMANAS_BASE + 1)]
    lags = pd.concat([yn.shift(s) for s in passos] + [yn.shift(-s) for s in passos], axis=1)
    return lags.median(axis=1).where(lags.notna().sum(axis=1) >= SEMANAS_BASE)


def dias_da_janela(cal: pd.DataFrame, data: pd.Timestamp) -> pd.DatetimeIndex:
    """Dias que levam o fator: de `DIAS_ANTES` antes até a data, loja aberta e sem abertura
    excepcional."""
    dias = pd.date_range(data - pd.Timedelta(days=DIAS_ANTES), data)
    c = cal.reindex(dias)
    return dias[(c["loja_fechada"] == 0) & (c["abertura_excepcional"] == 0)]


def fator(y: pd.Series, cal: pd.DataFrame, data: pd.Timestamp) -> tuple[float, float, float]:
    """(fator, venda, base) da semana de uma ocorrência."""
    base = base_mesmo_dia(y, dias_normais(cal)).reindex(dias_da_janela(cal, data)).dropna()
    venda = float(y.reindex(base.index).sum())
    return (venda / float(base.sum()) if base.sum() > 0 else np.nan), venda, float(base.sum())


# --------------------------------------------------------------------------- #
# EDA: fator da semana de cada data × semanas comuns
# --------------------------------------------------------------------------- #
def eda() -> pd.DataFrame:
    """Fator da semana de cada data, por loja e série (4 categorias e o total), e o percentil
    dele entre as semanas comuns (janela de 7 dias sem data, feriado nem fim de ano)."""
    df = carregar()
    linhas, comuns = [], []
    for unidade, slug in SLUG.items():
        cal = calendario(unidade)
        series = {c: montar(df, "k4", f"{slug}:{NIVEL_CATEGORIA}:{c}")[0] for c in CATEGORIAS}
        series["Total"] = sum(series.values())
        normal = dias_normais(cal)
        aberto = (cal["loja_fechada"] == 0) & (cal["abertura_excepcional"] == 0)
        livre = normal | ~aberto  # dia fechado não atrapalha a janela comum
        livre &= cal["nome_feriado"].isna()
        for nome, y in series.items():
            base = base_mesmo_dia(y, normal)
            for evento in EVENTOS:
                for d in datas_do_evento(cal, evento, y.index.max()):
                    f, venda, b = fator(y, cal, d)
                    linhas.append({"unidade": unidade, "serie": nome, "evento": evento, "ano": d.year,
                                   "fator": f, "venda": venda, "base": b})
            for t in y.index[35:-35]:
                dias = pd.date_range(t - pd.Timedelta(days=DIAS_ANTES), t)
                if not livre.reindex(dias, fill_value=False).all():
                    continue
                ok = dias[aberto.reindex(dias, fill_value=False).values & base.reindex(dias).notna().values]
                if len(ok) >= 4 and base[ok].sum() > 0:
                    comuns.append({"unidade": unidade, "serie": nome, "fator": y[ok].sum() / base[ok].sum()})
    tab, com = pd.DataFrame(linhas), pd.DataFrame(comuns)
    tab["percentil_semanas_comuns"] = [
        float((com.loc[(com.unidade == r.unidade) & (com.serie == r.serie), "fator"] < r.fator).mean())
        for r in tab.itertuples()]
    faixa = com.groupby(["unidade", "serie"])["fator"].quantile([0.05, 0.5, 0.95]).unstack()
    os.makedirs(SAIDA_DIR, exist_ok=True)
    tab.to_csv(os.path.join(SAIDA_DIR, "eda_fator_semana.csv"), sep=";", index=False)
    faixa.to_csv(os.path.join(SAIDA_DIR, "eda_semanas_comuns.csv"), sep=";")
    pd.set_option("display.width", 250)
    print("Semanas comuns (fator: p5, mediana, p95):")
    print(faixa.round(2).to_string())
    print("\nFator da semana (6 dias antes até o dia) — percentil entre as semanas comuns entre colchetes:")
    tab["txt"] = tab["fator"].round(2).astype(str) + " [" + tab["percentil_semanas_comuns"].round(2).astype(str) + "]"
    print(tab.pivot_table(index=["unidade", "serie"], columns=["evento", "ano"], values="txt", aggfunc="first")
          .to_string())
    return tab


# --------------------------------------------------------------------------- #
# Treino por ocorrência
# --------------------------------------------------------------------------- #
def casos() -> list[tuple[str, str, int]]:
    """(série, data comemorativa, ano) testáveis: com 180 dias antes da 1ª origem."""
    cfg, saida = ConfigTreino(), []
    for serie, eventos in CASOS.items():
        unidade = next(u for u, s in SLUG.items() if serie.startswith(s))
        cal = calendario(unidade)
        inicio, fim = pd.Timestamp("2024-01-02"), pd.Timestamp("2026-02-28")
        for evento in eventos:
            for d in datas_do_evento(cal, evento, fim):
                if (d - pd.Timedelta(days=ORIGENS_ANTES) - inicio).days >= cfg.min_historico_dias:
                    saida.append((serie, evento, d.year))
    return saida


def _cache(serie: str) -> str:
    return os.path.join(SAIDA_DIR, "cache", serie.replace(":", "_").replace(" ", "_") + ".pkl")


def preparar() -> None:
    """Monta as séries de `CASOS` uma vez e guarda em cache. A base carregada ocupa ~500 MB
    por processo: 6 treinos em paralelo, cada um carregando a base, esgotam a memória do
    Termux, e o Android derruba o processo."""
    df = carregar()
    os.makedirs(os.path.dirname(_cache("x")), exist_ok=True)
    for serie in CASOS:
        y, X, aberta, _, nome, unidade, *_ = montar(df, "k4", serie)
        pd.to_pickle((y, X, aberta, nome, unidade), _cache(serie))


def rodar(indice: int) -> dict:
    t0 = time.time()
    serie, evento, ano = casos()[indice]
    cfg = ConfigTreino()
    y, X, aberta, nome, unidade = pd.read_pickle(_cache(serie))
    cal = calendario(unidade)
    datas = datas_do_evento(cal, evento, y.index.max())
    data = next(d for d in datas if d.year == ano)
    outra = max((d for d in datas if d.year != ano and d < data), default=None) or \
        min(d for d in datas if d.year != ano)
    f, venda_outra, base_outra = fator(y, cal, outra)
    com_fator = (serie, evento) not in SEM_FATOR
    janela = dias_da_janela(cal, data)

    origens = pd.date_range(data - pd.Timedelta(days=ORIGENS_ANTES), data)
    pre = y[y.index < origens[0]].iloc[-cfg.janela_dias:]
    escolha = selecionar_ordem(pre, X.loc[pre.index], d=cfg.d, D=cfg.D, m=cfg.m, grade_pq=cfg.grade_pq,
                               grade_PQ=cfg.grade_PQ, maxiter=cfg.maxiter)
    linhas = []
    for origem in origens:
        treino = y[y.index < origem].iloc[-cfg.janela_dias:]
        futuro = pd.date_range(origem, periods=cfg.horizonte, freq="D")
        res = ajustar(treino, X.loc[treino.index], escolha.ordem, escolha.ordem_sazonal, cfg.maxiter)
        prev, inf, sup = prever(res, X.loc[futuro], cfg.alpha)
        ultima_semana = treino.values[-cfg.m:]
        for h, dia in enumerate(futuro):
            linhas.append({"origem": origem, "data": dia, "horizonte": h + 1, "previsto": prev[h],
                           "ic_inf": inf[h], "ic_sup": sup[h], "real": float(y.loc[dia]),
                           "naive": float(ultima_semana[h % cfg.m]), "aberta": bool(aberta.loc[dia]),
                           "na_janela": dia in janela})
    saida = {"serie": serie, "unidade": unidade, "nome": nome, "evento": evento, "ano": ano,
             "data": data.date().isoformat(), "dias_na_janela": len(janela), "com_fator": com_fator,
             "fator": round(f, 4), "fator_de": outra.date().isoformat(), "fora_de_ordem": bool(outra > data),
             "venda_semana_fator": round(venda_outra, 1), "base_semana_fator": round(base_outra, 1),
             "ordem": escolha.ordem, "ordem_sazonal": escolha.ordem_sazonal, "aic": round(escolha.aic, 2),
             "segundos": round(time.time() - t0, 1)}
    os.makedirs(SAIDA_DIR, exist_ok=True)
    arquivo = os.path.join(SAIDA_DIR, f"{serie.replace(':', '_')}__{evento}__{ano}".replace(" ", "_"))
    with open(arquivo + ".json", "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)
    pd.DataFrame(linhas).to_csv(arquivo + "_backtest.csv", sep=";", index=False)
    return saida


# --------------------------------------------------------------------------- #
# Consolidação
# --------------------------------------------------------------------------- #
def _com_variante(pontos: pd.DataFrame, info: dict, variante: str) -> pd.DataFrame:
    mult = 1 + VARIANTES[variante] * (info["fator"] - 1) if info["com_fator"] else 1.0
    p = pontos.copy()
    sel = p["na_janela"]
    for c in ("previsto", "ic_inf", "ic_sup"):
        p.loc[sel, c] = p.loc[sel, c] * mult
    return p


def _metricas(p: pd.DataFrame, data: pd.Timestamp) -> dict:
    """Erros nos dias da janela da data (todas as origens) e no total da semana (origens com
    a janela inteira à frente)."""
    d = p[p["na_janela"]]
    erro, erro_naive = (d["real"] - d["previsto"]).abs(), (d["real"] - d["naive"]).abs()
    inicio = data - pd.Timedelta(days=DIAS_ANTES)
    inteiras = d[(d["origem"] <= inicio) & (d["origem"] + pd.Timedelta(days=13) >= data)]
    sem = inteiras.groupby("origem")[["previsto", "real"]].sum()
    fora = p[~p["na_janela"]]  # controle: o fator não toca esses dias
    return {"previsto_fora": fora["previsto"].sum(), "real_fora": fora["real"].sum(), "pontos": len(d), "erro_dia": erro.sum(), "erro_naive_dia": erro_naive.sum(), "real_dia": d["real"].sum(),
            "previsto_dia": d["previsto"].sum(), "dentro_ic": int(((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).sum()),
            "largura_ic": (d["ic_sup"] - d["ic_inf"]).sum(),
            "origens_semana": len(sem), "erro_semana": (sem["previsto"] - sem["real"]).abs().sum(),
            "real_semana": sem["real"].sum()}


def _resumo(tab: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    g = tab.groupby(por + ["variante"])[["pontos", "erro_dia", "erro_naive_dia", "real_dia", "previsto_dia",
                                         "dentro_ic", "largura_ic", "erro_semana", "real_semana",
                                         "previsto_fora", "real_fora"]].sum()
    out = pd.DataFrame({
        "fora_previsto_sobre_real_pct": 100 * g["previsto_fora"] / g["real_fora"],
        "erro_rel_naive": g["erro_dia"] / g["erro_naive_dia"],
        "mae_dia": g["erro_dia"] / g["pontos"],
        "previsto_sobre_real_pct": 100 * g["previsto_dia"] / g["real_dia"],
        "erro_semana_pct": 100 * g["erro_semana"] / g["real_semana"],
        "cobertura_ic95_pct": 100 * g["dentro_ic"] / g["pontos"],
        "largura_ic95": g["largura_ic"] / g["pontos"],
    })
    out = out.unstack("variante").round(3)
    return out.reindex(columns=pd.MultiIndex.from_product([out.columns.get_level_values(0).unique(),
                                                                       list(VARIANTES)]))


def consolidar() -> pd.DataFrame:
    infos, pontos = [], {}
    for caminho in sorted(glob.glob(os.path.join(SAIDA_DIR, "*.json"))):
        with open(caminho, encoding="utf-8") as fh:
            info = json.load(fh)
        infos.append(info)
        p = pd.read_csv(caminho[:-5] + "_backtest.csv", sep=";", parse_dates=["origem", "data"])
        pontos[(info["serie"], info["evento"], info["ano"])] = p[p["aberta"]]
    linhas = []
    for info in infos:
        chave, data = (info["serie"], info["evento"], info["ano"]), pd.Timestamp(info["data"])
        for v in VARIANTES:
            linhas.append({**{k: info[k] for k in ("unidade", "nome", "evento", "ano", "fator", "fator_de",
                                                     "fora_de_ordem", "com_fator")},
                           "variante": v, **_metricas(_com_variante(pontos[chave], info, v), data)})
    # total de Itabirito em Finados: soma das 4 categorias por (origem, dia); sem IC (a soma
    # dos limites não é a faixa do total)
    for ano in sorted({i["ano"] for i in infos if i["evento"] == "Finados"}):
        partes = [i for i in infos if i["evento"] == "Finados" and i["ano"] == ano]
        if len(partes) < len(CATEGORIAS):
            continue
        for v in VARIANTES:
            # as categorias da loja têm o mesmo calendário: a janela é a mesma em todas
            soma = (pd.concat([_com_variante(pontos[(i["serie"], i["evento"], i["ano"])], i, v) for i in partes])
                    .groupby(["origem", "data"], as_index=False)
                    .agg(previsto=("previsto", "sum"), real=("real", "sum"), naive=("naive", "sum"),
                         ic_inf=("ic_inf", "sum"), ic_sup=("ic_sup", "sum"), na_janela=("na_janela", "max")))
            m = _metricas(soma, pd.Timestamp(partes[0]["data"]))
            m["dentro_ic"], m["largura_ic"] = np.nan, np.nan
            linhas.append({"unidade": "Itabirito", "nome": "Total da loja", "evento": "Finados", "ano": ano,
                           "fator": np.nan, "fator_de": None, "fora_de_ordem": ano == 2024, "com_fator": True,
                           "variante": v, **m})
    tab = pd.DataFrame(linhas)
    tab.to_csv(CONSOLIDADO_CSV, sep=";", index=False, encoding="utf-8")
    return tab


def imprimir(tab: pd.DataFrame) -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    com = tab[tab["com_fator"]]
    print("Por ocorrência:")
    print(_resumo(com, ["unidade", "nome", "evento", "ano"])[["erro_rel_naive", "erro_semana_pct"]].to_string())
    print("\nPor série (todas as ocorrências):")
    print(_resumo(com, ["unidade", "nome"]).to_string())
    print("\nPor série, só em ordem (fator do ano anterior):")
    print(_resumo(com[~com["fora_de_ordem"]], ["unidade", "nome"])[["erro_rel_naive", "erro_semana_pct"]].to_string())
    print(f"\n[fator_multiplicativo] {tab[['unidade', 'nome', 'evento', 'ano']].drop_duplicates().shape[0]} "
          f"ocorrências em {CONSOLIDADO_CSV}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--eda", action="store_true", help="fator da semana de cada data × semanas comuns")
    p.add_argument("--preparar", action="store_true", help="monta as séries e guarda em cache (antes de --caso)")
    p.add_argument("--listar", action="store_true", help="imprime as ocorrências testáveis, com o índice")
    p.add_argument("--caso", type=int, help="treina uma ocorrência (índice de --listar)")
    p.add_argument("--consolidar", action="store_true")
    a = p.parse_args()
    if a.eda:
        eda()
    elif a.preparar:
        preparar()
    elif a.listar:
        for i, c in enumerate(casos()):
            print(i, *c, sep=";")
    elif a.consolidar:
        imprimir(consolidar())
    else:
        r = rodar(a.caso)
        print(f"[fator_multiplicativo] {r['nome']} {r['unidade']} {r['evento']} {r['ano']}: fator {r['fator']} "
              f"(de {r['fator_de']}) · ordem {r['ordem']}{r['ordem_sazonal']} · {r['segundos']}s")


if __name__ == "__main__":
    main()
