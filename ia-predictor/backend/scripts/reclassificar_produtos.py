"""Reclassifica os produtos do banco com as regras de categoria de hoje (Etapa 3).

O envio de planilha só classifica produto novo: o já cadastrado mantém a categoria do
cadastro. Quando as regras de `training_scripts/preprocessing/taxonomy/categorias.py` mudam
(ex.: a revisão SKU a SKU de 2026-11-04), este script aplica a regra nova a todo o catálogo
— `products.category_id` e `products.subcategory` (`categoria_fina`) — pelo código e nome do
produto, como a carga inicial faria, sem apagar vendas, treinos nem o histórico da previsão.

Grava uma linha em `processing_log` (`kind = "reclassification"`) com as mudanças. O
catálogo entra na impressão digital do treino: o próximo "Treinar previsões" treina de novo.
Produto que entra em Serviço e taxa (ou sai dele) muda o tamanho do pedido: depois deste,
rode `reclassificar_encomendas` para conferir as encomendas grandes.

Sem `--aplicar` só mostra o que mudaria.

Uso (a partir de `ia-predictor/`):
    python -m backend.scripts.reclassificar_produtos [--aplicar]
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime

from sqlalchemy import select

from backend.infrastructure.database import Category, ProcessingLog, Product, SessionLocal, create_tables, engine
from backend.services.base_vendas import KIND_RECLASSIFICACAO
from training_scripts.preprocessing.taxonomy.categorias import map_categoria, map_categoria_negocio


def log(msg: str) -> None:
    print(f"[reclassificar_produtos] {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="grava a reclassificação (sem ele, só mostra)")
    args = parser.parse_args()
    log(f"banco: {engine.url.render_as_string(hide_password=True)}")
    create_tables()
    with SessionLocal() as db:
        categorias = {c.source_category: c for c in db.scalars(select(Category))}
        por_id = {c.id: c.source_category for c in categorias.values()}
        mudancas = []
        for p in db.scalars(select(Product)):
            fina = map_categoria(p.code, p.name)
            nova = categorias[map_categoria_negocio(p.code, p.name)]
            if nova.id != p.category_id or fina != p.subcategory:
                mudancas.append((p, nova, fina))

        trocas = [(p, n, f) for p, n, f in mudancas if n.id != p.category_id]
        log(f"{len(mudancas)} produtos mudam: {len(trocas)} de categoria, "
            f"{len(mudancas) - len(trocas)} só de subcategoria")
        resumo = Counter()
        for p, n, _ in trocas:
            resumo[(por_id[p.category_id], n.source_category)] += 1
        for (de, para), qtd in resumo.most_common():
            log(f"  {de} → {para}: {qtd} produtos")
        for p, n, _ in sorted(trocas, key=lambda t: -t[0].total_sold)[:15]:
            log(f"  {p.code} {p.name} ({p.total_sold:,.0f} un.): {por_id[p.category_id]} → {n.source_category}")
        if not args.aplicar:
            log("nada gravado (use --aplicar)")
            return

        detalhe = [{"codigo": p.code, "nome": p.name, "de": por_id[p.category_id], "para": n.source_category,
                    "subcategoria_de": p.subcategory, "subcategoria_para": f} for p, n, f in mudancas]
        for p, n, f in mudancas:
            p.category_id, p.subcategory = n.id, f
        agora = datetime.now()
        db.add(ProcessingLog(
            kind=KIND_RECLASSIFICACAO, filename="Reclassificação das categorias dos produtos",
            file_sha256="", file_size_bytes=0, status="done", stage="Concluído", started_at=agora,
            finished_at=agora,
            message=f"{len(trocas)} produtos mudaram de categoria e {len(mudancas) - len(trocas)} de subcategoria",
            quality={"produtos_reclassificados": detalhe,
                     "por_troca": [{"de": de, "para": para, "produtos": q} for (de, para), q in resumo.items()]}))
        db.commit()
        log(f"{len(mudancas)} produtos atualizados e registrados em processing_log")


if __name__ == "__main__":
    main()
