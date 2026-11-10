import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "MTCB - MEHTYS CODE BRIDGE"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Provider configuration: "ollama" or "mock"
    PROVIDER_TYPE: str = "ollama"

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # Cloud AI (Google Gemini) settings
    GEMINI_TIMEOUT_SECONDS: float = 90.0

    # Request validation limits
    MAX_CODE_SIZE_BYTES: int = 65536  # 64 KB
    MAX_INSTRUCTIONS_LENGTH: int = 1000

    # CORS configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
