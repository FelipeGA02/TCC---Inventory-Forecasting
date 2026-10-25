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

    # Auth
    JWT_SECRET_KEY: str = "change-me-32-characters-minimum!!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Usuários iniciais (seed)
    ADMIN_EMAIL: str = "gestora@floricultura.com"
    ADMIN_PASSWORD: str = "troque_por_senha_forte"
    VIEWER_EMAIL: str = "gerente@floricultura.com"
    VIEWER_PASSWORD: str = "troque_por_senha_forte"

    # Pipeline ML — camada L1 (unidade x categoria, diario). Ver ADR-009.
    TOP_N_PRODUCTS: int = 20              # SKUs com desagregacao (L2) e reposicao (L3) detalhadas
    FORECAST_HORIZON_DAYS: int = 14       # horizonte da previsao e da recomendacao de reposicao
    FORECAST_STORED_DAYS: int = 60        # dias previstos e gravados por geracao; a API mostra 14 a partir de hoje
    TEST_DAYS: int = 28                   # hold-out para avaliacao
    MIN_OBSERVATIONS_DAYS: int = 180      # minimo de dias por unidade x categoria para treinar L1
    SEASONAL_PERIOD: int = 7             # m — sazonalidade semanal do SARIMAX
    LOG_CV_THRESHOLD: float = 0.7        # limiar (CV = std/mean) para log1p transform
    ALERT_VARIATION_THRESHOLD: float = 0.20  # previsao 7d 20% acima da media 4 semanas dispara alerta
    MAX_UPLOAD_MB: int = 50
    TRAINING_WORKERS: int = 8            # processos no treino dos produtos (no servidor: o nº de CPUs)

    # Serviço de previsão (botão do admin): SARIMAX direto nas 4 categorias e nos produtos de
    # grama, por loja, com m = SEASONAL_PERIOD, d = 0, D = 0 (fixos em servico_previsao.py),
    # horizonte FORECAST_HORIZON_DAYS e mínimo de histórico MIN_OBSERVATIONS_DAYS.
    FORECAST_SERVICE_WINDOW_DAYS: int = 365     # janela deslizante de treino (dias)
    FORECAST_SERVICE_WF_ORIGINS: int = 56       # origens do walk-forward, andando 1 dia (8 semanas)
    FORECAST_SERVICE_MIN_SALE_DAYS: int = 28    # produto: dias com venda na última janela para treinar

    # Politica de reposicao (L3)
    SAFETY_STOCK_DAYS: int = 2           # estoque de seguranca em dias de demanda prevista
    SHELF_LIFE_DEFAULT_DAYS: int = 7     # validade usada quando a categoria nao tem parametro proprio

    # Scheduler
    RETRAIN_DAY_OF_WEEK: str = "mon"     # reajuste (fit) dos modelos L1; pulado sem venda nova
    RETRAIN_HOUR: int = 2                # 02:00
    RETRAIN_AFTER_UPLOAD_MINUTES: int = 10  # treino após planilha com venda nova; outro upload no intervalo adia
    # onde o treino roda: "local" (thread da API + agendador) ou "externo" (a API não treina:
    # script gravar_previsao em outra máquina; API no Render, ver services/disparo_treino.py)
    TRAINING_RUNNER: Literal["local", "externo"] = "local"
    DAILY_FORECAST_HOUR: int = 3         # confere o calendario; gera de novo a previsao so se ele mudou

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
