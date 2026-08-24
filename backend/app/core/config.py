"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://compta:compta@localhost:5432/comptaflow"
    database_url_sync: str = "postgresql://compta:compta@localhost:5432/comptaflow"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Mistral
    mistral_api_key: str = ""
    mistral_ocr_model: str = "mistral-ocr-latest"

    # Stripe — un price ID par plan (stripe_price_id_monthly = legacy, plan cabinet)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_monthly: str = ""
    stripe_price_id_decouverte: str = ""
    stripe_price_id_cabinet: str = ""
    stripe_price_id_cabinet_plus: str = ""

    def stripe_price_for_plan(self, plan: str) -> str:
        """Price ID Stripe du plan ('' si non configuré)."""
        mapping = {
            "decouverte": self.stripe_price_id_decouverte,
            "cabinet": self.stripe_price_id_cabinet or self.stripe_price_id_monthly,
            "cabinet_plus": self.stripe_price_id_cabinet_plus,
        }
        return mapping.get(plan, "")

    # App
    app_secret_key: str = "change-me-in-production"
    debug: bool = False
    upload_dir: str = "/tmp/comptaflow/uploads"
    max_upload_size_mb: int = 20
    # Bloque l'upload si trial expiré et pas d'abonnement (activer en prod)
    enforce_subscription: bool = False
    # Origines CORS autorisées, séparées par des virgules
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Liste des origines CORS, nettoyée."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
