"""Schemas Pydantic de autenticação — campos espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# NOTA: openapi.yaml declara `email` como `type: string, format: email` (não um
# `$ref` a formato validado). Usamos `str` em vez de `pydantic.EmailStr` porque
# `EmailStr` exige o pacote opcional `email-validator`, que não está listado em
# requirements.txt — evita introduzir uma dependência nova fora do escopo desta tarefa.


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Corpo de resposta de `POST /auth/refresh` (openapi.yaml define um schema
    inline distinto de `TokenResponse`: apenas `access_token` + `expires_in`,
    sem `refresh_token`/`role`)."""

    access_token: str
    expires_in: int
