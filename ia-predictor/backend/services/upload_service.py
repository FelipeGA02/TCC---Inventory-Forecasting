"""Carga de uma planilha "Contas a Receber" enviada pela tela de importação.

Passa a planilha pelas mesmas etapas do pré-processamento (`training_scripts/preprocessing`):
Etapa 1 (`parse_xlsx`), Etapa 2 (`tratar_dados`: limpeza) e Etapa 3 (`classificar`: loja e
categoria), rodadas numa pasta temporária, e grava em `sales` só as linhas que ainda não
estão no banco — a chave de duplicata é a da Etapa 1 (`DUPLICATE_KEY_FIELDS`: nota,
produto, data, quantidade e valor), comparada só contra o que já estava gravado, nunca
dentro da própria planilha (o mesmo produto pode vir em duas linhas da mesma nota).

A planilha não é guardada: sobra a linha de `processing_log` (nome, SHA-256, contagens).
Produto novo entra em `products` com a categoria da Etapa 3; produto já cadastrado mantém
a categoria do cadastro. A encomenda (venda > 2.000 un. na nota) é marcada como na carga
inicial. Com venda nova, o router agenda o treino para alguns minutos depois
(`scheduler.agendar_treino_pos_upload`).
"""
from __future__ import annotations

import csv
import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from backend.config import settings
from backend.infrastructure.database import Category, ProcessingLog, Product, Sale, Unit
from training_scripts.preprocessing.classificacao_03 import classificar
from training_scripts.preprocessing.extrair_base_01 import FIELDS, parse_xlsx
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA, marcar_encomendas
from training_scripts.preprocessing.tratamento_de_dados_02 import tratar_dados

EXTENSOES = (".xlsx", ".xlsm")
SERVICO = "Servico e taxa"
CASAS_CHAVE = {"quantity": 3, "gross_amount": 2}


class PlanilhaInvalida(Exception):
    """Arquivo que não é a planilha esperada (mensagem para a loja em `args[0]`)."""


class PlanilhaRepetida(Exception):
    """O mesmo arquivo (mesmo SHA-256) já foi carregado."""


class PlanilhaGrandeDemais(Exception):
    pass


@dataclass
class ResultadoUpload:
    filename: str
    rows_added: int = 0
    rows_skipped: int = 0
    rows_duplicate: int = 0
    processing_time_seconds: float = 0.0
    retrain_scheduled: bool = False
    errors: list[str] = field(default_factory=list)


def _chave(df: pd.DataFrame) -> pd.Series:
    """Chave de duplicata da Etapa 1 com quantidade e valor arredondados (no banco são float)."""
    return pd.Series(list(zip(df["document_number"], df["product_code"], df["sale_date"],
                              df["quantity"].round(CASAS_CHAVE["quantity"]),
                              df["gross_amount"].round(CASAS_CHAVE["gross_amount"]))), index=df.index)


