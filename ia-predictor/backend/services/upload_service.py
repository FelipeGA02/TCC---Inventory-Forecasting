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
inicial. Com venda nova, a resposta avisa que a previsão precisa ser treinada de novo
(`needs_training`): o treino é o botão "Treinar previsões" (ADR-017), não roda sozinho.

Conferência antes de gravar
---------------------------
`verificar()` passa a planilha pelas mesmas etapas e devolve o que a carga faria — período
de cada loja, vendas novas, já carregadas e ignoradas — e os dias de loja aberta que
ficariam sem venda na base (`domain.etl.cobertura`), sem gravar nada. A tela mostra isso e
a gestora confirma; a confirmação envia a planilha de novo para `processar()`, que confere
outra vez (a base pode ter mudado no meio) e grava os mesmos avisos em `processing_log`.
"""
from __future__ import annotations

import csv
import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from backend.config import settings
from backend.domain.etl.cobertura import DiasFaltando, dias_faltando
from backend.infrastructure.database import CalendarDay, Category, ProcessingLog, Product, Sale, Unit
from training_scripts.preprocessing.classificacao_03 import classificar
from training_scripts.preprocessing.extrair_base_01 import FIELDS, parse_xlsx
from training_scripts.preprocessing.remove_encomendas_06 import LIMIAR_QTD_VENDA, marcar_encomendas
from training_scripts.preprocessing.tratamento_de_dados_02 import tratar_dados

EXTENSOES = (".xlsx", ".xlsm")
SERVICO = "Servico e taxa"
CASAS_CHAVE = {"quantity": 3, "gross_amount": 2}
MAX_INTERVALOS_NO_AVISO = 5


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
    needs_training: bool = False  # venda nova: a previsão só a usa depois de "Treinar previsões"
    errors: list[str] = field(default_factory=list)


@dataclass
class VerificacaoUpload:
    """O que a carga da planilha faria, sem gravar (`verificar`)."""
    filename: str
    period_start: date
    period_end: date
    rows_new: int
    rows_duplicate: int
    rows_skipped: int
    units: list[dict]          # unit_id, unit_name, first_day, last_day, rows, last_day_loaded
    missing_days: list[dict]   # unit_id, unit_name, days, ranges [{start, end}], message
    warnings: list[str]        # avisos da leitura (linhas ignoradas); os de dias faltando vão em `missing_days`


@dataclass
class _Preparada:
    """A planilha lida, classificada e comparada com a base — tudo o que a gravação usa."""
    df: pd.DataFrame
    vendas: pd.DataFrame
    repetida: pd.Series
    cadastrados: dict
    pulados_leitura: int
    removidas: int
    ignoradas: int
    limpeza: dict
    avisos: list[str]
    faltando: list[DiasFaltando]
    ultimas_na_base: dict     # loja → última venda já carregada
    nomes_lojas: dict

    @property
    def rows_skipped(self) -> int:
        return self.pulados_leitura + self.removidas + self.ignoradas

    def avisos_faltando(self) -> list[str]:
        return [_texto_faltando(f, self.nomes_lojas[f.unit_id]) for f in self.faltando]


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


def _conferir_arquivo(db: Session, conteudo: bytes, nome: str) -> str:
    """Extensão, tamanho e planilha repetida. Devolve o SHA-256."""
    if not nome.lower().endswith(EXTENSOES):
        raise PlanilhaInvalida("Apenas arquivos .xlsx e .xlsm são aceitos.")
    if len(conteudo) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise PlanilhaGrandeDemais()
    sha = hashlib.sha256(conteudo).hexdigest()
    if db.scalar(select(ProcessingLog.id).where(ProcessingLog.file_sha256 == sha,
                                                ProcessingLog.status == "done")) is not None:
        raise PlanilhaRepetida()
    return sha


def verificar(db: Session, conteudo: bytes, nome: str) -> VerificacaoUpload:
    """Confere a planilha sem gravar nada: o que a carga faria e os dias que faltariam."""
    _conferir_arquivo(db, conteudo, nome)
    p = _preparar(db, conteudo, nome)
    db.rollback()  # só leituras: encerra a transação aberta pelas consultas
    datas = p.vendas["sale_date"]
    lojas = [{"unit_id": uid, "unit_name": p.nomes_lojas[uid], "first_day": grupo["sale_date"].min(),
              "last_day": grupo["sale_date"].max(), "rows": int(len(grupo)),
              "last_day_loaded": p.ultimas_na_base.get(uid)}
             for uid, grupo in p.vendas.groupby("unit_id")]
    return VerificacaoUpload(
        filename=nome, period_start=datas.min(), period_end=datas.max(),
        rows_new=int((~p.repetida).sum()), rows_duplicate=int(p.repetida.sum()), rows_skipped=p.rows_skipped,
        units=lojas,
        missing_days=[{"unit_id": f.unit_id, "unit_name": p.nomes_lojas[f.unit_id], "days": len(f.dias),
                       "ranges": [{"start": a, "end": b} for a, b in f.intervalos], "message": texto}
                      for f, texto in zip(p.faltando, p.avisos_faltando())],
        warnings=p.avisos)


def processar(db: Session, conteudo: bytes, nome: str, user_id: int | None) -> ResultadoUpload:
    t0 = time.time()
    sha = _conferir_arquivo(db, conteudo, nome)
    registro = ProcessingLog(kind="upload", filename=nome, file_sha256=sha, file_size_bytes=len(conteudo),
                             status="running", stage="Lendo a planilha", user_id=user_id)
    db.add(registro)
    db.commit()
    try:
        resultado = _gravar(db, registro, _preparar(db, conteudo, nome, registro))
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


def _preparar(db: Session, conteudo: bytes, nome: str, registro: ProcessingLog | None = None) -> _Preparada:
    """Etapas 1–3, loja, categoria, encomenda, duplicatas e dias faltando — sem gravar."""
    avisos = []
    with tempfile.TemporaryDirectory(prefix="upload_") as pasta:
        caminho = os.path.join(pasta, "planilha" + os.path.splitext(nome)[1].lower())
        with open(caminho, "wb") as fh:
            fh.write(conteudo)
        df, pulados_leitura, limpeza = _etapas_1_a_3(caminho, nome, pasta)
    removidas = sum(limpeza["linhas_removidas"].values())

    # ---- loja e categoria
    unidades = list(db.scalars(select(Unit)))
    lojas = {u.name: u.id for u in unidades}
    sem_loja = ~df["unidade"].isin(lojas)
    if sem_loja.any():
        empresas = sorted(df.loc[sem_loja, "empresa"].unique())
        avisos.append(f"{int(sem_loja.sum())} linha(s) de empresa sem loja cadastrada "
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
        avisos.append(f"{int(sem_categoria.sum())} linha(s) de categoria desconhecida foram ignoradas.")
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
    })

    # ---- duplicatas: só contra o que já estava gravado (mesmo período da planilha)
    if registro is not None:
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

    ultimas = dict(db.execute(select(Sale.unit_id, func.max(Sale.sale_date)).group_by(Sale.unit_id)).all())
    return _Preparada(df=df, vendas=vendas, repetida=repetida, cadastrados=cadastrados,
                      pulados_leitura=pulados_leitura, removidas=removidas,
                      ignoradas=int(sem_loja.sum()) + int(sem_categoria.sum()), limpeza=limpeza,
                      avisos=avisos, faltando=_dias_faltando(db, vendas, ultimas), ultimas_na_base=ultimas,
                      nomes_lojas={u.id: u.name for u in unidades})


def _dias_faltando(db: Session, vendas: pd.DataFrame, ultimas: dict) -> list[DiasFaltando]:
    """Os dias de loja aberta que ficariam sem venda na base com esta planilha."""
    ini, fim = vendas["sale_date"].min(), vendas["sale_date"].max()
    inicio = min([ini] + [u + timedelta(days=1) for u in ultimas.values() if u < ini])
    na_base: dict[str, set[date]] = {}
    for uid, dia in db.execute(select(Sale.unit_id, Sale.sale_date).distinct()
                               .where(Sale.sale_date.between(ini, fim))):
        na_base.setdefault(uid, set()).add(dia)
    calendario: dict[str, dict[date, bool]] = {}
    for uid, dia, fechada in db.execute(select(CalendarDay.unit_id, CalendarDay.day, CalendarDay.store_closed)
                                        .where(CalendarDay.day.between(inicio, fim))):
        calendario.setdefault(uid, {})[dia] = bool(fechada)
    na_planilha = {uid: set(g) for uid, g in vendas.groupby("unit_id")["sale_date"]}
    return dias_faltando(na_planilha, ultimas, na_base, calendario)


def _texto_faltando(f: DiasFaltando, loja: str) -> str:
    """Aviso de dias faltando de uma loja, na linguagem da tela de importação."""
    def periodo(a: date, b: date) -> str:
        return f"{a:%d/%m/%Y}" if a == b else f"{a:%d/%m/%Y} a {b:%d/%m/%Y}"

    intervalos = [periodo(a, b) for a, b in f.intervalos[:MAX_INTERVALOS_NO_AVISO]]
    if len(f.intervalos) > MAX_INTERVALOS_NO_AVISO:
        intervalos.append(f"e mais {len(f.intervalos) - MAX_INTERVALOS_NO_AVISO} período(s)")
    dias = f"{len(f.dias)} dia" + ("s" if len(f.dias) > 1 else "")
    if f.na_planilha is None:
        texto = (f"{loja}: esta planilha não traz vendas da loja, e ficariam faltando as vendas de {dias} "
                 f"com a loja aberta ({', '.join(intervalos)}).")
    else:
        texto = f"{loja}: faltam as vendas de {dias} com a loja aberta ({', '.join(intervalos)})."
    detalhes = []
    if f.ultima_na_base is not None:
        detalhes.append(f"a última venda da loja já carregada é de {f.ultima_na_base:%d/%m/%Y}")
    if f.na_planilha is not None:
        detalhes.append(f"esta planilha traz a loja de {periodo(*f.na_planilha)}")
    if detalhes:
        frase = " e ".join(detalhes)
        texto += f" {frase[0].upper()}{frase[1:]}."
    return texto


def _gravar(db: Session, registro: ProcessingLog, p: _Preparada) -> ResultadoUpload:
    resultado = ResultadoUpload(filename=registro.filename, errors=p.avisos + p.avisos_faltando())
    vendas = p.vendas.assign(import_id=registro.id)
    novas = vendas[~p.repetida]

    # ---- produtos novos e totais
    registro.stage = "Gravando vendas"
    ordenado = p.df[~p.repetida.values].sort_values("emissao")
    if len(ordenado):
        por_cod = ordenado.groupby("produto_cod").agg(
            nome=("produto_nome", "last"), category_id=("category_id", "first"),
            subcategory=("categoria_fina", lambda s: s.mode().iloc[0]), vendido=("qtdade", "sum"))
        novos = [{"code": cod, "name": r.nome, "category_id": r.category_id,
                  "subcategory": r.subcategory or None, "total_sold": round(float(r.vendido), 3)}
                 for cod, r in por_cod.iterrows() if cod not in p.cadastrados]
        if novos:
            db.execute(insert(Product), novos)
        for cod, r in por_cod.iterrows():
            if cod in p.cadastrados:
                db.execute(update(Product).where(Product.code == cod)
                           .values(name=r.nome, total_sold=Product.total_sold + round(float(r.vendido), 3)))
    if len(novas):
        db.execute(insert(Sale), novas.astype(object).where(novas.notna(), None).to_dict("records"))

    resultado.rows_added = int(len(novas))
    resultado.rows_duplicate = int(p.repetida.sum())
    resultado.rows_skipped = p.rows_skipped
    resultado.needs_training = resultado.rows_added > 0

    registro.status, registro.stage, registro.finished_at = "done", "Concluído", datetime.now()
    registro.reference_month = vendas["sale_date"].map(lambda d: d.strftime("%Y-%m")).mode().iloc[0]
    registro.rows_read = len(vendas) + p.rows_skipped
    registro.rows_added, registro.rows_duplicate = resultado.rows_added, resultado.rows_duplicate
    registro.rows_skipped = resultado.rows_skipped
    registro.quality = {"removidas_na_limpeza": p.removidas,
                        "clientes_sem_nome_corrigidos": p.limpeza["clientes_sem_nome_corrigidos"],
                        "puladas_na_leitura": p.pulados_leitura, "avisos": resultado.errors,
                        "periodo": [str(vendas["sale_date"].min()), str(vendas["sale_date"].max())],
                        "dias_faltando": {f.unit_id: [str(d) for d in f.dias] for f in p.faltando}}
    registro.message = (f"{resultado.rows_added} vendas novas, {resultado.rows_duplicate} já estavam "
                        f"carregadas")
    db.commit()
    return resultado
