"""Histórico da previsão: o previsto de cada dia, congelado depois que o dia passa para o modelo.

Regra: o previsto de um dia é o da última previsão feita antes dele — o número que a loja
viu na tela.

  * cada treino do serviço de previsão começa em `inicio` (dia seguinte à última venda) e
    cobre os 14 dias do horizonte: grava ou troca o previsto desses dias;
  * os dias antes de `inicio` já têm venda carregada e não mudam mais. Com o treino
    semanal, ficam congelados os dias entre um início e o seguinte (9 dias, se o treino
    seguinte vier 9 dias depois); se ele demorar mais de 14 dias, ficam os 14;
  * dia que nenhuma previsão cobriu — antes do 1º treino, ou o que passou dos 14 dias
    quando o treino seguinte demorou — vem do walk-forward desse treino, que só preenche
    dia ainda vazio. Do walk-forward entra só o 1º dia de cada janela (h = 1): as origens
    andam 1 dia, então cada dia tem um previsto só, feito com as vendas até a véspera.

Lógica pura: quem lê e grava o banco é `services.servico_previsao`. Cada ponto é um dict com
`level` ("category" | "product"), `item` (id da categoria ou código do produto), `day`
(date), `predicted`, `lower_95`, `upper_95`, `source` ("forecast" | "walk_forward") e
`origin_date` — o 1º dia da janela: o início da previsão, ou o próprio dia no walk-forward.
O horizonte de cada dia é `day − origin_date + 1`. `store_closed` guarda se o calendário
dava a loja fechada no dia quando ele foi previsto: se o calendário for corrigido depois, a
tela ainda explica por que o previsto era zero.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from backend.domain.models import datas_comemorativas

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


def pontos_da_serie(level: str, item: str, backtest: pd.DataFrame, complemento: pd.DataFrame | None,
                    previsao: pd.DataFrame, fechada: pd.Series | None = None) -> tuple[list[dict], list[dict]]:
    """(walk-forward, previsão) de uma série treinada (`ResultadoSerie` do trainer), no
    formato de `pontos_a_gravar`. Do walk-forward, o 1º dia de cada janela: o das origens
    completas (`backtest`, h = 1) e o do complemento, que vai até a véspera da previsão.
    `fechada`: loja fechada por dia (bool, índice diário), como o treino a viu. A coluna
    `fator` (datas comemorativas, ADR-019), quando existe, vira `event_factor`."""
    colunas = _COLUNAS + (["fator"] if "fator" in backtest.columns else [])
    janelas = [backtest.loc[backtest["horizonte"] == 1, colunas]]
    if complemento is not None and len(complemento):
        janelas.append(complemento[[c for c in colunas if c in complemento.columns]])
    walk_forward = [_ponto(level, item, p, "walk_forward", p.origem, fechada)
                    for p in pd.concat(janelas).sort_values("data").itertuples()]
    inicio = previsao["data"].min()
    return walk_forward, [_ponto(level, item, p, "forecast", inicio, fechada) for p in previsao.itertuples()]


def pontos_a_gravar(gravados_antes: set[Chave], walk_forward: list[dict], previsao: list[dict],
                    inicio: date) -> list[dict]:
    """Pontos a inserir depois de apagar o que estava gravado de `inicio` em diante.

    `gravados_antes`: chaves já gravadas com dia < `inicio` (congeladas). A previsão nova
    entra inteira (dias >= `inicio`); do walk-forward, só os dias < `inicio` ainda vazios.
    """
    novos = [p for p in previsao if p["day"] >= inicio]
    vistos = {chave(p) for p in novos} | gravados_antes
    for p in walk_forward:
        k = chave(p)
        if p["day"] < inicio and k not in vistos:
            novos.append(p)
            vistos.add(k)
    return novos


def serie_com_previsto(real: pd.Series,
                       previstos: dict[date, tuple[float, float, float, str, date, bool | None, float | None]]
                       ) -> list[dict]:
    """Vendido de cada dia de `real` (índice diário) com o previsto gravado: valor, faixa,
    de onde veio (`fonte`: "forecast" | "walk_forward"), a quantos dias do início da
    previsão ele estava (`horizonte`, 1 no walk-forward), se a previsão contava com a loja
    fechada (`loja_fechada`) e o ajuste da data comemorativa que entrou nele (`ajuste`:
    evento e multiplicador, ADR-019). `None` nos dias sem previsão."""
    serie = []
    for dia, vendido in real.items():
        p = previstos.get(dia.date())
        fator = p[6] if p is not None and len(p) > 6 else None
        serie.append({"data": str(dia.date()), "real": round(float(vendido), 1),
                      "previsto": None if p is None else p[0],
                      "inf": None if p is None else p[1],
                      "sup": None if p is None else p[2],
                      "fonte": None if p is None else p[3],
                      "horizonte": None if p is None else (dia.date() - p[4]).days + 1,
                      "loja_fechada": None if p is None else p[5],
                      "ajuste": None if fator is None else {"evento": datas_comemorativas.evento_do_dia(dia),
                                                            "multiplicador": round(float(fator), 3)}})
    return serie
