from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Wayfarer API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    database_url: str = Field(
        default="postgresql+psycopg://wayfarer:wayfarer@localhost:5433/wayfarer",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    openai_api_key: str = Field(default="YOUR_OPENAI_API_KEY", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="llama3.1", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")

    tripadvisor_api_key: str = Field(
        default="YOUR_TRIPADVISOR_API_KEY",
        alias="TRIPADVISOR_API_KEY",
    )
    google_places_api_key: str = Field(
        default="YOUR_GOOGLE_PLACES_API_KEY",
        alias="GOOGLE_PLACES_API_KEY",
    )

    default_llm_provider: str = Field(default="openai", alias="DEFAULT_LLM_PROVIDER")
    default_embed_provider: str = Field(default="ollama", alias="DEFAULT_EMBED_PROVIDER")

    frontend_cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="FRONTEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def frontend_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_cors_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()