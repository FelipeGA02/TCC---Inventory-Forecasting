"""Leitura da base de vendas e do calendário do banco, no formato de DataFrame que os
geradores de `training_scripts/frontend_mock/` usam (mesmos nomes de coluna da
`BaseClassificada03.csv`).

Assim o treino (`servico_previsao`) e os resumos do painel (`painel_service`) rodam sobre o
banco — SQLite local ou Neon — com o mesmo código que roda sobre os CSV do
pré-processamento.

Ficam de fora as linhas de categorias com `show_on_dashboard` falso (Serviço e taxa), como
em `carregar_base()` do gerador.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.database import CalendarDay, Category, ProcessingLog, Product, Sale, Unit
from training_scripts.frontend_mock.gerar_dados_frontend import UNIDADES
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA

_ORDEM_LOJAS = [u["id"] for u in UNIDADES]  # a ordem das telas: Jardim Canadá, Itabirito


def carregar_lojas(db: Session) -> list[dict]:
    """Lojas no formato do gerador (`id`, `nome`, `cidade`), na ordem das telas."""
    lojas = [{"id": u.id, "nome": u.name, "cidade": u.city} for u in db.scalars(select(Unit))]
    return sorted(lojas, key=lambda u: (_ORDEM_LOJAS.index(u["id"]) if u["id"] in _ORDEM_LOJAS
                                        else len(_ORDEM_LOJAS), u["nome"]))


_COLUNAS_VENDA = {
    "emissao": Sale.sale_date,
    "unit_id": Sale.unit_id,
    "doc_numero": Sale.document_number,
    "produto_cod": Sale.product_code,
    "qtdade": Sale.quantity,
    "vl_unit": Sale.unit_price,
    "vl_total": Sale.gross_amount,
    "vl_desconto": Sale.discount,
    "tot_liq": Sale.net_amount,
    "pagamento": Sale.payment_method,
    "cadastrado": Sale.is_registered_customer,
    "encomenda": Sale.is_bulk_order,
}


def _ler_vendas(db: Session, ate: date | None) -> pd.DataFrame:
    """Só as colunas de `sales` (nomes de loja e produto entram depois, pelas tabelas
    pequenas). No Postgres lê por `COPY ... TO STDOUT` em CSV: com o Neon longe, a leitura
    é limitada pela rede, e o COPY transfere metade do protocolo linha a linha (~25 s
    contra ~50 s para a base inteira)."""
    consulta = select(*[c.label(nome) for nome, c in _COLUNAS_VENDA.items()]).order_by(Sale.id)
    if ate is not None:
        consulta = consulta.where(Sale.sale_date <= ate)
    # conexão própria e curta: a sessão não fica parada no meio de uma transação durante
    # o cálculo do painel (o Neon derruba conexão ociosa)
    with db.get_bind().connect() as conn:
        if conn.dialect.name != "postgresql":
            return pd.read_sql(consulta, conn)
        sql = str(consulta.compile(conn, compile_kwargs={"literal_binds": True}))
        buf = io.BytesIO()
        cursor = conn.connection.dbapi_connection.cursor()
        try:
            with cursor.copy(f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)") as copia:
                for bloco in copia:
                    buf.write(bloco)
        finally:
            cursor.close()
    buf.seek(0)
    df = pd.read_csv(buf, dtype={"unit_id": str, "doc_numero": str, "produto_cod": str, "pagamento": str},
                     keep_default_na=False)
    for c in ("cadastrado", "encomenda"):
        df[c] = df[c].map({"t": True, "f": False})
    return df


def carregar_vendas(db: Session, ate: date | None = None) -> pd.DataFrame:
    """Vendas de produto (sem serviços), uma linha por produto de cada nota.

    Colunas: emissao, unit_id, unidade (nome da loja), doc_numero, produto_cod,
    produto_nome, qtdade, vl_unit, vl_total, vl_desconto, tot_liq, pagamento, cadastrado,
    encomenda, cat (id da categoria), categoria (rótulo da Etapa 3), categoria_fina.
    """
    lojas = pd.DataFrame([(u.id, u.name) for u in db.scalars(select(Unit))], columns=["unit_id", "unidade"])
    produtos = pd.DataFrame(
        db.execute(select(Product.code, Product.name, Category.id, Category.source_category, Product.subcategory)
                   .join(Category, Category.id == Product.category_id)
                   .where(Category.show_on_dashboard.is_(True))).all(),
        columns=["produto_cod", "produto_nome", "cat", "categoria", "categoria_fina"])
    db.commit()  # encerra a transação de leitura antes da leitura longa

    df = _ler_vendas(db, ate)
    # inner join com os produtos do painel: tira Serviço e taxa, como em `carregar_base()`
    df = df.merge(lojas, on="unit_id", how="inner").merge(produtos, on="produto_cod", how="inner")
    colunas = ["emissao", "unit_id", "unidade", "doc_numero", "produto_cod", "produto_nome", "qtdade",
               "vl_unit", "vl_total", "vl_desconto", "tot_liq", "pagamento", "cadastrado", "encomenda",
               "cat", "categoria", "categoria_fina"]
    df = df[colunas]
    df["emissao"] = pd.to_datetime(df["emissao"])
    for c in ("cadastrado", "encomenda"):
        df[c] = df[c].astype(bool)
    for c in ("qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq"):
        df[c] = df[c].astype(float)
    df["pagamento"] = df["pagamento"].fillna("")
    df["categoria_fina"] = df["categoria_fina"].fillna("")
    return df


# `processing_log.kind` da reclassificação da base (`scripts/reclassificar_encomendas.py`): não
# é planilha, fica fora da lista de arquivos carregados, mas guarda os limiares que valem.
KIND_RECLASSIFICACAO = "reclassification"


def limiares_encomenda_atuais(db: Session) -> dict[str, float]:
    """O limiar de encomenda grande de cada loja (ADR-018): o da última planilha gravada que o
    calculou, em `processing_log.quality.limiar_encomenda_un`. Loja sem limiar gravado (banco
    carregado antes do ADR-018): o limiar fixo de 2.000 un."""
    lojas = list(db.scalars(select(Unit.id)))
    limiares: dict[str, float] = {}
    for quality in db.scalars(select(ProcessingLog.quality).where(ProcessingLog.status == "done")
                              .order_by(ProcessingLog.id.desc()).limit(200)):
        for loja, valor in ((quality or {}).get("limiar_encomenda_un") or {}).items():
            limiares.setdefault(loja, float(valor))
        if all(loja in limiares for loja in lojas):
            break
    return {loja: limiares.get(loja, float(LIMIAR_QTD_VENDA)) for loja in lojas}


def carregar_calendario(db: Session) -> pd.DataFrame:
    """Calendário por loja como `calendario_diario.csv` da Etapa 10: data, unit_id,
    unidade (nome), loja_fechada, abertura_excepcional, nome_feriado, data_comemorativa."""
    consulta = (
        select(
            CalendarDay.day.label("data"),
            CalendarDay.unit_id,
            Unit.name.label("unidade"),
            CalendarDay.store_closed.label("loja_fechada"),
            CalendarDay.exceptional_opening.label("abertura_excepcional"),
            CalendarDay.holiday_name.label("nome_feriado"),
            CalendarDay.special_date_name.label("data_comemorativa"),
        )
        .join(Unit, Unit.id == CalendarDay.unit_id)
        .order_by(CalendarDay.unit_id, CalendarDay.day)
    )
    cal = pd.read_sql(consulta, db.connection())
    cal["data"] = pd.to_datetime(cal["data"])
    for c in ("loja_fechada", "abertura_excepcional"):
        cal[c] = cal[c].astype(int)
    # dia sem evento fica `None`: o gerador testa `isinstance(..., str)` para achar o evento
    for c in ("nome_feriado", "data_comemorativa"):
        cal[c] = cal[c].astype(object).where(cal[c].notna(), None)
    return cal
