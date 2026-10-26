"""Dias de venda que faltariam na base depois de carregar uma planilha.

Uma semana sem planilha não dá erro: os dias dela ficam sem venda e o treino os lê como
venda zero, e o histórico da previsão mostra "vendeu 0" contra o previsto congelado. Por
isso a carga confere, antes de gravar, cada loja de `inicio` a `fim`:

  * `inicio`: o dia seguinte à última venda da loja já na base, quando ele vem antes do
    1º dia da planilha (o buraco entre a base e a planilha); senão, o 1º dia da planilha;
  * `fim`: o último dia da planilha, de qualquer loja — a loja que parou antes, ou que nem
    está na planilha, também fica para trás.

Falta o dia em que a loja estava aberta e não tem venda nem na planilha nem na base. Loja
aberta segue o calendário da loja; dia fora dele, o padrão (fechada só no domingo), como
nas exógenas do treino (`features.exogenous`).

Lógica pura: quem lê o banco e escreve as mensagens é `services.upload_service`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

_DOMINGO = 6
_UM_DIA = timedelta(days=1)


@dataclass
class DiasFaltando:
    unit_id: str
    dias: list[date]                       # dias de loja aberta sem venda, em ordem
    intervalos: list[tuple[date, date]]    # os mesmos dias, juntos quando só há loja fechada entre eles
    ultima_na_base: date | None            # última venda da loja já carregada
    na_planilha: tuple[date, date] | None  # 1º e último dia da loja na planilha


def _fechada(dia: date, calendario: dict[date, bool]) -> bool:
    return calendario.get(dia, dia.weekday() == _DOMINGO)


def _intervalos(dias: list[date], calendario: dict[date, bool]) -> list[tuple[date, date]]:
    """Junta dias seguidos de falta; dia de loja fechada no meio não separa (sábado e
    segunda formam um intervalo só)."""
    grupos: list[list[date]] = []
    for dia in dias:
        if grupos:
            anterior = grupos[-1][-1]
            entre = (anterior + _UM_DIA * i for i in range(1, (dia - anterior).days))
            if all(_fechada(d, calendario) for d in entre):
                grupos[-1].append(dia)
                continue
        grupos.append([dia])
    return [(g[0], g[-1]) for g in grupos]


def dias_faltando(na_planilha: dict[str, set[date]], ultima_na_base: dict[str, date],
                  na_base: dict[str, set[date]], calendario: dict[str, dict[date, bool]]) -> list[DiasFaltando]:
    """As lojas com dia faltando, cada uma com os dias e os intervalos.

    `na_planilha`: dias com venda de cada loja na planilha. `ultima_na_base`: última venda
    de cada loja já na base. `na_base`: dias com venda de cada loja na base dentro do
    período a conferir (basta do 1º dia da planilha em diante). `calendario`: dia → loja
    fechada, por loja. Lojas sem venda nem na base nem na planilha não entram.
    """
    todos = set().union(*na_planilha.values()) if na_planilha else set()
    if not todos:
        return []
    ini_planilha, fim = min(todos), max(todos)
    resultado = []
    for loja in sorted(set(na_planilha) | set(ultima_na_base)):
        ultima = ultima_na_base.get(loja)
        inicio = ultima + _UM_DIA if ultima is not None and ultima < ini_planilha else ini_planilha
        cal = calendario.get(loja, {})
        com_venda = na_planilha.get(loja, set()) | na_base.get(loja, set())
        dias = [d for d in (inicio + _UM_DIA * i for i in range((fim - inicio).days + 1))
                if d not in com_venda and not _fechada(d, cal)]
        if dias:
            proprios = na_planilha.get(loja)
            resultado.append(DiasFaltando(loja, dias, _intervalos(dias, cal), ultima,
                                          (min(proprios), max(proprios)) if proprios else None))
    return resultado
