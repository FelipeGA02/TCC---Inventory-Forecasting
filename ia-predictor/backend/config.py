from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# `ia-predictor/.env`, de onde quer que o comando seja rodado (uvicorn na raiz do repo com
# --app-dir, scripts a partir de ia-predictor/...).
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    # Diretórios
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    RESULTS_DIR: str = "results"

    # Banco: SQLite local por padrão; Postgres no Neon com a URL de conexão do console
    # (postgresql://usuario:senha@ep-...neon.tech/neondb?sslmode=require). Ver ADR-014.
    DATABASE_URL: str = "sqlite:///./floricultura.db"

    # Auth — chave e senhas sem valor padrão: a API não sobe sem elas (`exigir_segredos`)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Usuários iniciais (seed)
    ADMIN_EMAIL: str = "gestora@floricultura.com"
    ADMIN_PASSWORD: str = ""
    VIEWER_EMAIL: str = "gerente@floricultura.com"
    VIEWER_PASSWORD: str = ""

    # /docs, /redoc e /openapi.json (desligados no Render pelo render.yaml)
    DOCS_ENABLED: bool = True

    # Previsão (ADR-017): SARIMAX direto nas 4 categorias e em cada produto de grama, por
    # loja, com m = SEASONAL_PERIOD, d = 0 e D = 0 (fixos em servico_previsao.py).
    FORECAST_HORIZON_DAYS: int = 14       # dias previstos a partir do dia seguinte à última venda
    SEASONAL_PERIOD: int = 7              # m — sazonalidade semanal do SARIMAX
    MIN_OBSERVATIONS_DAYS: int = 180      # histórico mínimo antes da 1ª origem do walk-forward
    FORECAST_SERVICE_WINDOW_DAYS: int = 365     # janela deslizante de treino (dias)
    FORECAST_SERVICE_WF_ORIGINS: int = 56       # origens do walk-forward, andando 1 dia (8 semanas)
    FORECAST_SERVICE_MIN_SALE_DAYS: int = 28    # produto: dias com venda na última janela para treinar
    FORECAST_SERVICE_KEEP_BACKTEST_JOBS: int = 4  # treinos concluídos que guardam o walk-forward inteiro
    TRAINING_WORKERS: int = 8             # processos no treino (no servidor: o nº de CPUs)
    # onde o treino roda: "local" (thread da API, pelo botão "Treinar previsões") ou "externo"
    # (a API não treina: script treinar_previsoes em outra máquina; API no Render, ADR-015)
    TRAINING_RUNNER: Literal["local", "externo"] = "local"
    MAX_UPLOAD_MB: int = 50

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    def exigir_segredos(self) -> None:
        """Chamado na subida da API. Os scripts (carga, treino) não precisam destes valores."""
        faltando = []
        if len(self.JWT_SECRET_KEY) < 32 or _de_exemplo(self.JWT_SECRET_KEY):
            faltando.append("JWT_SECRET_KEY (texto aleatório com 32 ou mais caracteres)")
        for nome in ("ADMIN_PASSWORD", "VIEWER_PASSWORD"):
            valor = getattr(self, nome)
            if len(valor) < 8 or _de_exemplo(valor):
                faltando.append(f"{nome} (senha própria com 8 ou mais caracteres)")
        if faltando:
            raise RuntimeError("Configure no .env ou nas variáveis do servidor: " + "; ".join(faltando))


def _de_exemplo(valor: str) -> bool:
    """Valores de exemplo do .env.example e os antigos padrões do código."""
    return any(trecho in valor.lower() for trecho in ("troque", "change-me"))


settings = Settings()
