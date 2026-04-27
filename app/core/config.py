from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Resume Engine"
    debug: bool = False

    database_url: str = "sqlite:///./resume_engine.db"

    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    max_upload_mb: int = 5
    allowed_extensions: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 30


settings = Settings()
