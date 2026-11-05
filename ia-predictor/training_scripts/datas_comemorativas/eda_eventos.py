"""EDA: quais feriados e datas comemorativas mexem na venda de cada série do sistema.

Pergunta
--------
Em quais séries (as 4 categorias e cada produto de grama com previsão, por loja — ADR-017) um
feriado ou uma data comemorativa muda a venda o bastante para justificar um fator, como o de
Flores de corte (ADR-019)? Só EDA, no fluxo sem encomendas grandes (ADR-018).

Eventos
-------
Os do calendário de cada loja (`calendario_diario.csv`): feriados nacionais, fechamentos
observados (15/08, 08/12...), Páscoa e as 6 datas comemorativas. E, pela regra, datas que
podem mexer numa floricultura: Dia dos Avós (26/07), Dia da Árvore (21/09), Dia da Secretária
(30/09), Dia do Professor (15/10) e Black Friday (sexta depois da 4ª quinta de novembro).
Carnaval conta como um evento (segunda e terça); Sexta-feira Santa e Páscoa também.

Janelas (em volta da data; "aberto" = loja aberta)
--------------------------------------------------
  * `antes`  — os 3 dias abertos antes do evento (a compra antecipada do feriado);
  * `semana` — os dias abertos de 6 dias antes até a data (a janela do fator, ADR-019);
  * `dia`    — o próprio dia, se a loja abre;
  * `depois` — os 2 dias abertos depois do evento (a compra adiada).

Cada janela: venda ÷ base, base = mediana do mesmo dia da semana nas 6 semanas antes e
depois (com pelo menos 4 delas), só com dias normais (aberto, sem abertura excepcional, fora de 7 dias antes a 3
depois de qualquer evento e de 20/12 a 10/01). O percentil compara com a mesma janela em
dias comuns: `antes` com 3 dias abertos seguidos, `depois` com 2, `dia` com 1, `semana` com
7 dias corridos.

Veredito por (série, evento, janela), com as ocorrências de 2024 a 2026:
  * `alta`  — todas as ocorrências acima do percentil 90 das janelas comuns e média ≥ 1,25;
  * `queda` — todas abaixo do percentil 10 e média ≤ 0,80;
  * fora disso, sem efeito consistente. Janela com base média abaixo de `BASE_MINIMA_UN`
    unidades (produto que quase não vende) fica sem veredito.

Controle (`--controle`): o mesmo teste nas datas falsas — cada evento deslocado 3 semanas
para trás e para frente, no mesmo dia da semana, longe dos eventos verdadeiros. Os vereditos
que aparecem nelas medem quantos dos verdadeiros podem ser acaso: são ~500 combinações com 2
ocorrências cada.

Execução (a partir de `ia-predictor/`):
    python -m training_scripts.datas_comemorativas.eda_eventos [--controle]
Saída: `results/metrics/fator_datas_comemorativas/eda_eventos.csv` (todas as janelas) e
`eda_eventos_vereditos.csv` (só alta e queda).
"""
from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

from backend.domain.models.trainer import NIVEL_PRODUTO, ConfigTreino, motivo_inelegivel
from training_scripts.datas_comemorativas.fator_multiplicativo import SAIDA_DIR, calendario
from training_scripts.encomendas.treino_por_limiar import CATEGORIAS, SLUG, carregar, chaves, montar

FIM_DADOS = pd.Timestamp("2026-02-28")
SEMANAS = 6            # base: mesmo dia da semana, 6 semanas antes e 6 depois
MIN_SEMANAS = 4        # ... com pelo menos 4 delas em dia normal
BASE_MINIMA_UN = 20    # base média da janela abaixo disso: sem veredito
PERTO_ANTES, PERTO_DEPOIS = 7, 3


def _quarta_quinta_novembro(ano: int) -> date:
    d = date(ano, 11, 1)
    return d + timedelta(days=(3 - d.weekday()) % 7 + 21)


EXTRAS = {  # datas pela regra, que o calendário não marca
    "Dia dos Avós": lambda a: date(a, 7, 26),
    "Dia da Árvore": lambda a: date(a, 9, 21),
    "Dia da Secretária": lambda a: date(a, 9, 30),
    "Dia do Professor": lambda a: date(a, 10, 15),
    "Black Friday": lambda a: _quarta_quinta_novembro(a) + timedelta(days=1),
}
AGRUPA = {"Páscoa": "Sexta-feira Santa e Páscoa", "Sexta-feira Santa": "Sexta-feira Santa e Páscoa"}


