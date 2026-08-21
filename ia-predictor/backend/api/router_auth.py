"""Endpoints de autenticação: POST /login, POST /refresh, GET /me.

Incluído em `backend/main.py` com `prefix="/auth"` — rotas aqui NÃO levam o
prefixo `/auth`. Estas rotas são públicas (login) ou exigem apenas um token
válido (refresh, me) — a dependência `get_current_user` aplicada em nível de
router-include a `/api/v1/*` NÃO se aplica a este router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from backend.auth.password_handler import verify_password
from backend.config import settings
from backend.infrastructure.database import User, get_db
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


def _token_payload(user: User) -> dict:
    return {"sub": str(user.id), "email": user.email, "role": user.role}


def _expires_in_seconds() -> int:
    return settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()

    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MSG_CREDENCIAIS_INVALIDAS,
        )

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


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
