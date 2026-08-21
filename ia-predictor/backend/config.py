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

    # Pipeline ML
    TOP_N_PRODUCTS: int = 20          # produtos a incluir no pipeline automático
    TEST_MONTHS: int = 3              # hold-out para avaliação
    FUTURE_MONTHS: int = 3            # horizonte de previsão futuro
    MIN_OBSERVATIONS: int = 15        # mínimo para treinar modelo
    LOG_CV_THRESHOLD: float = 0.7     # limiar (CV = std/mean) para log1p transform
    ALERT_STOCK_DAYS: int = 21        # janela de reposição (3 semanas)
    ALERT_VARIATION_THRESHOLD: float = 0.20  # 20% acima da média recente dispara alerta
    MAX_UPLOAD_MB: int = 50

    # Scheduler
    RETRAIN_DAY_OF_WEEK: str = "mon"  # segunda-feira
    RETRAIN_HOUR: int = 2             # 02:00

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
