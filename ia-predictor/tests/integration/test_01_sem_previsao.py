"""Antes do primeiro treino: o painel avisa em PT-BR; o resto das telas já funciona.

Arquivo numerado para rodar antes dos que gravam a previsão (fixture `com_previsao`).
"""


def test_painel_sem_previsao_responde_409(client, viewer):
    r = client.get("/api/v1/painel", headers=viewer)
    assert r.status_code == 409
    assert "previsão ainda não foi gerada" in r.json()["detail"]


def test_status_sem_previsao(client, viewer):
    r = client.get("/api/v1/models/status", headers=viewer)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total_models"] == 0
    assert corpo["forecast_until"] is None
    assert corpo["is_training"] is False
