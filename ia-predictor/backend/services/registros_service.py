"""Base de vendas linha a linha (tela "Conferir Dados"), consultada página a página no banco.

A tela não recebe mais a base inteira: cada requisição traz só a página visível
(`linhas`), os totais do filtro (`resumo`) ou os itens de uma nota (`itens_da_nota`). O
filtro, a busca e a ordenação são feitos no SQL — `LIMIT/OFFSET` sobre `sales` com os
nomes de produto, categoria e loja por join. `exportar()` devolve todas as linhas do filtro,
só quando a pessoa pede o arquivo.

Ficam de fora as categorias com `show_on_dashboard` falso (Serviço e taxa), como no resto
das telas. Nenhum dado pessoal sai: o cliente vira só "consumidor" ou "cadastrado".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import String, and_, case, cast, distinct, extract, func, or_, select
from sqlalchemy.orm import Session

from backend.infrastructure.database import Category, Product, Sale, Unit
from backend.services import base_vendas
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA

TAMANHO_MAXIMO = 200
SEM_PAGAMENTO = "NÃO INFORMADO"

Visao = Literal["todos", "encomendas", "cadastrados", "descontos", "devolucoes"]
Coluna = Literal["data", "loja", "nota", "produto", "categoria", "qtd", "unit", "desc", "liq", "pag",
                 "cliente", "tipo"]
VISOES: tuple[str, ...] = ("todos", "encomendas", "cadastrados", "descontos", "devolucoes")


@dataclass
class Filtros:
    """Os mesmos filtros da tela: meses, painel de filtros, busca e a aba (visão)."""
    meses: list[str] = field(default_factory=list)          # AAAA-MM; vazio = todos
    lojas: list[str] = field(default_factory=list)
    categorias: list[str] = field(default_factory=list)
    pagamentos: list[str] = field(default_factory=list)     # como a tela mostra (ex.: "Pix")
    cliente: Literal["todos", "consumidor", "cadastrado"] = "todos"
    tipo: Literal["todos", "dia", "encomenda"] = "todos"
    data_de: date | None = None
    data_ate: date | None = None
    valor_min: float | None = None
    valor_max: float | None = None
    busca: str = ""
    visao: Visao = "todos"


def nome_pagamento(bruto: str | None) -> str:
    """Forma de pagamento como a tela mostra: "PIX " → "Pix", vazio → "Não Informado"."""
    return ((bruto or "").strip() or SEM_PAGAMENTO).title()


def _num(v: float | None, casas: int = 2):
    v = round(float(v or 0), casas)
    return int(v) if v.is_integer() else v


# --------------------------------------------------------------------------- #
# Condições
# --------------------------------------------------------------------------- #
def _condicao_visao(visao: str):
    return {
        "todos": None,
        "encomendas": Sale.is_bulk_order.is_(True),
        "cadastrados": Sale.is_registered_customer.is_(True),
        "descontos": Sale.discount > 0,
        "devolucoes": or_(Sale.net_amount < 0, Sale.quantity < 0),
    }[visao]


def _pagamentos_brutos(db: Session, nomes: list[str]) -> list[str]:
    """Valores gravados em `sales.payment_method` que a tela mostra com estes nomes."""
    brutos = db.scalars(select(distinct(Sale.payment_method))).all()
    alvo = set(nomes)
    return [b for b in brutos if b is not None and nome_pagamento(b) in alvo]


def _condicoes(db: Session, f: Filtros) -> list:
    """Filtros + busca, sem a visão (as abas mostram a contagem de cada visão)."""
    c: list = [Category.show_on_dashboard.is_(True)]
    if f.meses:
        faixas = []
        for mes in f.meses:
            ini = date(int(mes[:4]), int(mes[5:7]), 1)
            fim = (ini.replace(day=28) + timedelta(days=4)).replace(day=1)
            faixas.append(and_(Sale.sale_date >= ini, Sale.sale_date < fim))
        c.append(or_(*faixas))
    if f.lojas:
        c.append(Sale.unit_id.in_(f.lojas))
    if f.categorias:
        c.append(Category.id.in_(f.categorias))
    if f.pagamentos:
        brutos = _pagamentos_brutos(db, f.pagamentos)
        sem_pagamento = SEM_PAGAMENTO.title() in f.pagamentos
        c.append(or_(Sale.payment_method.in_(brutos), Sale.payment_method.is_(None)) if sem_pagamento
                 else Sale.payment_method.in_(brutos))
    if f.cliente != "todos":
        c.append(Sale.is_registered_customer.is_(f.cliente == "cadastrado"))
    if f.tipo != "todos":
        c.append(Sale.is_bulk_order.is_(f.tipo == "encomenda"))
    if f.data_de:
        c.append(Sale.sale_date >= f.data_de)
    if f.data_ate:
        c.append(Sale.sale_date <= f.data_ate)
    if f.valor_min is not None:
        c.append(Sale.net_amount >= f.valor_min)
    if f.valor_max is not None:
        c.append(Sale.net_amount <= f.valor_max)
    termo = f.busca.strip().lower()
    if termo:
        c.append(or_(func.lower(Product.name).contains(termo, autoescape=True),
                     func.lower(Sale.product_code).contains(termo, autoescape=True),
                     Sale.document_number.contains(termo, autoescape=True)))
    return c


def _com_joins(consulta):
    return (consulta.join(Product, Product.code == Sale.product_code)
            .join(Category, Category.id == Product.category_id)
            .join(Unit, Unit.id == Sale.unit_id))


_ORDEM = {
    "data": [Sale.sale_date],
    "loja": [Unit.name],
    "nota": [func.length(Sale.document_number), Sale.document_number],  # ordem numérica
    "produto": [Product.name],
    "categoria": [Category.name],
    "qtd": [Sale.quantity],
    "unit": [Sale.unit_price],
    "desc": [Sale.discount],
    "liq": [Sale.net_amount],
    "pag": [Sale.payment_method],
    "cliente": [Sale.is_registered_customer],
    "tipo": [Sale.is_bulk_order],
}

_COLUNAS_LINHA = (Sale.id, Sale.sale_date, Sale.unit_id, Sale.document_number, Sale.product_code,
                  Product.name, Category.id, Sale.quantity, Sale.unit_price, Sale.discount,
                  Sale.net_amount, Sale.payment_method, Sale.is_registered_customer, Sale.is_bulk_order)


def _linha(r) -> dict:
    return {"id": r[0], "data": str(r[1]), "loja": r[2], "nota": r[3], "cod": r[4], "nome": r[5],
            "cat": r[6], "qtd": _num(r[7], 3), "unit": _num(r[8]), "desc": _num(r[9]),
            "liq": _num(r[10]), "pag": nome_pagamento(r[11]), "cad": bool(r[12]), "enc": bool(r[13])}


def _consulta_linhas(db: Session, f: Filtros, ordem: str | None, direcao: str):
    condicoes = _condicoes(db, f)
    visao = _condicao_visao(f.visao)
    if visao is not None:
        condicoes.append(visao)
    consulta = _com_joins(select(*_COLUNAS_LINHA)).where(*condicoes)
    colunas = _ORDEM.get(ordem or "", [])
    chaves = [c.desc() if direcao == "desc" else c.asc() for c in colunas]
    return consulta.order_by(*chaves, Sale.id)


# --------------------------------------------------------------------------- #
# Consultas da tela
# --------------------------------------------------------------------------- #
def indice(db: Session) -> dict:
    """Meses com venda (e quantas linhas por loja), lojas e formas de pagamento — o que a
    tela precisa para montar os seletores, sem nenhuma linha da base."""
    ano, mes = extract("year", Sale.sale_date), extract("month", Sale.sale_date)
    por_mes = db.execute(
        _com_joins(select(ano, mes, Sale.unit_id, func.count()))
        .where(Category.show_on_dashboard.is_(True))
        .group_by(ano, mes, Sale.unit_id)
    ).all()
    lojas = [u["id"] for u in base_vendas.carregar_lojas(db)]
    meses: dict[str, dict] = {}
    for a, m, loja, n in por_mes:
        chave = f"{int(a):04d}-{int(m):02d}"
        item = meses.setdefault(chave, {"mes": chave, "registros": 0, "por_loja": {u: 0 for u in lojas}})
        item["registros"] += n
        item["por_loja"][loja] = n
    pagamentos = sorted({nome_pagamento(p) for p in db.scalars(select(distinct(Sale.payment_method)))})
    lista = [meses[k] for k in sorted(meses)]
    return {"lojas": lojas, "pagamentos": pagamentos, "limiar_encomenda_un": LIMIAR_QTD_VENDA,
            "total_registros": sum(m["registros"] for m in lista), "meses": lista}


def linhas(db: Session, f: Filtros, ordem: str | None, direcao: str, pagina: int, tamanho: int) -> dict:
    """Uma página do filtro (na visão escolhida), já ordenada."""
    tamanho = max(1, min(tamanho, TAMANHO_MAXIMO))
    consulta = _consulta_linhas(db, f, ordem, direcao).limit(tamanho).offset((max(pagina, 1) - 1) * tamanho)
    return {"pagina": max(pagina, 1), "tamanho": tamanho, "linhas": [_linha(r) for r in db.execute(consulta)]}


def resumo(db: Session, f: Filtros) -> dict:
    """Totais do filtro numa consulta só: contagem de cada aba (sem a visão) e, na visão
    escolhida, linhas, notas distintas e as somas de quantidade, desconto e valor."""
    visao = _condicao_visao(f.visao)

    def na_visao(expr):
        return expr if visao is None else case((visao, expr))

    chave_nota = Sale.unit_id + "-" + cast(Sale.sale_date, String) + "-" + Sale.document_number
    colunas = [func.count(case((cond, 1))) if cond is not None else func.count()
               for cond in (_condicao_visao(v) for v in VISOES)]
    colunas += [func.count(distinct(na_visao(chave_nota))), func.sum(na_visao(Sale.quantity)),
                func.sum(na_visao(Sale.discount)), func.sum(na_visao(Sale.net_amount))]
    r = db.execute(_com_joins(select(*colunas)).where(*_condicoes(db, f))).one()
    por_visao = dict(zip(VISOES, (int(n) for n in r[:len(VISOES)])))
    return {"por_visao": por_visao, "registros": por_visao[f.visao], "notas": int(r[len(VISOES)] or 0),
            "quantidade": _num(r[len(VISOES) + 1], 3), "desconto": _num(r[len(VISOES) + 2]),
            "valor_liquido": _num(r[len(VISOES) + 3])}


def itens_da_nota(db: Session, loja: str, dia: date, nota: str) -> list[dict]:
    consulta = (_com_joins(select(*_COLUNAS_LINHA))
                .where(Category.show_on_dashboard.is_(True), Sale.unit_id == loja,
                       Sale.sale_date == dia, Sale.document_number == nota)
                .order_by(Sale.id))
    return [_linha(r) for r in db.execute(consulta)]


def exportar(db: Session, f: Filtros, ordem: str | None, direcao: str) -> dict:
    """Todas as linhas do filtro, em listas (metade do tamanho de objetos), para o arquivo."""
    colunas = ["data", "loja", "nota", "cod", "nome", "cat", "qtd", "unit", "desc", "liq", "pag", "cad", "enc"]
    saida = []
    for r in db.execute(_consulta_linhas(db, f, ordem, direcao)):
        d = _linha(r)
        saida.append([d[c] for c in colunas])
    return {"colunas": colunas, "linhas": saida}
