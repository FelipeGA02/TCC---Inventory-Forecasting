"""Limite de senhas erradas no `/auth/login`, contado na memória (a API roda num processo só).

Dois limites na mesma janela: por e-mail e IP (barra quem tenta senhas de um computador) e
por e-mail de qualquer IP. O segundo existe porque o IP vem do `X-Forwarded-For`, que quem
chama pode forjar; com ele, mesmo trocando de IP, são no máximo 20 tentativas a cada 15 min.
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque

JANELA_SEGUNDOS = 15 * 60
MAX_POR_EMAIL_E_IP = 5
MAX_POR_EMAIL = 20
_MAX_CHAVES = 10_000

_falhas: dict[tuple, deque[float]] = {}
_trava = threading.Lock()


def _limites(email: str, ip: str) -> list[tuple[tuple, int]]:
    email = email.strip().lower()
    return [(("email_ip", email, ip), MAX_POR_EMAIL_E_IP), (("email", email), MAX_POR_EMAIL)]


def _recentes(chave: tuple, agora: float) -> deque[float] | None:
    fila = _falhas.get(chave)
    while fila and agora - fila[0] >= JANELA_SEGUNDOS:
        fila.popleft()
    if fila is not None and not fila:
        del _falhas[chave]
        return None
    return fila


def segundos_de_espera(email: str, ip: str) -> int:
    """0 se pode tentar; senão, quantos segundos faltam para liberar."""
    agora = time.monotonic()
    espera = 0.0
    with _trava:
        for chave, limite in _limites(email, ip):
            fila = _recentes(chave, agora)
            if fila is not None and len(fila) >= limite:
                espera = max(espera, JANELA_SEGUNDOS - (agora - fila[-limite]))
    return math.ceil(espera)


def registrar_falha(email: str, ip: str) -> None:
    agora = time.monotonic()
    with _trava:
        if len(_falhas) >= _MAX_CHAVES:
            for chave in list(_falhas):
                _recentes(chave, agora)
        for chave, _ in _limites(email, ip):
            _falhas.setdefault(chave, deque()).append(agora)


def registrar_sucesso(email: str, ip: str) -> None:
    with _trava:
        _falhas.pop(_limites(email, ip)[0][0], None)


def limpar() -> None:
    with _trava:
        _falhas.clear()
