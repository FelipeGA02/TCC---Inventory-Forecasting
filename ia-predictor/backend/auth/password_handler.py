"""Hashing e verificação de senhas usando `bcrypt` diretamente.

NOTA: não usar `passlib` — `passlib==1.7.4` (última release, sem manutenção desde 2020)
é incompatível com `bcrypt>=4.1` (levanta `AttributeError: module 'bcrypt' has no
attribute '__about__'`). O hashing é feito diretamente com o pacote `bcrypt`.
"""
from __future__ import annotations

import bcrypt

# bcrypt processa no máximo 72 bytes; truncamos defensivamente para evitar erro.
_MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    """Gera hash bcrypt de uma senha em texto plano."""
    return bcrypt.hashpw(
        plain.encode("utf-8")[:_MAX_PASSWORD_BYTES], bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8")[:_MAX_PASSWORD_BYTES], hashed.encode("utf-8")
        )
    except ValueError:
        # hash malformado/vazio: nunca autentica.
        return False
