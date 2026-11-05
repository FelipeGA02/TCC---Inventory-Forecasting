"""Fator multiplicativo das datas comemorativas e da queda de fim de ano (ADR-019). Lógica pura.

O SARIMAX só conhece o dia da semana, a loja fechada e a abertura excepcional. Na semana do
Dia da Mulher, do Dia das Mães, do Dia dos Namorados, do Natal e do Ano Novo ele prevê uma
semana comum, e Flores de corte vende de 1,6 a 5,8 vezes isso. De 26 a 31/12 e na semana do
Dia do Trabalho, a Grama, as Plantas diversas e os Produtos de jardim vendem de 0,3 a 0,7 de
uma semana comum, e o modelo prevê de 2 a 5 vezes o vendido
(`docs/prediction/08-fator_datas_comemorativas.md`). Este módulo calcula, das vendas, quanto
a semana de cada data vendeu a mais ou a menos e devolve o multiplicador da previsão de cada dia.

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
da venda ÷ soma da base) e entra com a `fracao`, entre `piso` e `teto`:

    multiplicador = mín(teto, máx(piso, 1 + fracao · (fator − 1)))

Duas regras (`Regra`), uma para cada sentido:
  * **alta** (`REGRA_ALTA`, Flores de corte): metade do aumento, entre 1 e 3. Pela metade
    porque, com uma ocorrência por ano, o fator muda até 2× de um ano para o outro: no teste,
    o fator cheio errou para cima de 87% a 159% em Itabirito, e a metade melhorou o total da
    semana nas 10 ocorrências.
  * **queda** (`REGRA_QUEDA`, as outras séries): a queda inteira, entre 0,2 e 1, só com pelo
    menos `min_ocorrencias` (2) ocorrências passadas e cada uma das usadas (até 3) em até
    `limite` (0,8) de uma semana comum — o critério do EDA (doc 08 §9.3). Inteira porque o
    fator da queda muda pouco de um ano para o outro, e no teste a inteira venceu a metade em
    todas as ocorrências do Ano Novo. Série que caiu num ano e não no outro fica sem ajuste.
As datas vêm da regra (2º domingo de maio...), não do calendário gravado, que pode não estar
estendido para o ano do treino.

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
    # 1º de janeiro (loja fechada): a janela fica de 26 a 31/12
    "Ano Novo": lambda ano: date(ano, 1, 1),
    "Dia do Trabalho": lambda ano: date(ano, 5, 1),
}
DATAS_DE_PRESENTE = ("Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Natal")
DATAS_FLORES_DE_CORTE = DATAS_DE_PRESENTE + ("Ano Novo",)  # a alta (doc 08 §5 e §9.2)
DATAS_DE_QUEDA = ("Ano Novo", "Dia do Trabalho")          # a queda (doc 08 §9.3)


@dataclass(frozen=True)
class Regra:
    """Como o fator das ocorrências passadas vira multiplicador."""
    fracao: float                 # parte do aumento (ou da queda) que entra na previsão
    piso: float                   # multiplicador mínimo
    teto: float                   # multiplicador máximo
    ocorrencias: int = 3          # últimas ocorrências da data que entram no fator
    min_ocorrencias: int = 1      # com menos ocorrências passadas completas, sem ajuste
    limite: float | None = None   # cada ocorrência tem de ficar em até isso (só a queda)


REGRA_ALTA = Regra(fracao=0.5, piso=1.0, teto=3.0)
REGRA_QUEDA = Regra(fracao=1.0, piso=0.2, teto=1.0, min_ocorrencias=2, limite=0.8)

DIAS_ANTES = 6        # semana da data: 6 dias antes até o dia
SEMANAS_BASE = 4      # base: mesmo dia da semana, 4 semanas antes e 4 depois
_PERTO_ANTES, _PERTO_DEPOIS = 7, 3  # dias perto de uma data ficam fora da base


@dataclass(frozen=True)
class Ajuste:
    """O ajuste de uma data numa previsão: os dias que levam o multiplicador e de onde ele veio."""
    evento: str
    data: pd.Timestamp
    fator: float                 # venda ÷ base nas ocorrências passadas
    multiplicador: float         # o que multiplica a previsão (fração, piso e teto da regra)
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


def ajustes(y: pd.Series, X: pd.DataFrame, dias: pd.DatetimeIndex, eventos: tuple[str, ...],
            regra: Regra) -> list[Ajuste]:
    """Os ajustes das datas de `eventos` cuja semana cai em `dias` (os dias previstos).

    `y`: venda diária conhecida antes de `dias` (no walk-forward, antes da origem); `X`: as
    exógenas do treino, cobrindo `y` e `dias`. Data com menos de `regra.min_ocorrencias`
    ocorrências passadas completas, com uma acima de `regra.limite` ou cujo multiplicador dá 1
    não entra.
    """
    if not eventos or len(dias) == 0 or y.empty:
        return []
    alvos = []
    for evento in eventos:
        # + 1: a semana do Ano Novo do ano seguinte cai no fim de dezembro
        for ano in range(dias.min().year, dias.max().year + 2):
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
            if len(passadas) == regra.ocorrencias:
                break
        if not passadas or len(passadas) < regra.min_ocorrencias:
            continue
        if regra.limite is not None and any(v > regra.limite * b for _, v, b in passadas):
            continue
        fator = sum(v for _, v, _ in passadas) / sum(b for _, _, b in passadas)
        mult = min(regra.teto, max(regra.piso, 1 + regra.fracao * (fator - 1)))
        if mult != 1.0:
            saida.append(Ajuste(evento, d, fator, mult, tuple(sorted(a for a, _, _ in passadas)), tuple(semana)))
    return saida


def evento_do_dia(dia: date | pd.Timestamp,
                  eventos: tuple[str, ...] = DATAS_FLORES_DE_CORTE + DATAS_DE_QUEDA) -> str | None:
    """A data de `eventos` cuja semana (de `DIAS_ANTES` antes até ela) contém `dia`, ou None —
    para dizer na tela de qual data veio um ajuste gravado (`forecast_history.event_factor`).
    As semanas das datas de `DATAS_FLORES_DE_CORTE` e `DATAS_DE_QUEDA` não se cruzam."""
    dia = pd.Timestamp(dia).normalize()
    for evento in dict.fromkeys(eventos):
        for ano in (dia.year, dia.year + 1):
            d = data_do_evento(evento, ano)
            if d - pd.Timedelta(days=DIAS_ANTES) <= dia <= d:
                return evento
    return None


def multiplicadores(dias: pd.DatetimeIndex, lista: list[Ajuste]) -> np.ndarray:
    """Multiplicador de cada dia de `dias`: o do ajuste cuja semana o contém, ou 1."""
    m = pd.Series(1.0, index=dias)
    for a in lista:
        m.loc[list(a.dias)] = a.multiplicador
    return m.values
