"""Schemas de `/api/v1/servico-previsao/*` — campos espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ConfigServico(BaseModel):
    """Como o serviço treina — o modal de confirmação mostra isto."""

    m: int
    d: int  # com um candidato só, o d de todas as séries; com mais, o primeiro
    d_candidatos: list[int]  # d testados no walk-forward de cada série; fica o que errou menos (ADR-020)
    D: int
    janela_dias: int
    origens: int
    passo_dias: int
    horizonte_dias: int  # do walk-forward (o teste que dá o status)
    horizonte_previsao_dias: int  # dias previstos; a tela escolhe de horizonte_dias até este (ADR-021)
    base: str
    categoria_produtos: str


class TreinoServico(BaseModel):
    id: int
    status: str  # pending|running|done|error|skipped
    criado_em: datetime
    iniciado_em: datetime | None = None
    concluido_em: datetime | None = None
    dados_ate: date | None = None
    total_series: int = 0
    series_concluidas: int = 0
    progresso_pct: float = 0.0
    serie_atual: str | None = None
    series_treinadas: int = 0  # séries com previsão
    series_dados_insuficientes: int = 0
    series_com_erro: int = 0
    mensagem: str | None = None


class StatusServico(BaseModel):
    treino_na_api: bool
    em_andamento: TreinoServico | None = None
    ultimo: TreinoServico | None = None
    ultimo_concluido_em: datetime | None = None
    # se um disparo agora treinaria; nulo enquanto há treino em andamento
    dados_alterados: bool | None = None
    config: ConfigServico


class DisparoResposta(BaseModel):
    iniciado: bool
    mensagem: str
    treino: TreinoServico


class LogTreino(BaseModel):
    id: int
    registrado_em: datetime
    nivel: str  # info|warning|error
    serie: str | None = None
    mensagem: str


class PrevisaoDia(BaseModel):
    data: date
    previsto: float
    inf_95: float
    sup_95: float


class SerieTreinada(BaseModel):
    id: int
    loja: str
    loja_nome: str
    nivel: str  # category|product
    categoria: str | None = None
    produto_codigo: str | None = None
    nome: str
    status: str  # trained|insufficient_data|error
    ordem: list[int] | None = None
    ordem_sazonal: list[int] | None = None
    aic: float | None = None
    mase: float | None = None
    cobertura_ic95_pct: float | None = None
    metricas: dict | None = None
    mensagem: str | None = None
    previsao: list[PrevisaoDia] = []
