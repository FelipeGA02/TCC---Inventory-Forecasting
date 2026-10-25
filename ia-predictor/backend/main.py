import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.api import router_auth, router_health, router_models, router_painel, router_upload
from backend.auth.dependencies import get_current_user
from backend.auth.seed_users import seed_initial_users
from backend.config import settings
from backend.infrastructure.database import SessionLocal, create_tables
from backend.infrastructure.scheduler import start_scheduler, stop_scheduler

log = logging.getLogger(__name__)

settings.exigir_segredos()


def _aquecer_cache() -> None:
    """Monta painel e análises logo ao subir: a primeira leitura das vendas leva de segundos
    (SQLite) a perto de um minuto (Neon), e assim não cai na primeira requisição."""
    from backend.services import painel_service

    try:
        with SessionLocal() as db:
            painel_service.analises(db)
        with SessionLocal() as db:
            painel_service.painel_leve(db)
    except painel_service.PrevisaoIndisponivel:
        log.info("cache: ainda não há previsão gravada")
    except Exception:
        log.exception("cache: falha ao montar o painel na subida")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    seed_initial_users()
    if settings.TRAINING_RUNNER == "local":
        start_scheduler()  # com TRAINING_RUNNER=externo a API não treina (ver disparo_treino)
    threading.Thread(target=_aquecer_cache, daemon=True, name="aquecer-cache").start()
    yield
    stop_scheduler()


app = FastAPI(
    title="Floricultura — API de Previsão de Vendas",
    version="1.0.0",
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# o painel tem ~2 MB de JSON; comprimido fica perto de 10%
app.add_middleware(GZipMiddleware, minimum_size=1024)


# Endpoints públicos / autenticação (sem prefixo /api/v1)
app.include_router(router_health.router, tags=["health"])
app.include_router(router_auth.router, prefix="/auth", tags=["auth"])

# Endpoints protegidos — exigem Authorization: Bearer <access_token> em todos.
# Perfis mínimos (admin em upload/retrain) são aplicados dentro de cada router.
# products, forecast, alerts, simulation e reports (openapi.yaml) ainda não têm
# implementação (os routers estão vazios): as telas leem tudo de /api/v1/painel.
_v1_auth = [Depends(get_current_user)]

app.include_router(router_painel.router, prefix="/api/v1", tags=["painel"], dependencies=_v1_auth)
app.include_router(router_upload.router, prefix="/api/v1", tags=["upload"], dependencies=_v1_auth)
app.include_router(router_models.router, prefix="/api/v1", tags=["models"], dependencies=_v1_auth)
