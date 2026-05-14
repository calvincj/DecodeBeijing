from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root regardless of where uvicorn is launched from
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    database_url: str = "postgresql+asyncpg://decode:localdev@localhost:5432/decode_beijing"
    elasticsearch_url: str = "http://localhost:9200"
    deepl_api_key: str = ""
    openr_api_key: str = ""
    scraper_delay_seconds: float = 2.0
    scraper_user_agent: str = "Mozilla/5.0 (compatible; academic-research-bot/1.0)"


settings = Settings()
