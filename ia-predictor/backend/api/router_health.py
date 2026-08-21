from fastapi import APIRouter

router = APIRouter()

APP_VERSION = "1.0.0"


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "version": APP_VERSION}
