"""`scripts/reclassificar_produtos.py`: aplica as regras de categoria de hoje ao catálogo."""
import sys

from sqlalchemy import delete, select

from backend.infrastructure.database import ProcessingLog, Product, SessionLocal
from backend.scripts import reclassificar_produtos

CUIA = ("TESTE-CUIA", "CUIA PLAST.PRETO CBB-25")  # recipiente vazio: era Plantas diversas


def _rodar(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["reclassificar_produtos", *args])
    reclassificar_produtos.main()


def test_sem_aplicar_nao_grava_e_com_aplicar_reclassifica(client, monkeypatch):
    with SessionLocal() as db:
        antes = {p.code: (p.category_id, p.subcategory) for p in db.scalars(select(Product))}
        db.add(Product(code=CUIA[0], name=CUIA[1], category_id="plantas-diversas", subcategory="Muda e forracao"))
        db.commit()
        ultimo_log = db.scalar(select(ProcessingLog.id).order_by(ProcessingLog.id.desc()).limit(1)) or 0
    try:
        _rodar(monkeypatch)
        with SessionLocal() as db:
            assert db.get(Product, CUIA[0]).category_id == "plantas-diversas"
            assert db.scalar(select(ProcessingLog).where(ProcessingLog.id > ultimo_log)) is None

        _rodar(monkeypatch, "--aplicar")
        with SessionLocal() as db:
            cuia = db.get(Product, CUIA[0])
            assert (cuia.category_id, cuia.subcategory) == ("produtos-de-jardim", "Insumo e acessorio")
            registro = db.scalar(select(ProcessingLog).where(ProcessingLog.id > ultimo_log))
            assert registro.kind == "reclassification"
            mudou = {m["codigo"]: m for m in registro.quality["produtos_reclassificados"]}
            assert mudou[CUIA[0]]["de"] == "Plantas diversas"
            assert mudou[CUIA[0]]["para"] == "Produtos de jardim"
    finally:
        # devolve o catálogo da base sintética, que os outros testes usam
        with SessionLocal() as db:
            db.execute(delete(ProcessingLog).where(ProcessingLog.id > ultimo_log))
            db.execute(delete(Product).where(Product.code == CUIA[0]))
            for p in db.scalars(select(Product)):
                p.category_id, p.subcategory = antes[p.code]
            db.commit()
