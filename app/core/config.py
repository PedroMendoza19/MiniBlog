from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dev Log API"
    database_url: str = "sqlite:///./devlog.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
