"""Log de uso do sistema (tela Relatórios): as planilhas enviadas (`processing_log`) e os
treinos da previsão (`forecast_jobs`), numa lista só, do mais recente para o mais antigo.

A reclassificação da base (`kind = "reclassification"`, scripts de manutenção) fica de fora:
não é uso da loja. A mensagem gravada só sai quando a planilha ou o treino deu erro — a do
treino concluído é um resumo que a tela monta das contagens (e a dos treinos antigos fala de
uma classificação de confiança que saiu do sistema).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.database import ForecastJob, ProcessingLog, User
from backend.services.base_vendas import KIND_RECLASSIFICACAO

LIMITE_MAXIMO = 500

_SITUACAO = {"done": "concluido", "skipped": "sem_dados_novos", "error": "erro",
             "pending": "em_andamento", "running": "em_andamento"}


def _iso(v: datetime | None) -> str | None:
    return v.isoformat(timespec="seconds") if v else None


def _vazio() -> dict:
    return {"arquivo": None, "periodo": None, "linhas_novas": None, "linhas_duplicadas": None,
            "dados_ate": None, "series_com_previsao": None, "series_sem_dados": None, "series_com_falha": None}


def listar(db: Session, limite: int = 100) -> list[dict]:
    """Os `limite` eventos mais recentes, planilhas e treinos misturados pela hora de início."""
    limite = max(1, min(limite, LIMITE_MAXIMO))
    nomes = dict(db.execute(select(User.id, User.name)).all())

    planilhas = db.scalars(select(ProcessingLog).where(ProcessingLog.kind != KIND_RECLASSIFICACAO)
                           .order_by(ProcessingLog.started_at.desc()).limit(limite))
    treinos = db.scalars(select(ForecastJob).order_by(ForecastJob.created_at.desc()).limit(limite))

    itens = [{
        **_vazio(),
        "tipo": "planilha", "id": p.id, "inicio": _iso(p.started_at), "fim": _iso(p.finished_at),
        "situacao": _SITUACAO.get(p.status, p.status), "usuario": nomes.get(p.user_id),
        "origem": "carga_inicial" if p.kind == "initial_load" else "envio",
        "arquivo": p.filename, "periodo": (p.quality or {}).get("periodo"),
        "linhas_novas": p.rows_added, "linhas_duplicadas": p.rows_duplicate,
        "mensagem": p.message if p.status == "error" else None,
    } for p in planilhas]
    itens += [{
        **_vazio(),
        "tipo": "treino", "id": j.id, "inicio": _iso(j.started_at or j.created_at), "fim": _iso(j.finished_at),
        "situacao": _SITUACAO.get(j.status, j.status), "usuario": nomes.get(j.user_id),
        "origem": "botao" if j.trigger == "manual" else "script",
        "dados_ate": str(j.data_until) if j.data_until else None,
        "series_com_previsao": j.series_trained, "series_sem_dados": j.series_insufficient,
        "series_com_falha": j.series_failed,
        "mensagem": j.message if j.status == "error" else None,
    } for j in treinos]
    itens.sort(key=lambda i: i["inicio"] or "", reverse=True)
    return itens[:limite]
