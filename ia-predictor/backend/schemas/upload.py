"""Schemas Pydantic de `POST /api/v1/upload` e `POST /api/v1/upload/verificacao` — campos
espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    rows_added: int
    rows_skipped: int
    rows_duplicate: int
    processing_time_seconds: float
    needs_training: bool  # venda nova: a previsão só a usa depois de "Treinar previsões"
    errors: list[str] = []


class UploadUnitPeriod(BaseModel):
    unit_id: str
    unit_name: str
    first_day: date
    last_day: date
    rows: int
    last_day_loaded: date | None  # última venda da loja já na base, antes desta planilha


class DateRange(BaseModel):
    start: date
    end: date


class UploadMissingDays(BaseModel):
    unit_id: str
    unit_name: str
    days: int  # dias de loja aberta que ficariam sem venda
    ranges: list[DateRange]
    message: str


class UploadCheckResponse(BaseModel):
    filename: str
    period_start: date
    period_end: date
    rows_new: int
    rows_duplicate: int
    rows_skipped: int
    units: list[UploadUnitPeriod]
    missing_days: list[UploadMissingDays]
    warnings: list[str]  # avisos da leitura (linhas ignoradas)
    treatments: list["UploadTreatmentGroup"] = []  # cada tratamento, item a item, para corrigir a planilha


class UploadTreatmentColumn(BaseModel):
    key: str
    label: str


class UploadTreatmentItem(BaseModel):
    line: int | None = None            # linha do Excel, para achar e corrigir
    values: dict[str, str | None]      # coluna → valor como está na planilha (None = vazio)
    highlight: list[str] = []          # colunas com o problema


class UploadTreatmentGroup(BaseModel):
    """Um problema da planilha (`domain.etl.tratamentos`): onde está, os campos ligados a ele e
    o que fazer. `corrigir` interrompe (a venda fica de fora); `aviso` não impede gravar."""
    kind: str
    level: Literal["corrigir", "aviso"]
    title: str
    how_to_fix: str | None
    count: int
    count_label: str
    columns: list[UploadTreatmentColumn]
    items: list[UploadTreatmentItem]
    total_items: int                   # itens antes do corte (a tela lista até 100 por grupo)


UploadCheckResponse.model_rebuild()
