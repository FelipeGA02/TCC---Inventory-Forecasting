"""Dados das telas do frontend, pedidos por tela (nada é carregado de uma vez no login):

  * `/contexto`: o que o layout precisa logo depois do login (lojas, categorias, data da
    última venda, status dos previsores, planilhas carregadas) — leve, só consultas agregadas;
  * `/painel` (tela de previsão e relatórios: o último treino concluído das categorias e
    dos produtos de grama) e `/painel/historico/{loja}/{categoria|produto}/{item}` (vendido
    × previsto congelado, na tela de histórico da previsão);
  * `/analises` (painel inicial);
  * `/atividades` (tela Relatórios): o log de uso — planilhas enviadas e treinos;
  * `/registros/*` (Conferir Dados): a base paginada no banco — índice dos meses, uma página,
    os totais do filtro, os itens de uma nota e a exportação.

Os formatos são os de `app-react/src/domain/types.ts` (`BaseReal`) e
`app-react/src/app/data/analises.ts`. Painel e análises são montados de `sales` e das
tabelas do treino por `painel_service`, com cache até os dados mudarem.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.infrastructure.database import SessionLocal, get_db
from backend.services import atividades_service, painel_service, registros_service
from backend.services.registros_service import Filtros

router = APIRouter()

_MSG_SEM_PREVISAO = (
    "A previsão ainda não foi gerada. Peça à gestora para usar \"Treinar previsões\" e tente de novo."
)
_MSG_SEM_TREINO = (
    "O histórico da previsão aparece depois do primeiro treino. Peça à gestora para usar "
    "\"Treinar previsões\" e tente de novo."
)
_MSG_SEM_HISTORICO = "Não há vendas deste item nesta loja."


def _padrao(valor: Any):
    if isinstance(valor, np.generic):
        return valor.item()
    return str(valor)


class RespostaJSON(JSONResponse):
    """JSON compacto, sem passar pelo `jsonable_encoder` (o painel tem ~2 MB)."""

    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, separators=(",", ":"), default=_padrao).encode("utf-8")


@router.get("/contexto", response_class=RespostaJSON)
def contexto(db: Session = Depends(get_db)) -> RespostaJSON:
    return RespostaJSON(painel_service.contexto(db))


@router.get("/painel", response_class=RespostaJSON)
def painel(db: Session = Depends(get_db)) -> RespostaJSON:
    try:
        return RespostaJSON(painel_service.painel(db))
    except painel_service.PrevisaoIndisponivel:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_SEM_PREVISAO)


@router.get("/painel/historico/{unidade}/{nivel}/{item}", response_class=RespostaJSON)
def historico(unidade: str, nivel: Literal["categoria", "produto"], item: str,
              db: Session = Depends(get_db)) -> RespostaJSON:
    try:
        return RespostaJSON(painel_service.historico(db, unidade, nivel, item))
    except painel_service.PrevisaoIndisponivel:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_SEM_TREINO)
    except painel_service.ItemSemHistorico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_SEM_HISTORICO)


@router.get("/atividades", response_class=RespostaJSON)
def atividades(limite: int = Query(default=100, ge=1, le=atividades_service.LIMITE_MAXIMO),
               db: Session = Depends(get_db)) -> RespostaJSON:
    """Log de uso: planilhas enviadas e treinos da previsão, do mais recente ao mais antigo."""
    return RespostaJSON(atividades_service.listar(db, limite))


@router.get("/analises", response_class=RespostaJSON)
def analises(db: Session = Depends(get_db)) -> RespostaJSON:
    return RespostaJSON(painel_service.analises(db))


# --------------------------------------------------------------------------- #
# Registros (Conferir Dados) — paginados no banco
# --------------------------------------------------------------------------- #
def filtros_registros(
    meses: list[str] = Query(default=[], description="AAAA-MM; vazio = todos os meses"),
    lojas: list[str] = Query(default=[]),
    categorias: list[str] = Query(default=[]),
    pagamentos: list[str] = Query(default=[], description="como a tela mostra (ex.: Pix)"),
    cliente: Literal["todos", "consumidor", "cadastrado"] = "todos",
    tipo: Literal["todos", "dia", "encomenda"] = "todos",
    desconto: Literal["todos", "com", "sem"] = "todos",
    movimento: Literal["todos", "venda", "devolucao"] = "todos",
    data_de: date | None = None,
    data_ate: date | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    busca: str = Query(default="", max_length=100),
) -> Filtros:
    for m in meses:
        if len(m) != 7 or m[4] != "-" or not (m[:4] + m[5:]).isdigit():
            raise HTTPException(status_code=422, detail=f"Mês inválido: {m}. Use AAAA-MM.")
    return Filtros(meses=meses, lojas=lojas, categorias=categorias, pagamentos=pagamentos,
                   cliente=cliente, tipo=tipo, desconto=desconto, movimento=movimento,
                   data_de=data_de, data_ate=data_ate, valor_min=valor_min, valor_max=valor_max, busca=busca)


Ordem = Literal["data", "loja", "nota", "produto", "categoria", "qtd", "unit", "desc", "liq", "pag",
                "cliente", "tipo"]


@router.get("/registros", response_class=RespostaJSON)
def indice_registros(db: Session = Depends(get_db)) -> RespostaJSON:
    return RespostaJSON(registros_service.indice(db))


@router.get("/registros/linhas", response_class=RespostaJSON)
def linhas_registros(
    filtros: Filtros = Depends(filtros_registros),
    ordem: Ordem | None = "data",
    direcao: Literal["asc", "desc"] = "desc",
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=50, ge=1, le=registros_service.TAMANHO_MAXIMO),
    db: Session = Depends(get_db),
) -> RespostaJSON:
    return RespostaJSON(registros_service.linhas(db, filtros, ordem, direcao, pagina, tamanho))


@router.get("/registros/resumo", response_class=RespostaJSON)
def resumo_registros(filtros: Filtros = Depends(filtros_registros), db: Session = Depends(get_db)) -> RespostaJSON:
    return RespostaJSON(registros_service.resumo(db, filtros))


@router.get("/registros/nota", response_class=RespostaJSON)
def nota_registros(loja: str, data: date, nota: str, db: Session = Depends(get_db)) -> RespostaJSON:
    return RespostaJSON(registros_service.itens_da_nota(db, loja, data, nota))


@router.get("/registros/exportar")
def exportar_registros(
    filtros: Filtros = Depends(filtros_registros),
    ordem: Ordem | None = "data",
    direcao: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    def gerar():
        # sessão própria: vive enquanto a resposta é enviada, em pedaços
        with SessionLocal() as db:
            yield from registros_service.exportar(db, filtros, ordem, direcao)

    return StreamingResponse(gerar(), media_type="application/json")
