"""Inicia uma execução do Job de treino no Cloud Run (`TRAINING_RUNNER=cloud_run_job`).

Chama a Cloud Run Admin API (`POST .../jobs/<nome>:run`) com o token da conta de serviço
da própria API, lido do servidor de metadados do Google — sem biblioteca extra. A conta
precisa da permissão `run.jobs.run` no Job (ver `deploy/README.md`).
"""
from __future__ import annotations

import json
import urllib.request

_METADADOS = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
_API = "https://run.googleapis.com/v2"


def _token() -> str:
    req = urllib.request.Request(_METADADOS, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["access_token"]


def executar(job: str) -> None:
    """`job`: `projects/<projeto>/locations/<região>/jobs/<nome>`."""
    req = urllib.request.Request(f"{_API}/{job}:run", data=b"{}", method="POST",
                                 headers={"Authorization": f"Bearer {_token()}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30):
        pass
