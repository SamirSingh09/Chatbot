from functools import lru_cache
import os
from pathlib import Path
import dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY") or dotenv.get_key(BASE_DIR / ".env", "OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    max_upload_mb: int = 25
    chunk_size: int = 900
    chunk_overlap: int = 150
    data_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    index_path: Path = BASE_DIR / "data" / "rag_index.joblib"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Settings loaded: {settings}")   
    return settings
