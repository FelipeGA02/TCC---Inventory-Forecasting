"""Cria os usuários iniciais (admin/viewer) a partir das variáveis de ambiente.

Idempotente: chamado a cada startup (`backend/main.py`), só cria o usuário se o
e-mail ainda não existir na tabela `users`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.auth.password_handler import hash_password
from backend.config import settings
from backend.infrastructure.database import SessionLocal, User


def seed_initial_users() -> None:
    db: Session = SessionLocal()
    try:
        _create_if_missing(
            db,
            email=settings.ADMIN_EMAIL,
            password=settings.ADMIN_PASSWORD,
            name="Administradora",
            role="admin",
        )
        _create_if_missing(
            db,
            email=settings.VIEWER_EMAIL,
            password=settings.VIEWER_PASSWORD,
            name="Gerente",
            role="viewer",
        )
        db.commit()
    finally:
        db.close()


def _create_if_missing(db: Session, *, email: str, password: str, name: str, role: str) -> None:
    exists = db.query(User).filter(User.email == email).first()
    if exists is not None:
        return
    db.add(
        User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
    )
