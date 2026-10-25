"""Limite de senhas erradas no login (`backend/auth/tentativas_login.py`)."""
import pytest

from backend.auth import tentativas_login as t

EMAIL = "gestora@floricultura.com"


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(t.time, "monotonic", lambda: agora[0])
    return agora


def test_bloqueia_o_mesmo_email_e_ip_na_quinta_falha(relogio):
    for _ in range(t.MAX_POR_EMAIL_E_IP - 1):
        t.registrar_falha(EMAIL, "1.1.1.1")
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") == 0
    t.registrar_falha(EMAIL, "1.1.1.1")
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") == t.JANELA_SEGUNDOS
    assert t.segundos_de_espera(EMAIL, "2.2.2.2") == 0
    assert t.segundos_de_espera("gerente@floricultura.com", "1.1.1.1") == 0


def test_trocar_de_ip_nao_passa_do_limite_por_email(relogio):
    for i in range(t.MAX_POR_EMAIL):
        t.registrar_falha(EMAIL, f"10.0.0.{i}")
    assert t.segundos_de_espera(EMAIL, "10.9.9.9") > 0


def test_libera_quando_a_janela_passa(relogio):
    for _ in range(t.MAX_POR_EMAIL_E_IP):
        t.registrar_falha(EMAIL, "1.1.1.1")
    relogio[0] += t.JANELA_SEGUNDOS - 1
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") == 1
    relogio[0] += 1
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") == 0


def test_email_conta_igual_com_maiusculas_e_espacos(relogio):
    for _ in range(t.MAX_POR_EMAIL_E_IP):
        t.registrar_falha(" Gestora@Floricultura.com ", "1.1.1.1")
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") > 0


def test_login_certo_zera_o_contador_do_ip(relogio):
    for _ in range(t.MAX_POR_EMAIL_E_IP - 1):
        t.registrar_falha(EMAIL, "1.1.1.1")
    t.registrar_sucesso(EMAIL, "1.1.1.1")
    t.registrar_falha(EMAIL, "1.1.1.1")
    assert t.segundos_de_espera(EMAIL, "1.1.1.1") == 0
