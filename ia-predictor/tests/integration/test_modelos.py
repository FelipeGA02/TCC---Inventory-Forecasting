"""Status dos modelos e treino manual (admin)."""
import time

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
