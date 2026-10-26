"""Schemas Pydantic de `POST /api/v1/upload` e `POST /api/v1/upload/verificacao` — campos
espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from datetime import date

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
