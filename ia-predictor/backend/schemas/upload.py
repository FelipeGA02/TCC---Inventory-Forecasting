"""Schema Pydantic de `POST /api/v1/upload` — campos espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    rows_added: int
    rows_skipped: int
    rows_duplicate: int
    processing_time_seconds: float
    retrain_scheduled: bool
    errors: list[str] = []
