from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM API (CLIProxyAPI)
    llm_api_base_url: str = "http://192.168.88.115:8317/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3.6-35b-a3b-mtp"

    # App
    upload_dir: str = "./uploads"
    database_url: str = "sqlite+aiosqlite:///./spec_advisor.db"
    max_upload_size_mb: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Ensure upload directory exists
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
