"""Fator multiplicativo das datas comemorativas (ADR-019). Lógica pura.

O SARIMAX só conhece o dia da semana, a loja fechada e a abertura excepcional: na semana do
Dia da Mulher, do Dia das Mães, do Dia dos Namorados e do Natal ele prevê uma semana comum,
e Flores de corte vende de 1,5 a 5,7 vezes isso (`docs/prediction/08-fator_datas_comemorativas.md`).
Este módulo calcula, das vendas, quanto a semana de cada data vendeu a mais e devolve o
multiplicador da previsão de cada dia.

Fator de uma ocorrência (loja, série, data)
-------------------------------------------
Venda ÷ base, somadas nos dias de loja aberta de `DIAS_ANTES` antes da data até ela, sem
abertura excepcional (esse dia a exógena `abertura_excepcional` já explica). Base de um dia =
mediana do mesmo dia da semana nas `SEMANAS_BASE` semanas antes e depois, só com dias normais
(loja aberta, sem abertura excepcional, fora de 7 dias antes a 3 depois de qualquer data e de
20/12 a 10/01). No calendário das lojas todo feriado é loja fechada ou abertura excepcional,
então `loja_fechada` e `abertura_excepcional` bastam para achar os dias normais.

Multiplicador
-------------
O fator junta as últimas `ocorrencias` da data com as 4 semanas seguintes já vendidas (soma
da venda ÷ soma da base) e entra pela metade (`fracao`), entre 1 e `teto`:

    multiplicador = mín(teto, máx(1, 1 + fracao · (fator − 1)))

Pela metade porque, com uma ocorrência por ano, o fator muda até 2× de um ano para o outro:
no teste, o fator cheio errou para cima de 91% a 151% em Itabirito, e a metade melhorou o
total da semana nas 10 ocorrências. Nunca abaixo de 1: o teste não avaliou reduzir a
previsão. As datas vêm da regra (2º domingo de maio...), não do calendário gravado, que pode
não estar estendido para o ano do treino.

Quem chama passa só a venda conhecida antes do primeiro dia previsto: no walk-forward, a de
antes da origem — o fator não olha o período avaliado.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


def _segundo_domingo(ano: int, mes: int) -> date:
    d = date(ano, mes, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7 + 7)


REGRAS = {
    "Dia da Mulher": lambda ano: date(ano, 3, 8),
    "Dia das Mães": lambda ano: _segundo_domingo(ano, 5),
    "Dia dos Namorados": lambda ano: date(ano, 6, 12),
    "Dia dos Pais": lambda ano: _segundo_domingo(ano, 8),
    "Finados": lambda ano: date(ano, 11, 2),
    "Natal": lambda ano: date(ano, 12, 25),
}
DATAS_DE_PRESENTE = ("Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Natal")

DIAS_ANTES = 6        # semana da data: 6 dias antes até o dia
SEMANAS_BASE = 4      # base: mesmo dia da semana, 4 semanas antes e 4 depois
_PERTO_ANTES, _PERTO_DEPOIS = 7, 3  # dias perto de uma data ficam fora da base


@dataclass(frozen=True)
class Ajuste:
    """O ajuste de uma data numa previsão: os dias que levam o multiplicador e de onde ele veio."""
    evento: str
    data: pd.Timestamp
    fator: float                 # venda ÷ base nas ocorrências passadas
    multiplicador: float         # o que multiplica a previsão (fração, piso 1 e teto)
    anos: tuple[int, ...]        # anos das ocorrências usadas
    dias: tuple[pd.Timestamp, ...]

    def como_dict(self) -> dict:
        return {"evento": self.evento, "data": self.data.date().isoformat(), "fator": round(self.fator, 3),
                "multiplicador": round(self.multiplicador, 3), "anos": list(self.anos),
                "dias": [d.date().isoformat() for d in self.dias]}


def data_do_evento(evento: str, ano: int) -> pd.Timestamp:
    return pd.Timestamp(REGRAS[evento](ano))


def dias_normais(X: pd.DataFrame) -> pd.Series:
    """Dias que entram na base: loja aberta, sem abertura excepcional, longe de datas
    comemorativas e do fim de ano. `X`: exógenas do treino (`loja_fechada`, `abertura_excepcional`)."""
    idx = X.index
    perto = np.zeros(len(idx), dtype=bool)
    for ano in range(idx.min().year, idx.max().year + 1):
        for evento in REGRAS:
            d = data_do_evento(evento, ano)
            perto |= (idx >= d - pd.Timedelta(days=_PERTO_ANTES)) & (idx <= d + pd.Timedelta(days=_PERTO_DEPOIS))
    fim_de_ano = ((idx.month == 12) & (idx.day >= 20)) | ((idx.month == 1) & (idx.day <= 10))
    return pd.Series((X["loja_fechada"].values == 0) & (X["abertura_excepcional"].values == 0) & ~perto & ~fim_de_ano,
                     index=idx)


def base_mesmo_dia(y: pd.Series, normal: pd.Series) -> pd.Series:
    """Mediana do mesmo dia da semana nas `SEMANAS_BASE` semanas antes e depois, só com dias
    normais; NaN com menos de `SEMANAS_BASE` semanas disponíveis."""
    yn = y.where(normal.reindex(y.index, fill_value=False))
    passos = [7 * k for k in range(1, SEMANAS_BASE + 1)]
    lags = pd.concat([yn.shift(s) for s in passos] + [yn.shift(-s) for s in passos], axis=1)
    return lags.median(axis=1).where(lags.notna().sum(axis=1) >= SEMANAS_BASE)


def dias_da_janela(X: pd.DataFrame, data: pd.Timestamp) -> pd.DatetimeIndex:
    """Dias que levam o fator: de `DIAS_ANTES` antes até a data, loja aberta e sem abertura
    excepcional. Dia fora de `X` fica de fora."""
    dias = pd.date_range(data - pd.Timedelta(days=DIAS_ANTES), data).intersection(X.index)
    c = X.loc[dias]
    return dias[(c["loja_fechada"].values == 0) & (c["abertura_excepcional"].values == 0)]


def _venda_e_base(y: pd.Series, X: pd.DataFrame, base: pd.Series, data: pd.Timestamp) -> tuple[float, float] | None:
    """(venda, base) da semana de uma ocorrência passada, ou None se ela ainda não tem as
    semanas seguintes vendidas (a base usa as 4 semanas depois) ou não tem base."""
    if data + pd.Timedelta(days=7 * SEMANAS_BASE) > y.index.max() or data - pd.Timedelta(days=DIAS_ANTES) < y.index.min():
        return None
    b = base.reindex(dias_da_janela(X, data)).dropna()
    if b.empty or float(b.sum()) <= 0:
        return None
    return float(y.reindex(b.index).sum()), float(b.sum())


def ajustes(y: pd.Series, X: pd.DataFrame, dias: pd.DatetimeIndex, eventos: tuple[str, ...], *,
            fracao: float, teto: float, ocorrencias: int) -> list[Ajuste]:
    """Os ajustes das datas de `eventos` cuja semana cai em `dias` (os dias previstos).

    `y`: venda diária conhecida antes de `dias` (no walk-forward, antes da origem); `X`: as
    exógenas do treino, cobrindo `y` e `dias`. Data sem ocorrência passada completa, ou cujo
    multiplicador dá 1, não entra.
    """
    if not eventos or len(dias) == 0 or y.empty:
        return []
    alvos = []
    for evento in eventos:
        for ano in range(dias.min().year, dias.max().year + 1):
            d = data_do_evento(evento, ano)
            semana = dias_da_janela(X, d).intersection(dias)
            if len(semana):
                alvos.append((evento, d, semana))
    if not alvos:
        return []
    base = base_mesmo_dia(y, dias_normais(X.loc[y.index]))
    saida = []
    for evento, d, semana in alvos:
        passadas = []
        for ano in range(d.year - 1, y.index.min().year - 1, -1):
            vb = _venda_e_base(y, X, base, data_do_evento(evento, ano))
            if vb is not None:
                passadas.append((ano, *vb))
            if len(passadas) == ocorrencias:
                break
        if not passadas:
            continue
        fator = sum(v for _, v, _ in passadas) / sum(b for _, _, b in passadas)
        mult = min(teto, max(1.0, 1 + fracao * (fator - 1)))
        if mult > 1.0:
            saida.append(Ajuste(evento, d, fator, mult, tuple(sorted(a for a, _, _ in passadas)), tuple(semana)))
    return saida


def multiplicadores(dias: pd.DatetimeIndex, lista: list[Ajuste]) -> np.ndarray:
    """Multiplicador de cada dia de `dias`: o do ajuste cuja semana o contém, ou 1."""
    m = pd.Series(1.0, index=dias)
    for a in lista:
        m.loc[list(a.dias)] = a.multiplicador
    return m.values
