from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_title: str = "Accountant2 API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/accountant2"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    egrul_cache_ttl: int = 7200  # 2 hours in seconds

    # External API
    egrul_api_base_url: str = "https://egrul.org"


settings = Settings()
