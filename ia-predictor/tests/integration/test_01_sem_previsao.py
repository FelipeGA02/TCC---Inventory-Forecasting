"""Antes do primeiro treino: o painel avisa em PT-BR; o resto das telas já funciona.

Arquivo numerado para rodar antes dos que treinam a previsão (fixture `com_previsao`).
"""


def test_painel_sem_previsao_responde_409(client, viewer):
    r = client.get("/api/v1/painel", headers=viewer)
    assert r.status_code == 409
    assert "previsão ainda não foi gerada" in r.json()["detail"]
    assert "Treinar previsões" in r.json()["detail"]


def test_historico_sem_treino_responde_409(client, viewer):
    r = client.get("/api/v1/painel/historico/jardim-canada/categoria/grama", headers=viewer)
    assert r.status_code == 409
    assert "Treinar previsões" in r.json()["detail"]


def test_contexto_sem_previsao(client, viewer):
    c = client.get("/api/v1/contexto", headers=viewer).json()
    assert c["previsao"] is None
    assert c["configuracao"]["horizonte_dias"] == 14


def test_status_do_servico_antes_do_primeiro_treino(client, admin):
    s = client.get("/api/v1/servico-previsao/status", headers=admin).json()
    assert s["treino_na_api"] is True
    assert s["em_andamento"] is None and s["ultimo_concluido_em"] is None
    assert s["dados_alterados"] is True  # nunca treinou: um disparo treina
    assert (s["config"]["m"], s["config"]["d"], s["config"]["D"]) == (7, 0, 0)
    assert s["config"]["passo_dias"] == 1 and s["config"]["horizonte_dias"] == 14


def test_rotas_do_treino_antigo_sairam(client, admin):
    assert client.get("/api/v1/models/status", headers=admin).status_code == 404
    assert client.post("/api/v1/models/retrain", headers=admin).status_code == 404
