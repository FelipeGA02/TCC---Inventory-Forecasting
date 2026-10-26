"""JWT obrigatório em /api/v1/* e perfil admin em upload e treino (Princípio VI)."""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from backend.auth import tentativas_login
from backend.config import settings

ROTAS_VIEWER = ["/api/v1/contexto", "/api/v1/painel", "/api/v1/analises", "/api/v1/registros",
                "/api/v1/registros/linhas", "/api/v1/registros/resumo",
                "/api/v1/painel/historico/jardim-canada/categoria/grama"]


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


def test_login_bloqueia_depois_de_5_senhas_erradas(client):
    errada = {"email": settings.VIEWER_EMAIL, "password": "errada"}
    for _ in range(tentativas_login.MAX_POR_EMAIL_E_IP):
        assert client.post("/auth/login", json=errada).status_code == 401

    certa = client.post("/auth/login", json={"email": settings.VIEWER_EMAIL, "password": settings.VIEWER_PASSWORD})
    assert certa.status_code == 429
    assert certa.json()["detail"] == "Muitas tentativas com senha errada. Tente de novo em 15 minutos."
    assert 0 < int(certa.headers["Retry-After"]) <= tentativas_login.JANELA_SEGUNDOS

    outro = client.post("/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    assert outro.status_code == 200


def test_logout_encerra_a_renovacao(client):
    r = client.post("/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    refresh = r.json()["refresh_token"]
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 200

    assert client.post("/auth/logout", json={"refresh_token": refresh}).status_code == 204
    depois = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert depois.status_code == 401
    assert depois.json()["detail"] == "Sessão expirada. Faça login novamente."
    assert client.post("/auth/logout", json={"refresh_token": refresh}).status_code == 204


def test_logout_com_token_invalido_responde_204(client):
    assert client.post("/auth/logout", json={"refresh_token": "abc"}).status_code == 204


def test_refresh_sem_identificador_e_recusado(client):
    """Tokens emitidos antes do logout existir não têm `jti` e não podem ser revogados."""
    antigo = jwt.encode({"sub": "1", "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert client.post("/auth/refresh", json={"refresh_token": antigo}).status_code == 401


def test_viewer_nao_envia_planilha(client, viewer):
    r = client.post("/api/v1/upload", headers=viewer, files={"file": ("jan.xlsx", b"x")})
    assert r.status_code == 403


def test_viewer_nao_dispara_treino(client, viewer):
    assert client.post("/api/v1/servico-previsao/treinos", headers=viewer).status_code == 403
