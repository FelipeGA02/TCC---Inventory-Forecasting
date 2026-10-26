"""Dependências FastAPI de autenticação/autorização.

`get_current_user` é aplicado a nível de router-include em `backend/main.py`
(`dependencies=[Depends(get_current_user)]`) em todos os routers `/api/v1/*`.
`require_admin` é usado individualmente nos endpoints que exigem perfil admin
(envio de planilha e todo o `/api/v1/servico-previsao/*`, o treino da previsão).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import decode_token
from backend.infrastructure.database import User, get_db

# auto_error=False para que a ausência de header produza a mesma mensagem PT-BR
# (via HTTPException abaixo) em vez do 403 genérico padrão do HTTPBearer.
_bearer_scheme = HTTPBearer(auto_error=False)

_MSG_NAO_AUTENTICADO = "Autenticação necessária. Faça login para continuar."
_MSG_TOKEN_INVALIDO = "Sessão expirada ou token inválido. Faça login novamente."
_MSG_USUARIO_INEXISTENTE = "Usuário não encontrado."
_MSG_USUARIO_INATIVO = "Usuário inativo. Contate o administrador."


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decodifica o Bearer token e carrega o usuário correspondente.

    Levanta 401 (PT-BR, sem jargão) se: header ausente, token inválido/expirado,
    token não é do tipo access, usuário não existe ou está inativo.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized(_MSG_NAO_AUTENTICADO)

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise _unauthorized(_MSG_TOKEN_INVALIDO)

    if payload.get("type") != "access":
        raise _unauthorized(_MSG_TOKEN_INVALIDO)

    user_id = payload.get("sub")
    if user_id is None:
        raise _unauthorized(_MSG_TOKEN_INVALIDO)

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    except (TypeError, ValueError):
        raise _unauthorized(_MSG_TOKEN_INVALIDO)

    if user is None:
        raise _unauthorized(_MSG_USUARIO_INEXISTENTE)
    if not user.is_active:
        raise _unauthorized(_MSG_USUARIO_INATIVO)

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Exige perfil admin. Levanta 403 (PT-BR) caso contrário."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para esta ação.",
        )
    return user
