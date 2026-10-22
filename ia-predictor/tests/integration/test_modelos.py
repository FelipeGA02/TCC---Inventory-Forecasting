"""Status dos modelos, treino manual (admin) e treino automático após o upload."""
import time
from datetime import datetime

import pytest
from sqlalchemy import delete

from backend.infrastructure import scheduler
from backend.infrastructure.database import ProcessingLog, RetrainHistory, SessionLocal
from backend.services import treino_service


def test_status_dos_modelos(client, viewer, com_previsao):
    r = client.get("/api/v1/models/status", headers=viewer)
    assert r.status_code == 200
    s = r.json()
    assert s["total_models"] == 2
    assert s["trained_models"] == 2
    assert s["forecast_until"] == "2026-03-14"
    assert s["skus_covered"] == 2  # o produto regular nas 2 lojas
    assert {u["unidade"] for u in s["units"]} == {"Jardim Canadá", "Itabirito"}
    assert s["units"][0]["sarimax_order"] == "(0,1,1)"
    assert s["next_retrain_at"] is not None


def test_treino_manual_inicia_em_segundo_plano(client, admin, monkeypatch):
    chamadas = []
    monkeypatch.setattr(treino_service, "treinar", lambda *a, **k: chamadas.append(k))
    r = client.post("/api/v1/models/retrain", headers=admin)
    assert r.status_code == 202
    assert "segundo plano" in r.json()["message"]
    # espera a thread chamar o treino falso antes de o monkeypatch ser desfeito
    limite = time.time() + 5
    while not chamadas and time.time() < limite:
        time.sleep(0.05)
    assert chamadas and chamadas[0]["user_id"] is not None


def test_treino_manual_em_andamento_responde_409(client, admin, monkeypatch):
    monkeypatch.setattr(treino_service, "ha_treino_rodando", lambda db: True)
    r = client.post("/api/v1/models/retrain", headers=admin)
    assert r.status_code == 409
    assert r.json()["detail"] == "Atualização já em andamento. Tente novamente em alguns minutos."


def test_nova_planilha_adia_o_treino_apos_upload(client):
    primeiro = scheduler.agendar_treino_pos_upload()
    segundo = scheduler.agendar_treino_pos_upload()
    try:
        assert primeiro is not None and segundo >= primeiro
        assert scheduler.treino_pos_upload_agendado() == segundo  # um treino só, adiado
    finally:
        scheduler._scheduler.remove_job(scheduler._JOB_POS_UPLOAD)


class _Treinou(Exception):
    pass


def test_treino_e_pulado_so_sem_planilha_nova(client, com_previsao, monkeypatch):
    def treinou(*_a, **_k):
        raise _Treinou()

    monkeypatch.setattr(treino_service.gerador, "gerar_unidade", treinou)
    # mesmas vendas e configuração do último treino, nenhuma planilha pendente: pulado
    rid = treino_service.treinar("upload", pular_sem_venda_nova=True)
    with SessionLocal() as db:
        assert db.get(RetrainHistory, rid).status == "skipped"

    # planilha com venda nova ainda não usada (ex.: completou dias antigos): treina
    with SessionLocal() as db:
        db.add(ProcessingLog(filename="jan 26.xlsx", file_sha256="x" * 64, file_size_bytes=1,
                             status="done", rows_added=5, finished_at=datetime.now()))
        db.commit()
    try:
        with pytest.raises(_Treinou):
            treino_service.treinar("upload", pular_sem_venda_nova=True)
    finally:
        with SessionLocal() as db:
            db.execute(delete(ProcessingLog).where(ProcessingLog.filename == "jan 26.xlsx"))
            db.commit()
