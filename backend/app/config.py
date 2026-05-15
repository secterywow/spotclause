from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://spotclause:spotclause@localhost:5432/spotclause"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168  # 7 days

    # LLM
    llm_api_base: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    # Stripe (test mode)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email (Resend)
    resend_api_key: str = ""
    resend_from_email: str = ""

    # App
    app_name: str = "SpotClause"
    debug: bool = True

    # Cost Control
    daily_cost_limit: float = 0.50
    max_follow_up_rounds: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