def _etapas_1_a_3(caminho_xlsx: str, nome: str, pasta: str) -> tuple[pd.DataFrame, int, dict]:
    """Etapas 1–3 do pré-processamento sobre uma planilha. Devolve a base classificada, as
    linhas puladas na leitura e o resumo da limpeza."""
    registros, pulados = parse_xlsx(caminho_xlsx)
    if not registros:
        raise PlanilhaInvalida(
            "Não encontramos vendas nesta planilha. Confira se é o relatório “Contas a Receber” "
            "exportado do sistema da loja.")
    base01 = os.path.join(pasta, "Base01.csv")
    with open(base01, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.DictWriter(fh, fieldnames=FIELDS, delimiter=";")
        escritor.writeheader()
        for r in registros:
            escritor.writerow({**r, "arquivo_origem": nome})
    base02 = os.path.join(pasta, "BaseFormatada02.csv")
    base03 = os.path.join(pasta, "BaseClassificada03.csv")
    limpeza = tratar_dados(input_csv=base01, output_csv=base02,
                           report_json=os.path.join(pasta, "etapa02.json"), verbose=False)
    classificar(input_csv=base02, output_csv=base03, produtos_csv=os.path.join(pasta, "produtos03.csv"),
                report_json=os.path.join(pasta, "etapa03.json"), verbose=False)
    df = pd.read_csv(base03, sep=";", dtype=str, keep_default_na=False)
    for c in ["qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq"]:
        df[c] = pd.to_numeric(df[c])
    return df, len(pulados), limpeza


def processar(db: Session, conteudo: bytes, nome: str, user_id: int | None) -> ResultadoUpload:
    t0 = time.time()
    if not nome.lower().endswith(EXTENSOES):
        raise PlanilhaInvalida("Apenas arquivos .xlsx e .xlsm são aceitos.")
    if len(conteudo) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise PlanilhaGrandeDemais()
    sha = hashlib.sha256(conteudo).hexdigest()
    if db.scalar(select(ProcessingLog.id).where(ProcessingLog.file_sha256 == sha,
                                                ProcessingLog.status == "done")) is not None:
        raise PlanilhaRepetida()

    registro = ProcessingLog(kind="upload", filename=nome, file_sha256=sha, file_size_bytes=len(conteudo),
                             status="running", stage="Lendo a planilha", user_id=user_id)
    db.add(registro)
    db.commit()
    try:
        resultado = _gravar(db, registro, conteudo, nome)
    except Exception as erro:
        db.rollback()
        registro.status, registro.finished_at = "error", datetime.now()
        registro.stage = "Erro"
        registro.message = (erro.args[0] if isinstance(erro, PlanilhaInvalida)
                            else f"{type(erro).__name__}: {erro}")[:500]
        db.commit()
        raise
    resultado.processing_time_seconds = round(time.time() - t0, 1)
    return resultado


def _gravar(db: Session, registro: ProcessingLog, conteudo: bytes, nome: str) -> ResultadoUpload:
    resultado = ResultadoUpload(filename=nome)
    with tempfile.TemporaryDirectory(prefix="upload_") as pasta:
        caminho = os.path.join(pasta, "planilha" + os.path.splitext(nome)[1].lower())
        with open(caminho, "wb") as fh:
            fh.write(conteudo)
        df, pulados_leitura, limpeza = _etapas_1_a_3(caminho, nome, pasta)
    removidas = sum(limpeza["linhas_removidas"].values())

    # ---- loja e categoria
    lojas = {u.name: u.id for u in db.scalars(select(Unit))}
    sem_loja = ~df["unidade"].isin(lojas)
    if sem_loja.any():
        empresas = sorted(df.loc[sem_loja, "empresa"].unique())
        resultado.errors.append(f"{int(sem_loja.sum())} linha(s) de empresa sem loja cadastrada "
                                f"foram ignoradas: {', '.join(empresas)}")
        df = df[~sem_loja].copy()
    if df.empty:
        raise PlanilhaInvalida("Nenhuma linha da planilha é de uma loja cadastrada.")

    categorias = {c.source_category: c.id for c in db.scalars(select(Category))}
    cadastrados = {p.code: p.category_id for p in db.scalars(select(Product))}
    df["category_id"] = [cadastrados.get(cod) or categorias.get(cat)
                         for cod, cat in zip(df["produto_cod"], df["categoria"])]
    sem_categoria = df["category_id"].isna()
    if sem_categoria.any():
        resultado.errors.append(f"{int(sem_categoria.sum())} linha(s) de categoria desconhecida foram ignoradas.")
        df = df[~sem_categoria].copy()

    # ---- encomenda (sem as linhas de serviço), como na carga inicial
    df["emissao"] = pd.to_datetime(df["emissao"])
    df["encomenda"] = False
    produto = df["categoria"] != SERVICO
    df.loc[produto, "encomenda"] = marcar_encomendas(df[produto], LIMIAR_QTD_VENDA)

    vendas = pd.DataFrame({
        "sale_date": df["emissao"].dt.date,
        "unit_id": df["unidade"].map(lojas),
        "document_type": df["doc_tipo"],
        "document_number": df["doc_numero"],
        "product_code": df["produto_cod"],
        "quantity": df["qtdade"],
        "unit_price": df["vl_unit"],
        "gross_amount": df["vl_total"],
        "discount": df["vl_desconto"],
        "net_amount": df["tot_liq"],
        "payment_method": df["pagamento"],
        "is_registered_customer": df["cliente_nome"].str.strip().str.upper() != "CONSUMIDOR",
        "is_bulk_order": df["encomenda"].astype(bool),
        "import_id": registro.id,
    })

    # ---- duplicatas: só contra o que já estava gravado (mesmo período da planilha)
    registro.stage = "Conferindo vendas já carregadas"
    db.flush()
    gravadas = pd.read_sql(
        select(Sale.document_number, Sale.product_code, Sale.sale_date, Sale.quantity, Sale.gross_amount)
        .where(Sale.sale_date.between(vendas["sale_date"].min(), vendas["sale_date"].max())),
        db.connection())
    if len(gravadas):
        gravadas["sale_date"] = pd.to_datetime(gravadas["sale_date"]).dt.date
        repetida = _chave(vendas).isin(set(_chave(gravadas)))
    else:
        repetida = pd.Series(False, index=vendas.index)
    novas = vendas[~repetida]

    # ---- produtos novos e totais
    registro.stage = "Gravando vendas"
    ordenado = df[~repetida.values].sort_values("emissao")
    if len(ordenado):
        por_cod = ordenado.groupby("produto_cod").agg(
            nome=("produto_nome", "last"), category_id=("category_id", "first"),
            subcategory=("categoria_fina", lambda s: s.mode().iloc[0]), vendido=("qtdade", "sum"))
        novos = [{"code": cod, "name": r.nome, "category_id": r.category_id,
                  "subcategory": r.subcategory or None, "total_sold": round(float(r.vendido), 3)}
                 for cod, r in por_cod.iterrows() if cod not in cadastrados]
        if novos:
            db.execute(insert(Product), novos)
        for cod, r in por_cod.iterrows():
            if cod in cadastrados:
                db.execute(update(Product).where(Product.code == cod)
                           .values(name=r.nome, total_sold=Product.total_sold + round(float(r.vendido), 3)))
    if len(novas):
        db.execute(insert(Sale), novas.astype(object).where(novas.notna(), None).to_dict("records"))

    resultado.rows_added = int(len(novas))
    resultado.rows_duplicate = int(repetida.sum())
    resultado.rows_skipped = pulados_leitura + removidas + int(sem_loja.sum()) + int(sem_categoria.sum())
    resultado.retrain_scheduled = resultado.rows_added > 0

    registro.status, registro.stage, registro.finished_at = "done", "Concluído", datetime.now()
    registro.reference_month = vendas["sale_date"].map(lambda d: d.strftime("%Y-%m")).mode().iloc[0]
    registro.rows_read = len(vendas) + removidas + pulados_leitura + int(sem_loja.sum()) + int(sem_categoria.sum())
    registro.rows_added, registro.rows_duplicate = resultado.rows_added, resultado.rows_duplicate
    registro.rows_skipped = resultado.rows_skipped
    registro.quality = {"removidas_na_limpeza": removidas,
                        "clientes_sem_nome_corrigidos": limpeza["clientes_sem_nome_corrigidos"],
                        "puladas_na_leitura": pulados_leitura, "avisos": resultado.errors}
    registro.message = (f"{resultado.rows_added} vendas novas, {resultado.rows_duplicate} já estavam "
                        f"carregadas")
    db.commit()
    return resultado
