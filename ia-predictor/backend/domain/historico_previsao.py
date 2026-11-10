"""Histórico da previsão: o previsto de cada dia, no registro mais antigo que o sistema fez dele.

Regra: cada dia de cada série guarda a primeira previsão gravada para ele, e ela não é mais
trocada. Cada treino concluído só grava os dias que ainda não têm registro:

  * do walk-forward, cada dia vem da janela mais antiga que o previu — a origem mais cedo,
    com o maior horizonte (até 14 dias antes, com as vendas até a véspera da origem). Os
    primeiros dias do período testado só aparecem nas primeiras janelas, com horizonte menor;
  * da previsão final, entram só os primeiros `dias_historico` dias (14: o horizonte do
    walk-forward) a partir do dia seguinte à última venda. O resto dos 91 dias previstos
    (ADR-021) fica só em `series_forecasts`;
  * com o treino semanal, os dias da semana seguinte já ficam gravados pela previsão do
    treino anterior (horizontes 1 a 14) e o walk-forward do treino novo só preenche o dia
    que nenhuma previsão cobriu — antes do 1º treino, ou quando o treino seguinte demorou
    mais de 14 dias.

Lógica pura: quem lê e grava o banco é `services.servico_previsao`. Cada ponto é um dict com
`level` ("category" | "product"), `item` (id da categoria ou código do produto), `day`
(date), `predicted`, `lower_95`, `upper_95`, `source` ("forecast" | "walk_forward") e
`origin_date` — o 1º dia da janela que previu o dia: o início da previsão, ou a origem do
walk-forward. O horizonte de cada dia é `day − origin_date + 1`. `store_closed` guarda se o
calendário dava a loja fechada no dia quando ele foi previsto: se o calendário for corrigido
depois, a tela ainda explica por que o previsto era zero.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

Chave = tuple[str, str, date]  # (nível, item, dia)
_COLUNAS = ["origem", "data", "previsto", "ic_inf", "ic_sup"]


def chave(p: dict) -> Chave:
    return p["level"], p["item"], p["day"]


def _ponto(level: str, item: str, linha, source: str, origem, fechada: pd.Series | None) -> dict:
    fator = getattr(linha, "fator", 1.0)
    fator = 1.0 if pd.isna(fator) else float(fator)
    return {"level": level, "item": item, "day": linha.data.date(), "predicted": round(float(linha.previsto), 3),
            "lower_95": round(float(linha.ic_inf), 3), "upper_95": round(float(linha.ic_sup), 3),
            "source": source, "origin_date": origem.date(),
            "store_closed": None if fechada is None or linha.data not in fechada.index else bool(fechada[linha.data]),
            "event_factor": None if fator == 1.0 else round(fator, 4)}


def mais_antigo_por_dia(backtest: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por dia do walk-forward: a da origem mais cedo (o maior horizonte)."""
    return backtest.sort_values(["data", "origem"]).drop_duplicates("data", keep="first")


def pontos_da_serie(level: str, item: str, backtest: pd.DataFrame, previsao: pd.DataFrame,
                    fechada: pd.Series | None = None, dias_historico: int = 14) -> tuple[list[dict], list[dict]]:
    """(walk-forward, previsão) de uma série treinada (`ResultadoSerie` do trainer), no
    formato de `pontos_a_gravar`: de cada dia do walk-forward, a janela mais antiga que o
    previu; da previsão, os primeiros `dias_historico` dias. `fechada`: loja fechada por dia
    (bool, índice diário), como o treino a viu. A coluna `fator` (datas comemorativas,
    ADR-019), quando existe, vira `event_factor`."""
    colunas = _COLUNAS + (["fator"] if "fator" in backtest.columns else [])
    walk_forward = [_ponto(level, item, p, "walk_forward", p.origem, fechada)
                    for p in mais_antigo_por_dia(backtest[colunas]).itertuples()]
    previsao = previsao.sort_values("data").head(dias_historico)
    inicio = previsao["data"].min()
    return walk_forward, [_ponto(level, item, p, "forecast", inicio, fechada) for p in previsao.itertuples()]


def pontos_a_gravar(gravados: set[Chave], walk_forward: list[dict], previsao: list[dict]) -> list[dict]:
    """Pontos a inserir: os dias que ainda não têm registro (`gravados`: as chaves já
    gravadas da loja). O que já está gravado é mais antigo e fica. Se o mesmo dia vier mais
    de uma vez, fica o de origem mais cedo."""
    novos: dict[Chave, dict] = {}
    for p in sorted(previsao + walk_forward, key=lambda p: (chave(p), p["origin_date"])):
        k = chave(p)
        if k not in gravados and k not in novos:
            novos[k] = p
    return list(novos.values())


def serie_com_previsto(real: pd.Series,
                       previstos: dict[date, tuple[float, float, float, str, date, bool | None]]
                       ) -> list[dict]:
    """Vendido de cada dia de `real` (índice diário) com o previsto gravado: valor, faixa,
    de onde veio (`fonte`: "forecast" | "walk_forward"), com quantos dias de antecedência ele
    foi previsto (`horizonte`: 1 = previsto na véspera, com as vendas até ela) e se a
    previsão contava com a loja fechada (`loja_fechada`). `None` nos dias sem previsão. O
    fator da data comemorativa (`event_factor`, ADR-019) é interno e não vai para a tela."""
    serie = []
    for dia, vendido in real.items():
        p = previstos.get(dia.date())
        serie.append({"data": str(dia.date()), "real": round(float(vendido), 1),
                      "previsto": None if p is None else p[0],
                      "inf": None if p is None else p[1],
                      "sup": None if p is None else p[2],
                      "fonte": None if p is None else p[3],
                      "horizonte": None if p is None else (dia.date() - p[4]).days + 1,
                      "loja_fechada": None if p is None else p[5]})
    return serie
