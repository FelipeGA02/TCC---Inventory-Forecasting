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
    assert corpo["retrain_scheduled"] is True

    de_novo = client.post("/api/v1/upload", headers=admin, files={"file": ("fev 26.xlsx", conteudo)})
    assert de_novo.status_code == 409
    assert de_novo.json()["detail"] == "Esta planilha já foi carregada antes. Nada foi duplicado."

    indice = client.get("/api/v1/registros", headers=admin).json()
    assert indice["total_registros"] > 9000
