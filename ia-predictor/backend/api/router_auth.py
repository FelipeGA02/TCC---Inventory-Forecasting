"""Endpoints de autenticação: POST /login, POST /refresh, POST /logout, GET /me.

Incluído em `backend/main.py` com `prefix="/auth"` — rotas aqui NÃO levam o
prefixo `/auth`. Estas rotas são públicas (login, logout) ou exigem apenas um token
válido (refresh, me) — a dependência `get_current_user` aplicada em nível de
router-include a `/api/v1/*` NÃO se aplica a este router.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.auth import tentativas_login
from backend.auth.dependencies import get_current_user
from backend.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from backend.auth.password_handler import hash_password, verify_password
from backend.config import settings
from backend.infrastructure.database import RevokedToken, User, get_db
from backend.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshTokenResponse,
    TokenResponse,
    UserOut,
)

router = APIRouter()

_MSG_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."
_MSG_REFRESH_INVALIDO = "Sessão expirada. Faça login novamente."
_MSG_USUARIO_INDISPONIVEL = "Usuário não encontrado ou inativo."

# e-mail sem cadastro também passa pelo bcrypt: o tempo da resposta não revela quem existe
_HASH_SEM_USUARIO = hash_password("usuario-inexistente")


def _token_payload(user: User) -> dict:
    return {"sub": str(user.id), "email": user.email, "role": user.role}


def _expires_in_seconds() -> int:
    return settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600


def _utc(timestamp: float) -> datetime:
    """`revoked_tokens.expires_at` é gravado em UTC, sem fuso (coluna `DateTime` simples)."""
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    ip = request.client.host if request.client else ""
    espera = tentativas_login.segundos_de_espera(payload.email, ip)
    if espera:
        minutos = -(-espera // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas com senha errada. Tente de novo em {minutos} "
                   f"minuto{'s' if minutos > 1 else ''}.",
            headers={"Retry-After": str(espera)},
        )

    user = db.query(User).filter(User.email == payload.email).first()
    senha_ok = verify_password(payload.password, user.hashed_password if user else _HASH_SEM_USUARIO)

    if user is None or not user.is_active or not senha_ok:
        tentativas_login.registrar_falha(payload.email, ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MSG_CREDENCIAIS_INVALIDAS,
        )
    tentativas_login.registrar_sucesso(payload.email, ip)

    data = _token_payload(user)
    return TokenResponse(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
        token_type="bearer",
        role=user.role,
        expires_in=_expires_in_seconds(),
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> RefreshTokenResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_MSG_REFRESH_INVALIDO)

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_MSG_REFRESH_INVALIDO)

    jti = decoded.get("jti")
    if not jti or db.get(RevokedToken, jti) is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_MSG_REFRESH_INVALIDO)

    user_id = decoded.get("sub")
    user = None
    if user_id is not None:
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
        except (TypeError, ValueError):
            user = None

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_MSG_USUARIO_INDISPONIVEL)

    new_access_token = create_access_token(_token_payload(user))
    return RefreshTokenResponse(access_token=new_access_token, expires_in=_expires_in_seconds())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    """Revoga o token de renovação. Token já inválido ou expirado não tem o que revogar."""
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    jti, user_id = decoded.get("jti"), decoded.get("sub")
    if decoded.get("type") == "refresh" and jti and user_id is not None:
        db.execute(delete(RevokedToken).where(RevokedToken.expires_at < _utc(time.time())))
        db.merge(RevokedToken(jti=jti, user_id=int(user_id), expires_at=_utc(decoded["exp"])))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
