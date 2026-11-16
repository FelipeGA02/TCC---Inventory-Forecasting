"""Liga o Container Apps Job do treino no Azure (`TRAINING_RUNNER=azure_job`).

A API roda num Container App pequeno, sem CPU para o treino. O botão "Treinar previsões"
registra o disparo como `pending` em `forecast_jobs` e chama esta função, que inicia uma
execução do job (`python -m backend.scripts.treinar_previsoes --pendente`, com mais CPU e
memória, cobrado só enquanto roda). O job pega o disparo pendente e grava o andamento no
mesmo banco; a tela acompanha pela tabela, como no treino local.

Autenticação pela identidade gerenciada do Container App (variáveis `IDENTITY_ENDPOINT` e
`IDENTITY_HEADER`, que o Azure preenche), sem segredo guardado. A identidade precisa de
permissão para iniciar o job (papel *Contributor* no próprio job — deploy/azure/README.md).
Só biblioteca padrão: nada a instalar.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_ARM = "https://management.azure.com"
_API_VERSION = "2024-03-01"
_TIMEOUT_S = 20


class FalhaAoIniciarJob(Exception):
    """O Azure recusou ou não respondeu ao pedido de iniciar o job."""


def _token() -> str:
    endpoint, header = os.environ.get("IDENTITY_ENDPOINT"), os.environ.get("IDENTITY_HEADER")
    if not endpoint or not header:
        raise FalhaAoIniciarJob("identidade gerenciada não configurada no Container App "
                                "(IDENTITY_ENDPOINT/IDENTITY_HEADER ausentes)")
    consulta = urllib.parse.urlencode({"resource": _ARM + "/", "api-version": "2019-08-01"})
    pedido = urllib.request.Request(f"{endpoint}?{consulta}", headers={"X-IDENTITY-HEADER": header})
    try:
        with urllib.request.urlopen(pedido, timeout=_TIMEOUT_S) as r:
            return json.load(r)["access_token"]
    except (urllib.error.URLError, KeyError, ValueError) as e:
        raise FalhaAoIniciarJob(f"token da identidade gerenciada: {e}") from e


def iniciar_job(job_id_azure: str) -> str:
    """Inicia uma execução do job; devolve o nome da execução."""
    pedido = urllib.request.Request(
        f"{_ARM}{job_id_azure}/start?api-version={_API_VERSION}", data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=_TIMEOUT_S) as r:
            corpo = r.read()
    except urllib.error.HTTPError as e:
        raise FalhaAoIniciarJob(f"HTTP {e.code}: {e.read()[:500].decode('utf-8', 'replace')}") from e
    except urllib.error.URLError as e:
        raise FalhaAoIniciarJob(str(e)) from e
    try:
        return json.loads(corpo or b"{}").get("name", "")
    except ValueError:
        return ""
