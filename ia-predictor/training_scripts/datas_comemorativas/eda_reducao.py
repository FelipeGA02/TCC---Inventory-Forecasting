"""EDA: onde a venda cai no fim de ano e nos feriados prolongados, em cada série do sistema.

Pergunta
--------
`eda_eventos.py` viu quedas de 0,46 a 0,63 do normal na semana antes de 1º/01 (Grama de
Itabirito; Grama, Plantas diversas e Produtos de jardim de Jardim Canadá) e na Grama nos
feriados de abril e maio. O teste com o SARIMAX de produção (doc 08 §9.2) mostrou que, em
Jardim Canadá, o modelo também prevê acima do vendido fora da semana de 26 a 31/12: a queda
parece ser da temporada de festas, não da semana. Este EDA mede, dia a dia, onde a queda
começa e onde termina, em cada série (as 4 categorias e cada produto de grama com previsão,
por loja — ADR-017), no fluxo sem encomendas grandes (ADR-018). Só EDA, sem modelo.

Medida
------
Venda ÷ base, base = mediana do mesmo dia da semana nas 6 semanas antes e depois (com pelo
menos 4), só com dias normais (loja aberta, sem abertura excepcional, fora de 7 dias antes a
3 depois de qualquer evento do calendário e de 20/12 a 10/01). Como em `eda_eventos.py`.

Blocos do fim de ano (dias de loja aberta, sem abertura excepcional):
  * `dez_1_14`    — 1 a 14/12 (o começo de dezembro, controle: a base já é a de novembro);
  * `dez_15_19`   — 15 a 19/12;
  * `natal`       — 20 a 24/12 (a semana antes do Natal, sem o dia);
  * `ano_novo`    — 26 a 31/12 (a janela do Ano Novo, ADR-019);
  * `jan_2_10`    — 2 a 10/01;
  * `jan_11_20`   — 11 a 20/01 (controle: depois da temporada).
E, para cada feriado prolongado de abril e maio (Sexta-feira Santa, Tiradentes, Dia do
Trabalho, Corpus Christi), a semana de 6 dias antes até o feriado e os 2 dias abertos depois.

Veredito por (série, bloco): `queda` se as 2 temporadas (2024/25 e 2025/26) ficam abaixo do
percentil 10 das semanas comuns e a média ≤ 0,80; `alta` se acima do 90 e média ≥ 1,25.
Dia sem base (perto de outro evento) fica de fora; bloco com menos da metade dos dias com base,
sem medida. Base média abaixo de 20 un. por bloco: sem veredito (produto que quase não vende).

Execução (a partir de `ia-predictor/`):
    python -m training_scripts.datas_comemorativas.eda_reducao
Saída: `results/metrics/fator_datas_comemorativas/eda_reducao.csv` (um bloco por linha) e
`eda_reducao_dias.csv` (venda ÷ base de cada dia de 01/12 a 31/01).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from training_scripts.datas_comemorativas.eda_eventos import (
    BASE_MINIMA_UN, base_mesmo_dia, comuns, dias_normais, eventos, series_da_loja)
from training_scripts.datas_comemorativas.fator_multiplicativo import SAIDA_DIR, calendario
from training_scripts.encomendas.treino_por_limiar import SLUG, carregar

FIM_DADOS = pd.Timestamp("2026-02-28")
TEMPORADAS = (2024, 2025)  # dezembro de 2024 e de 2025 (com o janeiro seguinte)
BLOCOS = {  # nome → (mês, dia inicial, dia final); os de janeiro são do ano seguinte
    "dez_1_14": (12, 1, 14), "dez_15_19": (12, 15, 19), "natal": (12, 20, 24),
    "ano_novo": (12, 26, 31), "jan_2_10": (1, 2, 10), "jan_11_20": (1, 11, 20),
}
FERIADOS = ("Sexta-feira Santa", "Tiradentes", "Dia do trabalho", "Corpus Christi")


def _dias_bloco(temporada: int, bloco: str) -> pd.DatetimeIndex:
    mes, ini, fim = BLOCOS[bloco]
    ano = temporada + (1 if mes == 1 else 0)
    return pd.date_range(f"{ano}-{mes:02d}-{ini:02d}", f"{ano}-{mes:02d}-{fim:02d}")


def avaliar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    blocos, dias_tab = [], []
    for unidade, slug in SLUG.items():
        cal = calendario(unidade)
        cal = cal[cal.index <= FIM_DADOS + pd.Timedelta(days=60)]
        ev = eventos(cal)
        normal = dias_normais(cal, ev)
        aberto = (cal["loja_fechada"] == 0) & (cal["abertura_excepcional"] == 0)
        for nome, y in series_da_loja(df, slug).items():
            base = base_mesmo_dia(y, normal)
            ref = comuns(y, base, normal, aberto)["semana"]
            janelas = [(f"fim de ano: {b}", t, _dias_bloco(t, b)) for t in TEMPORADAS for b in BLOCOS]
            for feriado in FERIADOS:
                for r in ev[ev.evento == feriado].itertuples():
                    janelas.append((f"{feriado}: semana", r.ano, pd.date_range(r.fim - pd.Timedelta(days=6), r.fim)))
                    depois = aberto.index[aberto.values & (aberto.index > r.fim)][:2]
                    janelas.append((f"{feriado}: depois", r.ano, depois))
            for rotulo, temporada, dias in janelas:
                dias = dias[aberto.reindex(dias, fill_value=False).values]
                dias = dias[(dias >= y.index.min()) & (dias <= y.index.max())]
                b = base.reindex(dias).dropna()  # dia sem base (perto de outro evento) fica de fora
                if len(dias) == 0 or len(b) * 2 < len(dias) or b.sum() <= 0:
                    continue
                dias = b.index
                f = float(y[dias].sum() / b.sum())
                blocos.append({"unidade": unidade, "serie": nome, "bloco": rotulo, "temporada": temporada,
                               "dias": len(dias), "venda": float(y[dias].sum()), "base": float(b.sum()),
                               "fator": f, "percentil": float((ref < f).mean()) if len(ref) else np.nan})
            for t in TEMPORADAS:
                for d in pd.date_range(f"{t}-12-01", f"{t + 1}-01-31"):
                    if d in y.index and bool(aberto.get(d, False)) and pd.notna(base.get(d)) and base[d] > 0:
                        dias_tab.append({"unidade": unidade, "serie": nome, "temporada": t, "data": d,
                                         "venda": float(y[d]), "base": float(base[d]), "fator": float(y[d] / base[d])})
    return pd.DataFrame(blocos), pd.DataFrame(dias_tab)


def vereditos(tab: pd.DataFrame) -> pd.DataFrame:
    r = (tab.groupby(["unidade", "serie", "bloco"])
         .agg(n=("fator", "size"), fator_medio=("fator", "mean"), fator_min=("fator", "min"),
              fator_max=("fator", "max"), pct_min=("percentil", "min"), pct_max=("percentil", "max"),
              venda=("venda", "sum"), base=("base", "sum"))
         .reset_index())
    r["base_media"] = r["base"] / r["n"]
    r["fator_somado"] = r["venda"] / r["base"]
    grande = r.base_media >= BASE_MINIMA_UN
    r["veredito"] = np.select(
        [grande & (r.n >= 2) & (r.pct_max <= 0.10) & (r.fator_medio <= 0.80),
         grande & (r.n >= 2) & (r.pct_min >= 0.90) & (r.fator_medio >= 1.25)], ["queda", "alta"], "")
    return r


def main() -> None:
    df = carregar()
    tab, dias = avaliar(df)
    os.makedirs(SAIDA_DIR, exist_ok=True)
    tab.to_csv(os.path.join(SAIDA_DIR, "eda_reducao.csv"), sep=";", index=False)
    dias.to_csv(os.path.join(SAIDA_DIR, "eda_reducao_dias.csv"), sep=";", index=False)
    r = vereditos(tab)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 30)
    fim = tab[tab.bloco.str.startswith("fim de ano")].copy()
    fim["bloco"] = fim["bloco"].str.replace("fim de ano: ", "")
    fim["txt"] = fim["fator"].round(2).astype(str) + np.where(fim["percentil"] <= 0.10, "↓",
                                                              np.where(fim["percentil"] >= 0.90, "↑", ""))
    print("Fim de ano: venda ÷ base por bloco (↓ abaixo do p10 das semanas comuns, ↑ acima do p90)")
    print(fim.pivot_table(index=["unidade", "serie"], columns=["bloco", "temporada"], values="txt", aggfunc="first")
          .reindex(columns=list(BLOCOS), level=0).to_string())
    fer = tab[~tab.bloco.str.startswith("fim de ano")].copy()
    fer["txt"] = fer["fator"].round(2).astype(str) + np.where(fer["percentil"] <= 0.10, "↓",
                                                              np.where(fer["percentil"] >= 0.90, "↑", ""))
    print("\nFeriados prolongados: venda ÷ base")
    print(fer.pivot_table(index=["unidade", "serie"], columns=["bloco", "temporada"], values="txt", aggfunc="first")
          .to_string())
    ver = r[r.veredito != ""]
    print("\nVereditos (as 2 ocorrências do mesmo lado):")
    print(ver[["unidade", "serie", "bloco", "n", "veredito", "fator_medio", "fator_min", "fator_max", "pct_min",
               "pct_max", "base_media"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
