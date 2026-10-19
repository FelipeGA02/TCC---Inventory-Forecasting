from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Diretórios
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    RESULTS_DIR: str = "results"

    # Banco
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
    FORECAST_HORIZON_DAYS: int = 14       # dias previstos a partir do 1o dia sem dado
    FORECAST_STORED_DAYS: int = 60        # dias previstos e gravados por geracao; a API mostra 14 a partir de hoje
    TEST_DAYS: int = 28                   # hold-out para avaliacao
    MIN_OBSERVATIONS_DAYS: int = 180      # minimo de dias por unidade x categoria para treinar L1
    SEASONAL_PERIOD: int = 7             # m — sazonalidade semanal do SARIMAX
    LOG_CV_THRESHOLD: float = 0.7        # limiar (CV = std/mean) para log1p transform
    ALERT_VARIATION_THRESHOLD: float = 0.20  # previsao 7d 20% acima da media 4 semanas dispara alerta
    MAX_UPLOAD_MB: int = 50

    # Politica de reposicao (L3)
    SAFETY_STOCK_DAYS: int = 2           # estoque de seguranca em dias de demanda prevista
    SHELF_LIFE_DEFAULT_DAYS: int = 7     # validade usada quando a categoria nao tem parametro proprio

    # Previsao semanal (backend/services/forecast_service.py). O cliente envia a base
    # atualizada toda terca; o pre-processamento publica em PROCESSED_DIR e a previsao le
    # dali. Caminhos relativos sao resolvidos a partir de `ia-predictor/`.
    PROCESSED_DIR: str = "data/processed"
    FORECAST_LOAD_WEEKDAY: int = 1        # dia da carga semanal (0 = segunda; 1 = terca)
    TRAIN_WINDOW_DAYS: int = 425          # janela deslizante (treino da 1a origem dos testes)
    BACKTEST_ORIGINS: int = 52            # origens semanais do backtest (um ano)
    ADI_CUTOFF: float = 1.32              # produto regular — Syntetos, Boylan & Croston (2005)
    FORECAST_WORKERS: int = 0             # processos em paralelo; 0 = nucleos - 2

    # Scheduler
    RETRAIN_DAY_OF_WEEK: str = "tue"     # retreino + previsao semanal, no dia da carga
    RETRAIN_HOUR: int = 23               # 23:00 — depois da carga do dia (pula se a base nao mudou)
    DAILY_FORECAST_HOUR: int = 3         # confere o calendario; gera de novo a previsao so se ele mudou

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
