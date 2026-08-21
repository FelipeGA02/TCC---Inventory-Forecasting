from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import (
    router_alerts,
    router_auth,
    router_forecast,
    router_health,
    router_models,
    router_products,
    router_reports,
    router_simulation,
    router_upload,
)
from backend.auth.dependencies import get_current_user
from backend.auth.seed_users import seed_initial_users
from backend.config import settings
from backend.infrastructure.database import create_tables
from backend.infrastructure.scheduler import start_scheduler

app = FastAPI(
    title="Floricultura — API de Previsão de Estoque",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    create_tables()
    seed_initial_users()
    start_scheduler()


# Endpoints públicos / autenticação (sem prefixo /api/v1)
app.include_router(router_health.router, tags=["health"])
app.include_router(router_auth.router, prefix="/auth", tags=["auth"])

# Endpoints protegidos — exigem Authorization: Bearer <access_token> em todos.
# Perfis mínimos (admin em upload/retrain) são aplicados dentro de cada router.
_v1_auth = [Depends(get_current_user)]

app.include_router(router_upload.router, prefix="/api/v1", tags=["upload"], dependencies=_v1_auth)
app.include_router(router_products.router, prefix="/api/v1", tags=["products"], dependencies=_v1_auth)
app.include_router(router_forecast.router, prefix="/api/v1", tags=["forecast"], dependencies=_v1_auth)
app.include_router(router_alerts.router, prefix="/api/v1", tags=["alerts"], dependencies=_v1_auth)
app.include_router(router_simulation.router, prefix="/api/v1", tags=["simulation"], dependencies=_v1_auth)
app.include_router(router_reports.router, prefix="/api/v1", tags=["reports"], dependencies=_v1_auth)
app.include_router(router_models.router, prefix="/api/v1", tags=["models"], dependencies=_v1_auth)
