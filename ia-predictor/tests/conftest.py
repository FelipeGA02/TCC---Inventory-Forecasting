"""Fixtures dos testes: um SQLite temporário com uma base sintética pequena.

`DATABASE_URL` é trocado ANTES de importar o backend (o engine nasce no import), então os
testes nunca tocam o banco do `.env` (Neon ou o SQLite de desenvolvimento). A chave do JWT e
as senhas também são dos testes: não dependem do `.env` de quem roda.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta

_PASTA = tempfile.mkdtemp(prefix="testes_api_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_PASTA, "testes.db").replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-dos-testes-0123456789abcdef0123456789"
os.environ["ADMIN_PASSWORD"] = "senha-admin-dos-testes"
os.environ["VIEWER_PASSWORD"] = "senha-viewer-dos-testes"

_IA_PREDICTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _IA_PREDICTOR not in sys.path:
    sys.path.insert(0, _IA_PREDICTOR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import insert  # noqa: E402

from backend.auth import tentativas_login  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.domain.models.trainer import ConfigTreino  # noqa: E402
from backend.infrastructure.database import (  # noqa: E402
    Base,
    CalendarDay,
    Category,
    Product,
    Sale,
    SessionLocal,
    Unit,
    engine,
)
from backend.services import cache  # noqa: E402

LOJAS = [("jardim-canada", "Jardim Canadá", "Nova Lima"), ("itabirito", "Itabirito", "Itabirito")]
CATEGORIAS = [("grama", "Grama", "Grama"), ("plantas-diversas", "Plantas diversas", "Plantas diversas"),
              ("produtos-de-jardim", "Produtos de jardim", "Produtos de jardim"),
              ("flores-de-corte", "Flores de corte", "Flores de corte")]
PRODUTOS = [("100", "GRAMA ESMERALDA M2", "grama"), ("200", "SAMAMBAIA CUIA 21", "plantas-diversas"),
            ("300", "TERRA VEGETAL 25KG", "produtos-de-jardim"), ("400", "ROSA VERMELHA DZ", "flores-de-corte"),
            ("900", "FRETE", "servico-e-taxa")]
INICIO, FIM = date(2025, 12, 1), date(2026, 2, 28)
FIM_CALENDARIO = date(2026, 3, 31)
# A base sintética tem 3 meses — menos que a janela e o histórico mínimo de produção —,
# então o treino de ponta a ponta roda com uma configuração reduzida.
# previsão de 21 dias com walk-forward de 14: a previsão final é independente do teste (ADR-021)
CONFIG_TESTE = ConfigTreino(janela_dias=30, janela_venda_dias=30, origens=3, grade_pq=(0, 1), grade_PQ=(0,), min_historico_dias=20,
                            min_dias_com_venda=10, horizonte_previsao=21, d_candidatos=(0, 1))
DIAS_PREVISAO = 21


def _dias(ini: date, fim: date):
    d = ini
    while d <= fim:
        yield d
        d += timedelta(days=1)


def _popular_base() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(Unit), [{"id": i, "name": n, "city": c} for i, n, c in LOJAS])
        conn.execute(insert(Category), [
            {"id": i, "name": n, "source_category": g, "description": "", "show_on_dashboard": True, "sort_order": k}
            for k, (i, n, g) in enumerate(CATEGORIAS)] + [
            {"id": "servico-e-taxa", "name": "Serviço e taxa", "source_category": "Servico e taxa",
             "description": "", "show_on_dashboard": False, "sort_order": 9}])
        conn.execute(insert(Product), [{"code": c, "name": n, "category_id": k, "total_sold": 0.0}
                                       for c, n, k in PRODUTOS])
        vendas, nota = [], 1
        for loja, _, _ in LOJAS:
            for d in _dias(INICIO, FIM):
                if d.weekday() == 6:
                    continue  # domingo: loja fechada
                for k, (cod, _, _) in enumerate(PRODUTOS):
                    if cod == "400" and d.weekday() != 4:
                        continue  # flores só às sextas
                    qtd = 3000.0 if (cod == "100" and d.day == 15) else float(5 + k + d.weekday())
                    vendas.append({"sale_date": d, "unit_id": loja, "document_type": "C1",
                                   "document_number": str(nota), "product_code": cod, "quantity": qtd,
                                   "unit_price": 2.0, "gross_amount": qtd * 2, "discount": 0.0,
                                   "net_amount": qtd * 2, "payment_method": "PIX",
                                   "is_registered_customer": k % 2 == 0, "is_bulk_order": qtd > 2000})
                    nota += 1
        conn.execute(insert(Sale), vendas)
        conn.execute(insert(CalendarDay), [
            {"unit_id": loja, "day": d, "store_closed": d.weekday() == 6, "exceptional_opening": False,
             "holiday_name": "Carnaval" if d == date(2026, 3, 3) else None, "special_date_name": None}
            for loja, _, _ in LOJAS for d in _dias(date(2024, 1, 1), FIM_CALENDARIO)])


@pytest.fixture(autouse=True)
def _zerar_tentativas_login():
    tentativas_login.limpar()


@pytest.fixture(scope="session")
def client():
    from backend.main import app

    _popular_base()
    cache.limpar()
    with TestClient(app) as c:
        yield c


def _token(client, email: str, senha: str) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def viewer(client):
    return _token(client, settings.VIEWER_EMAIL, settings.VIEWER_PASSWORD)


@pytest.fixture(scope="session")
def admin(client):
    return _token(client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def com_previsao(client):
    """Um treino concluído da previsão (o do serviço, com `CONFIG_TESTE`, um processo só) —
    uma vez por sessão. As telas leem o último treino concluído."""
    from backend.services import servico_previsao

    with SessionLocal() as db:
        ja_treinou = servico_previsao.ultimo_concluido(db) is not None
    if not ja_treinou:
        workers, settings.TRAINING_WORKERS = settings.TRAINING_WORKERS, 1
        try:
            job = servico_previsao.treinar_agora(trigger="manual", cfg=CONFIG_TESTE)
        finally:
            settings.TRAINING_WORKERS = workers
        assert job.status == "done", job.message
    return True
