"""A API não sobe com chave do JWT ou senhas vazias, curtas ou de exemplo."""
import pytest

from backend.config import Settings

FORTES = {"JWT_SECRET_KEY": "k" * 40, "ADMIN_PASSWORD": "senha-propria-1", "VIEWER_PASSWORD": "senha-propria-2"}


def _settings(**valores) -> Settings:
    return Settings(_env_file=None, **{**FORTES, **valores})


def test_valores_proprios_passam():
    _settings().exigir_segredos()


@pytest.mark.parametrize("campo, valor", [
    ("JWT_SECRET_KEY", ""),
    ("JWT_SECRET_KEY", "curta"),
    ("JWT_SECRET_KEY", "change-me-32-characters-minimum!!"),
    ("JWT_SECRET_KEY", "troque_por_string_aleatoria_32_chars_minimo"),
    ("ADMIN_PASSWORD", ""),
    ("ADMIN_PASSWORD", "1234567"),
    ("VIEWER_PASSWORD", "troque_por_senha_forte"),
])
def test_valor_fraco_impede_a_subida(campo, valor):
    with pytest.raises(RuntimeError, match=campo):
        _settings(**{campo: valor}).exigir_segredos()
