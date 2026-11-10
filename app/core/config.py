from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dev Log API"
    database_url: str = "sqlite:///./devlog.db"
    # Si está definida, crear/editar/borrar exige el header X-Admin-Key con este valor.
    # Si no (desarrollo local), la escritura queda abierta.
    admin_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        # Neon/Render dan URLs "postgres://" o "postgresql://"; SQLAlchemy necesita saber el driver.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @field_validator("admin_key")
    @classmethod
    def empty_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


settings = Settings()
