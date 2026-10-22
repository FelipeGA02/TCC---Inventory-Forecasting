"""JWT obrigatório em /api/v1/* e perfil admin em upload e treino (Princípio VI)."""
import pytest

from backend.config import settings

ROTAS_VIEWER = ["/api/v1/contexto", "/api/v1/painel", "/api/v1/analises", "/api/v1/registros",
                "/api/v1/registros/linhas", "/api/v1/registros/resumo",
                "/api/v1/models/status"]


def test_health_publico(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("rota", ROTAS_VIEWER)
def test_sem_token_responde_401_em_portugues(client, rota):
    r = client.get(rota)
    assert r.status_code == 401
    assert r.json()["detail"] == "Autenticação necessária. Faça login para continuar."


def test_token_invalido(client):
    r = client.get("/api/v1/painel", headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401


def test_login_senha_errada(client):
    r = client.post("/auth/login", json={"email": settings.VIEWER_EMAIL, "password": "errada"})
    assert r.status_code == 401
    assert r.json()["detail"] == "E-mail ou senha incorretos."


def test_refresh_e_me(client):
    r = client.post("/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    tokens = r.json()
    assert tokens["role"] == "admin"
    novo = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert novo.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {novo.json()['access_token']}"})
    assert me.json()["email"] == settings.ADMIN_EMAIL


def test_viewer_nao_envia_planilha(client, viewer):
    r = client.post("/api/v1/upload", headers=viewer, files={"file": ("jan.xlsx", b"x")})
    assert r.status_code == 403


def test_viewer_nao_dispara_treino(client, viewer):
    assert client.post("/api/v1/models/retrain", headers=viewer).status_code == 403
