"""Histórico da previsão: o previsto de cada dia, congelado depois que o dia passa para o modelo.

Regra: o previsto de um dia é o da última previsão feita antes dele — o número que a loja
viu na tela.

  * cada geração começa em `inicio` (dia seguinte à última venda do treino) e cobre os 14
    dias do horizonte: grava ou troca o previsto desses dias;
  * os dias antes de `inicio` já têm venda carregada e não mudam mais;
  * dia que nenhuma geração cobriu — desde a data fixa de treino até a 1ª geração, ou
    porque as vendas chegaram com mais de 14 dias de atraso — vem do walk-forward do treino,
    que só preenche dia ainda vazio. O horizonte não aumenta: o walk-forward prevê esses
    dias com o que se sabia antes de cada rodada.

Lógica pura: quem lê e grava o banco é `services.treino_service`. Cada ponto é um dict com
`level` ("category" | "product"), `item` (id da categoria ou código do produto), `day`
(date), `predicted`, `lower_95`, `upper_95` e o que mais a tabela guardar.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

Chave = tuple[str, str, date]  # (nível, item, dia)


def chave(p: dict) -> Chave:
    return p["level"], p["item"], p["day"]


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


def serie_com_previsto(real: pd.Series, previstos: dict[date, tuple[float, float, float]]) -> list[dict]:
    """Vendido de cada dia de `real` (índice diário) com o previsto e a faixa gravados —
    `None` nos dias sem previsão (antes da data fixa de treino)."""
    serie = []
    for dia, vendido in real.items():
        p = previstos.get(dia.date())
        serie.append({"data": str(dia.date()), "real": round(float(vendido), 1),
                      "previsto": None if p is None else p[0],
                      "inf": None if p is None else p[1],
                      "sup": None if p is None else p[2]})
    return serie
