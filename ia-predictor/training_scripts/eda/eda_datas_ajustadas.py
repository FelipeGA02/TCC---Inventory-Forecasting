"""EDA 2.6 revisado — efeito das datas comemorativas descontando dia da semana e loja fechada.

A razão original (`eda_series._efeito_datas`) compara a janela {data, data−1, data−2} com a
média geral da série. Quando a data cai num domingo (Dia das Mães, Dia dos Pais), a janela
é sex–sáb–dom e fica abaixo da média mesmo sem efeito nenhum. Esta versão divide a razão
pelo que se esperaria na janela só pelo dia da semana e pelo calendário da loja
(ressalva metodológica 1 do mapa da EDA, até aqui calculada fora do repositório).

    índice_dia[d] ← média(s nos dias de funcionamento REGULAR de dia d) / média(s)
                    (sem abertura excepcional: ela existe por causa da data)
    esperado[e]   ← média, na janela, de (0 se loja fechada, senão índice_dia[dia da semana])
    ajustada[e]   ← razão[e] / esperado[e]

Saídas: 27_datas_comemorativas_ajustadas.png e results/metrics/eda_datas_ajustadas.json.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.eda.eda_datas_ajustadas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from training_scripts.preprocessing.dados_externos_10 import CALENDAR_CSV

from . import _common as C

EVENTOS = ["Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Dia dos Pais", "Finados", "Natal"]
CATEGORIAS = ["Grama", "Produtos de jardim", "Flores de corte"]


def _calendario(unidade: str) -> pd.DataFrame:
    cal = pd.read_csv(CALENDAR_CSV, sep=";", encoding="utf-8", parse_dates=["data"])
    return cal[cal["unidade"] == unidade].set_index("data")[["loja_fechada", "abertura_excepcional"]].astype(bool)


def efeito_ajustado(s: pd.Series, cal: pd.DataFrame) -> dict:
    cal = cal.reindex(s.index, fill_value=False)
    fechado = cal["loja_fechada"]
    base = s.mean()
    # Índice só com dias de funcionamento REGULAR: a abertura excepcional (domingo das Mães
    # em Itabirito) existe por causa da data, então não pode entrar no "esperado sem a data".
    # Sem dias regulares de domingo, o índice de domingo fica 0, que é o domingo normal.
    regulares = s[~fechado & ~cal["abertura_excepcional"]]
    indice_dia = regulares.groupby(regulares.index.weekday).mean() / base
    anos = range(s.index.year.min(), s.index.year.max() + 1)
    out = {}
    for evento, grp in C.datas_comemorativas(anos).groupby("evento"):
        dias = pd.DatetimeIndex(grp["data"]).normalize()
        janela = dias.union(dias - pd.Timedelta(days=1)).union(dias - pd.Timedelta(days=2))
        janela = janela.intersection(s.index)
        if len(janela) == 0:
            continue
        razao = s.loc[janela].mean() / base
        esperado = np.mean([0.0 if fechado[d] else indice_dia.get(d.weekday(), 0.0) for d in janela])
        out[evento] = {"razao": float(razao), "esperado": float(esperado),
                       "ajustada": float(razao / esperado) if esperado else None}
    return out


def _rotulo(serie: str) -> str:
    loja, _, cat = serie.partition(" · ")
    loja = {"Jardim Canadá": "J. Canadá", "Itabirito": "Itabirito"}[loja]
    cat = {"": "total", "Produtos de jardim": "Jardim", "Flores de corte": "Flores"}.get(cat, cat)
    return f"{loja}\n{cat}"


def grafico(res: dict, plt) -> str:
    from matplotlib.ticker import NullFormatter
    series = list(res)
    rotulos = [_rotulo(s) for s in series]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.6), gridspec_kw={"width_ratios": [1, 1.25]})

    # (a) Dia das Mães: razão do relatório × razão ajustada
    x = np.arange(len(series))
    bruta = [res[s]["Dia das Mães"]["razao"] for s in series]
    ajust = [res[s]["Dia das Mães"]["ajustada"] for s in series]
    ax1.bar(x - .2, bruta, .4, color="#B0BEC5", label="razão do relatório (contra a média geral)")
    ax1.bar(x + .2, ajust, .4, color="#00838F", label="ajustada (desconta dia da semana e loja fechada)")
    ax1.axhline(1, color="#B71C1C", lw=.8, ls="--")
    ax1.set_yscale("log")
    ax1.set_yticks([.2, .5, 1, 2, 5], ["0,2", "0,5", "1", "2", "5"])
    ax1.yaxis.set_minor_formatter(NullFormatter())
    ax1.set_xticks(x, rotulos, fontsize=8)
    ax1.set_ylabel("venda na janela ÷ venda típica (escala log; 1 = sem efeito)")
    ax1.set_title("(a) Dia das Mães: a janela sex–sáb–dom já fica abaixo da média\n"
                  "sem efeito nenhum da data", fontsize=10.5)
    ax1.legend(frameon=False, fontsize=8, loc="upper left")

    # (b) mapa de calor: razão ajustada, evento × série
    m = np.array([[res[s][e]["ajustada"] for s in series] for e in EVENTOS])
    im = ax2.imshow(np.log2(m), cmap="RdBu", vmin=-2.5, vmax=2.5, aspect="auto")
    for i in range(len(EVENTOS)):
        for j in range(len(series)):
            v = m[i, j]
            ax2.text(j, i, f"{v:.2f}".replace(".", ","), ha="center", va="center", fontsize=7.5,
                     color="white" if abs(np.log2(v)) > 1.4 else "black")
    ax2.set_xticks(range(len(series)), rotulos, fontsize=8)
    ax2.set_yticks(range(len(EVENTOS)), EVENTOS, fontsize=8.5)
    ax2.grid(False)
    ax2.set_title("(b) Razão ajustada por data e série: azul sobe, vermelho cai", fontsize=10.5)
    cb = fig.colorbar(im, ax=ax2, fraction=.035, pad=.02)
    cb.set_ticks([-2, -1, 0, 1, 2], labels=["¼", "½", "1", "2", "4"])
    fig.tight_layout()
    return C.savefig(fig, "27_datas_comemorativas_ajustadas.png")


def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    res = {}
    for u in C.UNIDADES:
        cal = _calendario(u)
        res[u] = efeito_ajustado(C.serie_unidade(df, u), cal)
        for c in CATEGORIAS:
            res[f"{u} · {c}"] = efeito_ajustado(C.serie_diaria(df, u, c), cal)
    caminho = grafico(res, plt)
    C.dump_metrics("eda_datas_ajustadas.json", {"gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
                                                "por_serie": res, "grafico": caminho})
    for s, r in res.items():
        m = r["Dia das Mães"]
        print(f"[eda_datas_ajustadas] {s:<34} Mães: razão {m['razao']:.2f} · esperado {m['esperado']:.2f} "
              f"· ajustada {m['ajustada']:.2f}")
    return res


if __name__ == "__main__":
    main()
