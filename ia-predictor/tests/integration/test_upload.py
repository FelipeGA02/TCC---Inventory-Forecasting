"""Envio de planilha (admin). Roda por último: a planilha real muda a base de teste."""
import io
import os

import openpyxl
import pytest

PLANILHA_REAL = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "fev 26.xlsx")


def test_upload_recusa_arquivo_que_nao_e_planilha(client, admin):
    r = client.post("/api/v1/upload", headers=admin, files={"file": ("vendas.csv", b"a;b")})
    assert r.status_code == 400
    assert r.json()["detail"] == "Apenas arquivos .xlsx e .xlsm são aceitos."


def test_upload_recusa_arquivo_acima_do_limite(client, admin, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    r = client.post("/api/v1/upload", headers=admin,
                    files={"file": ("grande.xlsx", b"0" * (1024 * 1024 + 10))})
    assert r.status_code == 413


def test_upload_recusa_xlsx_sem_vendas(client, admin):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "outra coisa"
    buf = io.BytesIO()
    wb.save(buf)
    r = client.post("/api/v1/upload", headers=admin, files={"file": ("vazia.xlsx", buf.getvalue())})
    assert r.status_code == 400
    assert "Não encontramos vendas" in r.json()["detail"]


@pytest.mark.skipif(not os.path.exists(PLANILHA_REAL), reason="planilha real de data/raw/ ausente")
def test_upload_planilha_real_grava_so_uma_vez(client, admin):
    with open(PLANILHA_REAL, "rb") as fh:
        conteudo = fh.read()
    r = client.post("/api/v1/upload", headers=admin, files={"file": ("fev 26.xlsx", conteudo)})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["rows_added"] > 9000
    assert corpo["rows_duplicate"] == 0
    assert corpo["needs_training"] is True  # venda nova: a previsão só a usa depois de treinar
    assert "retrain_at" not in corpo  # o treino não roda sozinho (ADR-017)

    de_novo = client.post("/api/v1/upload", headers=admin, files={"file": ("fev 26.xlsx", conteudo)})
    assert de_novo.status_code == 409
    assert de_novo.json()["detail"] == "Esta planilha já foi carregada antes. Nada foi duplicado."

    indice = client.get("/api/v1/registros", headers=admin).json()
    assert indice["total_registros"] > 9000


# --------------------------------------------------------------------------- #
# Conferência antes de gravar: dias faltando entre a base e a planilha
# --------------------------------------------------------------------------- #
# A base sintética do `conftest` vai até sábado, 28/02/2026. A planilha falsa traz 05 a
# 07/03: com o domingo 01/03 fechado, faltam 02, 03 e 04/03 nas duas lojas.
from datetime import date, timedelta  # noqa: E402

import pandas as pd  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

from backend.infrastructure.database import ProcessingLog, Sale, SessionLocal  # noqa: E402
from backend.services import upload_service  # noqa: E402

MSG_FALTANDO = "faltam as vendas de 3 dias com a loja aberta (02/03/2026 a 04/03/2026)"


def _planilha_classificada(dias: list[date], lojas=("Jardim Canadá", "Itabirito")) -> pd.DataFrame:
    """A saída das Etapas 1–3 para uma planilha com uma venda de grama por loja e dia."""
    linhas = [{"doc_tipo": "C1", "doc_numero": f"T{d:%m%d}{i}", "pagamento": "PIX", "emissao": str(d),
               "cliente_nome": "CONSUMIDOR", "empresa": loja, "unidade": loja, "produto_cod": "100",
               "produto_nome": "GRAMA ESMERALDA M2", "categoria": "Grama", "categoria_fina": "Grama esmeralda",
               "qtdade": 10.0, "vl_unit": 2.0, "vl_total": 20.0, "vl_desconto": 0.0, "tot_liq": 20.0}
              for d in dias for i, loja in enumerate(lojas)]
    return pd.DataFrame(linhas)


@pytest.fixture
def planilha_marco(monkeypatch):
    df = _planilha_classificada([date(2026, 3, 5) + timedelta(days=i) for i in range(3)])
    monkeypatch.setattr(upload_service, "_etapas_1_a_3",
                        lambda *a: (df.copy(), 0, {"linhas_removidas": {}, "clientes_sem_nome_corrigidos": 0}))
    return {"file": ("marco 26.xlsx", b"planilha de teste: 05 a 07/03/2026")}


def _contagens():
    with SessionLocal() as db:
        return (db.scalar(select(func.count()).select_from(Sale)),
                db.scalar(select(func.count()).select_from(ProcessingLog)))


def test_conferencia_avisa_os_dias_faltando_sem_gravar(client, admin, planilha_marco):
    antes = _contagens()
    r = client.post("/api/v1/upload/verificacao", headers=admin, files=planilha_marco)
    assert r.status_code == 200, r.text
    v = r.json()
    assert (v["period_start"], v["period_end"]) == ("2026-03-05", "2026-03-07")
    assert v["rows_new"] == 6 and v["rows_duplicate"] == 0
    assert {(u["unit_id"], u["last_day_loaded"]) for u in v["units"]} == {
        ("jardim-canada", "2026-02-28"), ("itabirito", "2026-02-28")}
    assert {(m["unit_id"], m["days"]) for m in v["missing_days"]} == {("jardim-canada", 3), ("itabirito", 3)}
    assert v["missing_days"][0]["ranges"] == [{"start": "2026-03-02", "end": "2026-03-04"}]
    ita = next(m for m in v["missing_days"] if m["unit_id"] == "itabirito")
    assert ita["message"] == (f"Itabirito: {MSG_FALTANDO}. A última venda da loja já carregada é de "
                              "28/02/2026 e esta planilha traz a loja de 05/03/2026 a 07/03/2026.")
    assert v["warnings"] == []  # nenhuma linha ignorada na leitura
    assert _contagens() == antes  # nada gravado, nem a linha da planilha


def test_conferencia_so_para_admin(client, viewer, planilha_marco):
    assert client.post("/api/v1/upload/verificacao", headers=viewer, files=planilha_marco).status_code == 403


def test_planilha_que_continua_a_base_nao_tem_aviso(client, admin, monkeypatch):
    df = _planilha_classificada([date(2026, 3, 2), date(2026, 3, 3)])  # segunda e terça depois da base
    monkeypatch.setattr(upload_service, "_etapas_1_a_3",
                        lambda *a: (df, 0, {"linhas_removidas": {}, "clientes_sem_nome_corrigidos": 0}))
    v = client.post("/api/v1/upload/verificacao", headers=admin,
                    files={"file": ("semana.xlsx", b"continua a base")}).json()
    assert v["missing_days"] == [] and v["warnings"] == []


def test_confirmar_grava_e_registra_o_aviso(client, admin, planilha_marco):
    r = client.post("/api/v1/upload", headers=admin, files=planilha_marco)
    assert r.status_code == 200, r.text
    try:
        assert r.json()["rows_added"] == 6
        assert any(MSG_FALTANDO in e for e in r.json()["errors"])
        with SessionLocal() as db:
            log = db.scalar(select(ProcessingLog).order_by(ProcessingLog.id.desc()))
            assert log.filename == "marco 26.xlsx" and log.status == "done"
            assert log.quality["periodo"] == ["2026-03-05", "2026-03-07"]
            assert log.quality["dias_faltando"]["itabirito"] == ["2026-03-02", "2026-03-03", "2026-03-04"]
            assert any(MSG_FALTANDO in a for a in log.quality["avisos"])
        # a mesma planilha é recusada já na conferência
        de_novo = client.post("/api/v1/upload/verificacao", headers=admin, files=planilha_marco)
        assert de_novo.status_code == 409
    finally:
        with SessionLocal() as db:
            log = db.scalar(select(ProcessingLog).where(ProcessingLog.filename == "marco 26.xlsx"))
            db.execute(delete(Sale).where(Sale.import_id == log.id))
            db.delete(log)
            db.commit()


# --------------------------------------------------------------------------- #
# Encomenda grande: média + 4 desvios da quantidade dos pedidos da loja (ADR-018)
# --------------------------------------------------------------------------- #
# Na base sintética os pedidos têm de 5 a 15 un., mais um de 3.000 m² de grama por loja no
# dia 15 de cada mês (marcados como encomenda grande no conftest).


def _enviar(client, admin, monkeypatch, df: pd.DataFrame, nome: str):
    monkeypatch.setattr(upload_service, "_etapas_1_a_3",
                        lambda *a: (df.copy(), 0, {"linhas_removidas": {}, "clientes_sem_nome_corrigidos": 0}))
    r = client.post("/api/v1/upload", headers=admin, files={"file": (nome, nome.encode())})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        log = db.scalar(select(ProcessingLog).where(ProcessingLog.filename == nome))
        marcadas = dict(db.execute(select(Sale.document_number, Sale.is_bulk_order)
                                   .where(Sale.import_id == log.id)).all())
        return log, marcadas


def _apagar(*nomes: str) -> None:
    with SessionLocal() as db:
        for nome in nomes:
            log = db.scalar(select(ProcessingLog).where(ProcessingLog.filename == nome))
            if log is not None:
                db.execute(delete(Sale).where(Sale.import_id == log.id))
                db.delete(log)
        db.commit()


def test_pedido_acima_de_4_desvios_da_loja_e_encomenda_grande(client, admin, monkeypatch):
    df = _planilha_classificada([date(2026, 3, 2)], lojas=("Itabirito",))
    obra = df.iloc[[0]].assign(doc_numero="OBRA1", qtdade=5000.0, vl_total=10000.0, tot_liq=10000.0)
    try:
        log, marcadas = _enviar(client, admin, monkeypatch, pd.concat([df, obra], ignore_index=True), "obra.xlsx")
        assert marcadas == {"T03020": False, "OBRA1": True}
        assert set(log.quality["limiar_encomenda_un"]) == {"jardim-canada", "itabirito"}
        assert log.quality["limiar_encomenda_un"]["itabirito"] < 5000
        assert log.quality["linhas_de_encomenda_grande"] == 1
        contexto = client.get("/api/v1/contexto", headers=admin).json()
        assert contexto["configuracao"]["limiares_encomenda_un"] == log.quality["limiar_encomenda_un"]
    finally:
        _apagar("obra.xlsx")


def test_planilha_nova_recalcula_o_limiar_e_nao_remarca_a_base(client, admin, monkeypatch):
    """Um pedido de 100 mil un. sobe o limiar de Itabirito para mais de 3.000: os pedidos de
    3.000 m² já gravados continuam encomenda grande, e um de 3.000 que chega depois não é."""
    tres_mil_gravados = (Sale.quantity == 3000.0) & Sale.import_id.is_(None)
    with SessionLocal() as db:
        antes = list(db.scalars(select(Sale.is_bulk_order).where(tres_mil_gravados)))
    assert antes and all(antes)
    try:
        enorme = _planilha_classificada([date(2026, 3, 2)], lojas=("Itabirito",)).assign(qtdade=100_000.0)
        log, marcadas = _enviar(client, admin, monkeypatch, enorme, "enorme.xlsx")
        assert list(marcadas.values()) == [True]
        assert log.quality["limiar_encomenda_un"]["itabirito"] > 3000

        depois = _planilha_classificada([date(2026, 3, 3)], lojas=("Itabirito",)).assign(qtdade=3000.0)
        _, marcadas = _enviar(client, admin, monkeypatch, depois, "depois.xlsx")
        assert list(marcadas.values()) == [False]
        with SessionLocal() as db:
            assert list(db.scalars(select(Sale.is_bulk_order).where(tres_mil_gravados))) == antes
    finally:
        _apagar("enorme.xlsx", "depois.xlsx")
