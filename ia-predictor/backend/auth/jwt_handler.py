"""Criação e decodificação de tokens JWT usando `python-jose`."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from backend.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Cria um access_token JWT. Expira em `ACCESS_TOKEN_EXPIRE_HOURS` por padrão."""
    to_encode = data.copy()
    delta = (
        expires_delta
        if expires_delta is not None
        else timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    expire = datetime.now(timezone.utc) + delta
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Cria um refresh_token JWT. Expira em `REFRESH_TOKEN_EXPIRE_DAYS`. O `jti` identifica o
    token para o logout revogá-lo (`revoked_tokens`)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida um token JWT.

    Levanta `jose.exceptions.JWTError` (ou subclasse, como `ExpiredSignatureError`)
    se o token estiver expirado, malformado ou com assinatura inválida — o chamador
    (`backend/auth/dependencies.py`) é responsável por capturar e traduzir em HTTP 401.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
