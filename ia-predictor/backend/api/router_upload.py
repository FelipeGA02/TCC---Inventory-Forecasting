"""Envio de planilha "Contas a Receber" (admin), em dois passos:

  * `POST /upload/verificacao`: confere a planilha sem gravar — período de cada loja, vendas
    novas e já carregadas, e os dias de loja aberta que ficariam sem venda — para a tela
    avisar antes da confirmação;
  * `POST /upload`: grava, depois que a gestora confirma (a planilha é enviada de novo).

O processamento é síncrono (alguns segundos por planilha mensal) e só grava as vendas que
ainda não estão no banco. Ver `upload_service`. O treino não roda sozinho: com venda nova,
a resposta traz `needs_training` e a tela oferece "Treinar previsões" (ADR-017).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_admin
from backend.config import settings
from backend.infrastructure.database import User, get_db
from backend.schemas.upload import UploadCheckResponse, UploadResponse
from backend.services import upload_service

router = APIRouter()

_MSG_REPETIDA = "Esta planilha já foi carregada antes. Nada foi duplicado."
_MSG_GRANDE = f"O arquivo passa de {settings.MAX_UPLOAD_MB} MB. Envie a planilha de um mês por vez."
_MSG_FALHA = "Não foi possível processar a planilha. Confira o arquivo e tente de novo."

T = TypeVar("T")


def _ler_planilha(file: UploadFile, passo: Callable[[bytes, str], T]) -> T:
    """Lê o arquivo e roda `passo(conteudo, nome)`, com as recusas em linguagem da loja."""
    # 1 byte além do limite basta para o serviço recusar o arquivo sem carregá-lo inteiro
    conteudo = file.file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        return passo(conteudo, file.filename or "planilha.xlsx")
    except upload_service.PlanilhaInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=erro.args[0])
    except upload_service.PlanilhaRepetida:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_REPETIDA)
    except upload_service.PlanilhaGrandeDemais:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=_MSG_GRANDE)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_MSG_FALHA)


@router.post("/upload/verificacao", response_model=UploadCheckResponse)
def verificar_upload(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UploadCheckResponse:
    verificacao = _ler_planilha(file, lambda conteudo, nome: upload_service.verificar(db, conteudo, nome))
    return UploadCheckResponse(**asdict(verificacao))


@router.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UploadResponse:
    resultado = _ler_planilha(file, lambda conteudo, nome: upload_service.processar(db, conteudo, nome, user.id))
    return UploadResponse(**asdict(resultado))
