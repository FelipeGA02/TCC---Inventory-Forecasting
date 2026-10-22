"""`POST /upload` (admin): carrega uma planilha "Contas a Receber" no banco.

O processamento é síncrono (alguns segundos por planilha mensal) e só grava as vendas que
ainda não estão no banco. Ver `upload_service`. Com venda nova, agenda o treino para daqui a
`RETRAIN_AFTER_UPLOAD_MINUTES` (outra planilha no intervalo adia; ver `disparo_treino`).
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_admin
from backend.config import settings
from backend.infrastructure.database import User, get_db
from backend.schemas.upload import UploadResponse
from backend.services import disparo_treino, upload_service

router = APIRouter()

_MSG_REPETIDA = "Esta planilha já foi carregada antes. Nada foi duplicado."
_MSG_GRANDE = f"O arquivo passa de {settings.MAX_UPLOAD_MB} MB. Envie a planilha de um mês por vez."
_MSG_FALHA = "Não foi possível processar a planilha. Confira o arquivo e tente de novo."


@router.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UploadResponse:
    conteudo = file.file.read()
    try:
        resultado = upload_service.processar(db, conteudo, file.filename or "planilha.xlsx", user.id)
    except upload_service.PlanilhaInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=erro.args[0])
    except upload_service.PlanilhaRepetida:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_REPETIDA)
    except upload_service.PlanilhaGrandeDemais:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=_MSG_GRANDE)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_MSG_FALHA)
    treino = disparo_treino.apos_upload() if resultado.retrain_scheduled else None
    return UploadResponse(**asdict(resultado), retrain_at=treino)