def eventos(cal: pd.DataFrame) -> pd.DataFrame:
    """Um evento por linha: nome, primeiro e último dia (Carnaval e Páscoa ocupam vários)."""
    linhas = []
    for d, r in cal.iterrows():
        nome = r["data_comemorativa"] if isinstance(r["data_comemorativa"], str) else r["nome_feriado"]
        if not isinstance(nome, str):
            if r["fechamento_observado"] == 1:
                nome = f"Fechamento {d:%d/%m}"
            else:
                continue
        linhas.append((AGRUPA.get(nome, nome), d))
    for ano in range(cal.index.min().year, cal.index.max().year + 1):
        linhas += [(n, pd.Timestamp(f(ano))) for n, f in EXTRAS.items()]
    ev = pd.DataFrame(linhas, columns=["evento", "data"])
    ev["ano"] = ev["data"].dt.year
    ev = ev.groupby(["evento", "ano"]).agg(inicio=("data", "min"), fim=("data", "max")).reset_index()
    return ev[ev["fim"] <= FIM_DADOS]


def base_mesmo_dia(y: pd.Series, normal: pd.Series) -> pd.Series:
    yn = y.where(normal.reindex(y.index, fill_value=False))
    passos = [7 * k for k in range(1, SEMANAS + 1)]
    lags = pd.concat([yn.shift(s) for s in passos] + [yn.shift(-s) for s in passos], axis=1)
    return lags.median(axis=1).where(lags.notna().sum(axis=1) >= MIN_SEMANAS)


def deslocados(ev: pd.DataFrame, semanas: int = 3) -> pd.DataFrame:
    """Datas falsas: cada evento deslocado `semanas` para trás e para frente, longe dos
    verdadeiros (nenhum dia a menos de 10 dias de um evento)."""
    falsos = []
    for passo in (-semanas, semanas):
        d = ev.assign(inicio=ev.inicio + pd.Timedelta(weeks=passo), fim=ev.fim + pd.Timedelta(weeks=passo),
                      evento=ev.evento + f" ({passo:+d} sem)")
        falsos.append(d)
    f = pd.concat(falsos)
    longe = [all(abs((r.inicio - e.inicio).days) > 10 and abs((r.fim - e.fim).days) > 10 for e in ev.itertuples())
             for r in f.itertuples()]
    f = f[longe]
    return f[(f.fim <= FIM_DADOS) & (f.inicio >= ev.inicio.min())]


def dias_normais(cal: pd.DataFrame, ev: pd.DataFrame) -> pd.Series:
    idx = cal.index
    perto = np.zeros(len(idx), dtype=bool)
    for r in ev.itertuples():
        perto |= (idx >= r.inicio - pd.Timedelta(days=PERTO_ANTES)) & (idx <= r.fim + pd.Timedelta(days=PERTO_DEPOIS))
    fim_de_ano = ((idx.month == 12) & (idx.day >= 20)) | ((idx.month == 1) & (idx.day <= 10))
    aberto = (cal["loja_fechada"] == 0) & (cal["abertura_excepcional"] == 0)
    return aberto & ~perto & ~fim_de_ano


def janelas(cal: pd.DataFrame, r) -> dict[str, pd.DatetimeIndex]:
    aberto = cal.index[(cal["loja_fechada"] == 0) & (cal["abertura_excepcional"] == 0)]
    antes = aberto[aberto < r.inicio][-3:]
    depois = aberto[aberto > r.fim][:2]
    semana = aberto[(aberto >= r.fim - pd.Timedelta(days=6)) & (aberto <= r.fim)]
    dia = aberto[(aberto >= r.inicio) & (aberto <= r.fim)]
    return {"antes": antes, "semana": semana, "dia": dia, "depois": depois}


def comuns(y: pd.Series, base: pd.Series, normal: pd.Series, aberto: pd.Series) -> dict[str, np.ndarray]:
    """Razão venda ÷ base nas janelas de dias comuns, por tipo de janela."""
    ok = normal.reindex(y.index, fill_value=False) & base.notna()
    dias = y.index[ok.values]
    yv, bv = y[dias].values, base[dias].values
    saida = {}
    for nome, k in (("dia", 1), ("depois", 2), ("antes", 3)):
        # k dias comuns seguidos na sequência dos dias comuns (o domingo fechado não quebra)
        s_y = np.convolve(yv, np.ones(k), "valid")
        s_b = np.convolve(bv, np.ones(k), "valid")
        saida[nome] = s_y[s_b > 0] / s_b[s_b > 0]
    sem = []
    for t in y.index[35:-35]:
        w = pd.date_range(t - pd.Timedelta(days=6), t)
        abre = w[aberto.reindex(w, fill_value=False).values]
        if len(abre) >= 4 and normal.reindex(abre, fill_value=False).all() and base.reindex(abre).notna().all():
            bs = base[abre].sum()
            if bs > 0:
                sem.append(y[abre].sum() / bs)
    saida["semana"] = np.array(sem)
    return saida


