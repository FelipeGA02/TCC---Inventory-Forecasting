"""Carga inicial do banco a partir do pré-processamento já rodado.

Lê `training_scripts/output/` (gerado por `python -m training_scripts.preprocessing.run_all`)
e os XLSX de `data/raw/` (só para o SHA-256 e o tamanho de cada planilha) e grava, no banco
de `DATABASE_URL` (SQLite local ou Postgres no Neon):

  * `units` e `categories` (listas fixas do painel, as mesmas do gerador do frontend);
  * `users` (admin e viewer do `.env`);
  * `processing_log`: uma linha `initial_load` por planilha com linhas na base;
  * `products`: catálogo (nome mais recente, categoria, subcategoria, total vendido);
  * `sales`: uma linha por produto vendido, só com os campos que o sistema usa;
  * `calendar_days`: calendário por loja (Etapa 10).

As tabelas de previsão ficam vazias: são preenchidas pelo treino ("Treinar previsões" na
tela, ou `python -m backend.scripts.treinar_previsoes`).

Só roda com o banco vazio. `--recriar` apaga TODAS as tabelas (inclusive usuários e
previsões) e cria de novo antes da carga.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.carga_inicial [--recriar]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import pandas as pd
from sqlalchemy import func, insert, select

from backend.auth.seed_users import seed_initial_users
from backend.config import settings
from backend.infrastructure.database import (
    Base,
    CalendarDay,
    Category,
    ProcessingLog,
    Product,
    Sale,
    SessionLocal,
    Unit,
    engine,
)
from training_scripts.frontend_mock.gerar_dados_frontend import CATEGORIAS, UNIDADES
from training_scripts.preprocessing.extrair_base_01 import OUTPUT_DIR, RAW_DIR
from training_scripts.preprocessing.remove_encomendas_06 import calcular_limiares, marcar_encomendas_por_unidade

BASE_CSV = os.path.join(OUTPUT_DIR, "BaseClassificada03.csv")
CALENDARIO_CSV = os.path.join(OUTPUT_DIR, "calendario_diario.csv")
LOG_ETAPA1 = os.path.join(OUTPUT_DIR, "processamento_log.json")

SERVICO = "Servico e taxa"
CATEGORIA_SERVICO = {"id": "servico-e-taxa", "nome": "Serviço e taxa", "grupo": SERVICO,
                     "descricao": "Frete, entrega, plantio e taxas — entra na base, fica fora da previsão"}
SENHA_PADRAO = "troque_por_senha_forte"  # default de config.py
LOTE = 5_000

COLUNAS_SALES = ["sale_date", "unit_id", "document_type", "document_number", "product_code",
                 "quantity", "unit_price", "gross_amount", "discount", "net_amount",
                 "payment_method", "is_registered_customer", "is_bulk_order", "import_id"]


def log(msg: str) -> None:
    print(f"[carga_inicial] {msg}", flush=True)


def sha256_arquivo(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_base() -> tuple[pd.DataFrame, dict]:
    cols = ["doc_tipo", "doc_numero", "pagamento", "emissao", "cliente_nome", "produto_cod",
            "produto_nome", "qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq",
            "arquivo_origem", "unidade", "categoria", "categoria_fina"]
    df = pd.read_csv(BASE_CSV, sep=";", usecols=cols, dtype=str, keep_default_na=False)
    for c in ["qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq"]:
        df[c] = pd.to_numeric(df[c])
    df["emissao"] = pd.to_datetime(df["emissao"])
    # Encomenda grande: pedido acima de média + 4 desvios da quantidade de todos os pedidos
    # da loja (ADR-018), calculada sem as linhas de serviço — a mesma regra do envio de planilha.
    df["encomenda"] = False
    produto = df["categoria"] != SERVICO
    limiares = calcular_limiares(df[produto])
    df.loc[produto, "encomenda"] = marcar_encomendas_por_unidade(df[produto], limiares)
    return df, limiares


def gravar_em_lotes(conn, tabela, registros: list[dict]) -> None:
    for i in range(0, len(registros), LOTE):
        conn.execute(insert(tabela), registros[i:i + LOTE])


def gravar_vendas(conn, linhas: pd.DataFrame) -> None:
    """COPY no Postgres (uma ida ao servidor para centenas de milhares de linhas); INSERT
    em lotes nos demais bancos."""
    if conn.dialect.name == "postgresql":
        cursor = conn.connection.dbapi_connection.cursor()
        # astype(object) troca os escalares do numpy pelos tipos do Python, que o COPY sabe gravar
        nativos = linhas.astype(object).where(linhas.notna(), None).itertuples(index=False, name=None)
        with cursor.copy(f"COPY sales ({', '.join(COLUNAS_SALES)}) FROM STDIN") as copy:
            for row in nativos:
                copy.write_row(row)
        cursor.close()
    else:
        gravar_em_lotes(conn, Sale.__table__, linhas.to_dict("records"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--recriar", action="store_true",
                        help="apaga todas as tabelas (inclusive usuários e previsões) antes da carga")
    args = parser.parse_args()
    t0 = time.time()

    for caminho in (BASE_CSV, CALENDARIO_CSV, LOG_ETAPA1):
        if not os.path.exists(caminho):
            sys.exit(f"Falta {caminho}. Rode antes: python -m training_scripts.preprocessing.run_all")

    remoto = engine.dialect.name != "sqlite"
    if remoto and SENHA_PADRAO in (settings.ADMIN_PASSWORD, settings.VIEWER_PASSWORD):
        sys.exit("Defina ADMIN_PASSWORD e VIEWER_PASSWORD no ia-predictor/.env antes de carregar "
                 "um banco remoto: as senhas padrão ficariam gravadas num banco na internet.")

    log(f"banco: {engine.url.render_as_string(hide_password=True)}")
    if args.recriar:
        log("--recriar: apagando todas as tabelas")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Sale)):
            sys.exit("A tabela sales já tem dados. Use --recriar para apagar tudo e carregar de novo.")

    df, limiares = carregar_base()
    log(f"base: {len(df):,} linhas · {df['emissao'].min():%d/%m/%Y} a {df['emissao'].max():%d/%m/%Y}")

    # ---- unidades, categorias e usuários
    unidade_por_nome = {u["nome"]: u["id"] for u in UNIDADES}
    categorias = CATEGORIAS + [CATEGORIA_SERVICO]
    categoria_por_nome = {c["grupo"]: c["id"] for c in categorias}
    faltando = (set(df["unidade"]) - set(unidade_por_nome)) | (set(df["categoria"]) - set(categoria_por_nome))
    if faltando:
        sys.exit(f"Valores sem cadastro em units/categories: {sorted(faltando)}")

    with engine.begin() as conn:
        conn.execute(insert(Unit), [{"id": u["id"], "name": u["nome"], "city": u["cidade"]} for u in UNIDADES])
        conn.execute(insert(Category), [
            {"id": c["id"], "name": c["nome"], "source_category": c["grupo"], "description": c["descricao"],
             "show_on_dashboard": c["grupo"] != SERVICO, "sort_order": i}
            for i, c in enumerate(categorias)])
    seed_initial_users()
    log(f"{len(UNIDADES)} lojas, {len(categorias)} categorias e usuários do .env")

    # ---- uma linha de processing_log por planilha que deixou linhas na base
    with open(LOG_ETAPA1, encoding="utf-8") as fh:
        etapa1 = json.load(fh)["arquivos_processados"]
    por_arquivo = df.groupby("arquivo_origem")
    import_id = {}
    with SessionLocal() as db:
        for nome, linhas in sorted(por_arquivo, key=lambda kv: kv[1]["emissao"].min()):
            caminho = os.path.join(RAW_DIR, nome)
            info = etapa1.get(nome, {})
            extraidas = info.get("registros_adicionados", len(linhas))
            removidas = max(0, extraidas - len(linhas))  # tiradas na limpeza (Etapa 2)
            registro = ProcessingLog(
                kind="initial_load", filename=nome,
                file_sha256=sha256_arquivo(caminho) if os.path.exists(caminho) else info.get("hash", ""),
                file_size_bytes=os.path.getsize(caminho) if os.path.exists(caminho) else 0,
                reference_month=linhas["emissao"].dt.strftime("%Y-%m").mode().iloc[0],
                status="done", stage="Concluído", finished_at=pd.Timestamp.now().to_pydatetime(),
                rows_read=extraidas + info.get("duplicatas_encontradas", 0) + info.get("registros_pulados", 0),
                rows_added=len(linhas), rows_duplicate=info.get("duplicatas_encontradas", 0),
                rows_skipped=info.get("registros_pulados", 0) + removidas,
                quality={"removidas_na_limpeza": removidas,
                         "limiar_encomenda_un": {unidade_por_nome[u]: round(v, 1) for u, v in limiares.items()}},
            )
            db.add(registro)
            db.flush()
            import_id[nome] = registro.id
        db.commit()
    log(f"{len(import_id)} planilhas em processing_log")

    # ---- produtos: nome mais recente, categoria e subcategoria (fixas por código na Etapa 3)
    ordenado = df.sort_values("emissao")
    prod = ordenado.groupby("produto_cod").agg(
        nome=("produto_nome", "last"), categoria=("categoria", "first"),
        subcategory=("categoria_fina", lambda s: s.mode().iloc[0]), total_sold=("qtdade", "sum"))
    produtos = [{"code": cod, "name": r.nome, "category_id": categoria_por_nome[r.categoria],
                 "subcategory": r.subcategory or None, "total_sold": round(float(r.total_sold), 3)}
                for cod, r in prod.iterrows()]
    with engine.begin() as conn:
        gravar_em_lotes(conn, Product.__table__, produtos)
    log(f"{len(produtos):,} produtos")

    # ---- vendas
    vendas = pd.DataFrame({
        "sale_date": df["emissao"].dt.date,
        "unit_id": df["unidade"].map(unidade_por_nome),
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
        "import_id": df["arquivo_origem"].map(import_id),
    })[COLUNAS_SALES]
    t1 = time.time()
    with engine.begin() as conn:
        gravar_vendas(conn, vendas)
    log(f"{len(vendas):,} vendas ({vendas['is_bulk_order'].sum():,} linhas de encomendas grandes; pedido acima de "
        + ", ".join(f"{u} {v:,.0f} un." for u, v in limiares.items()) + ") "
        f"em {time.time() - t1:.0f}s")

    # ---- calendário
    cal = pd.read_csv(CALENDARIO_CSV, sep=";", dtype={"nome_feriado": str, "data_comemorativa": str},
                      keep_default_na=False)
    dias = [{"unit_id": unidade_por_nome[r.unidade], "day": pd.Timestamp(r.data).date(),
             "store_closed": bool(r.loja_fechada), "exceptional_opening": bool(r.abertura_excepcional),
             "holiday_name": r.nome_feriado or None, "special_date_name": r.data_comemorativa or None}
            for r in cal.itertuples()]
    with engine.begin() as conn:
        gravar_em_lotes(conn, CalendarDay.__table__, dias)
    log(f"{len(dias):,} dias de calendário ({cal['data'].min()} a {cal['data'].max()})")

    # ---- conferência
    with SessionLocal() as db:
        n_sales = db.scalar(select(func.count()).select_from(Sale))
        soma = db.scalar(select(func.sum(Sale.quantity)))
    if n_sales != len(df) or abs(soma - df["qtdade"].sum()) > 0.01:
        sys.exit(f"Conferência falhou: banco {n_sales:,} linhas / {soma:,.2f} un., "
                 f"base {len(df):,} linhas / {df['qtdade'].sum():,.2f} un.")
    log(f"conferência ok: {n_sales:,} linhas e {soma:,.1f} un. iguais à base · total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