def series_da_loja(df: pd.DataFrame, slug: str) -> dict[str, pd.Series]:
    """Categorias e produtos de grama com previsão (os que `motivo_inelegivel` deixa treinar)."""
    cfg = ConfigTreino()
    out = {}
    for chave in chaves(df):
        if not chave.startswith(slug + ":"):
            continue
        y, X, aberta, nivel, nome, unidade, *_ = montar(df, "k4", chave)
        if nivel == NIVEL_PRODUTO and motivo_inelegivel(y, cfg, nivel):
            continue
        out[nome if nivel != NIVEL_PRODUTO else f"Grama · {nome}"] = y
    return out


def avaliar(df: pd.DataFrame, controle: bool) -> pd.DataFrame:
    """Uma linha por (loja, série, evento, ano, janela); com `controle`, nas datas falsas."""
    linhas = []
    for unidade, slug in SLUG.items():
        cal = calendario(unidade)
        cal = cal[cal.index <= FIM_DADOS + pd.Timedelta(days=60)]
        ev = eventos(cal)
        normal = dias_normais(cal, ev)
        aberto = (cal["loja_fechada"] == 0) & (cal["abertura_excepcional"] == 0)
        alvo = deslocados(ev) if controle else ev
        for nome, y in series_da_loja(df, slug).items():
            base = base_mesmo_dia(y, normal)
            ref = comuns(y, base, normal, aberto)
            for r in alvo.itertuples():
                for tipo, dias in janelas(cal, r).items():
                    dias = dias[(dias >= y.index.min()) & (dias <= y.index.max())]
                    b = base.reindex(dias)
                    if len(dias) == 0 or b.isna().any() or b.sum() <= 0:
                        continue
                    f = float(y[dias].sum() / b.sum())
                    linhas.append({"unidade": unidade, "serie": nome, "evento": r.evento, "ano": r.ano,
                                   "janela": tipo, "dias": len(dias), "venda": float(y[dias].sum()),
                                   "base": float(b.sum()), "fator": f,
                                   "percentil": float((ref[tipo] < f).mean()) if len(ref[tipo]) else np.nan})
    return pd.DataFrame(linhas)


def vereditos(tab: pd.DataFrame) -> pd.DataFrame:
    g = tab.groupby(["unidade", "serie", "evento", "janela"])
    r = g.agg(n=("fator", "size"), fator_medio=("fator", "mean"), fator_min=("fator", "min"),
              fator_max=("fator", "max"), pct_min=("percentil", "min"), pct_max=("percentil", "max"),
              venda=("venda", "sum"), base=("base", "sum")).reset_index()
    r["extra_un"] = (r["venda"] - r["base"]) / r["n"]
    r["base_media"] = r["base"] / r["n"]
    grande = r.base_media >= BASE_MINIMA_UN
    r["veredito"] = np.select(
        [grande & (r.n >= 2) & (r.pct_min >= 0.90) & (r.fator_medio >= 1.25),
         grande & (r.n >= 2) & (r.pct_max <= 0.10) & (r.fator_medio <= 0.80)], ["alta", "queda"], "")
    return r


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--controle", action="store_true", help="o mesmo teste em datas falsas (eventos deslocados)")
    a = p.parse_args()
    df = carregar()
    tab = avaliar(df, a.controle)
    sufixo = "_controle" if a.controle else ""
    os.makedirs(SAIDA_DIR, exist_ok=True)
    tab.to_csv(os.path.join(SAIDA_DIR, f"eda_eventos{sufixo}.csv"), sep=";", index=False)
    r = vereditos(tab)
    ver = r[r.veredito != ""].sort_values(["unidade", "serie", "evento", "janela"])
    ver.to_csv(os.path.join(SAIDA_DIR, f"eda_eventos{sufixo}_vereditos.csv"), sep=";", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    print(ver[["unidade", "serie", "evento", "janela", "n", "veredito", "fator_medio", "fator_min", "fator_max",
               "pct_min", "pct_max", "extra_un", "base_media"]].round(2).to_string(index=False))
    avaliadas = r[(r.n >= 2) & (r.base_media >= BASE_MINIMA_UN)]
    print(f"\n[eda_eventos{sufixo}] {len(avaliadas)} combinações série × evento × janela avaliadas; "
          f"{len(ver)} com efeito consistente ({100 * len(ver) / max(1, len(avaliadas)):.1f}%)")


if __name__ == "__main__":
    main()
