import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    SERPAPI_API_KEY: str = "dummy_serpapi_key_replace_me"
    GEMINI_API_KEY: str = "dummy_gemini_key_replace_me"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    DATABASE_URL: str = "sqlite:///./npc.db"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    SERP_CACHE_TTL_HOURS: int = 12

    model_config = SettingsConfigDict(
        env_file=[
            str(BASE_DIR / ".env"),
            str(BASE_DIR.parent / ".env"),
            ".env"
        ],
        extra="ignore"
    )

    @property
    def is_serpapi_live(self) -> bool:
        k = self.SERPAPI_API_KEY.strip()
        return bool(k and not k.startswith("dummy"))

    @property
    def is_groq_live(self) -> bool:
        k = self.GROQ_API_KEY.strip()
        return bool(k and not k.startswith("dummy"))

    @property
    def is_gemini_live(self) -> bool:
        k = self.GEMINI_API_KEY.strip()
        return bool(k and not k.startswith("dummy"))

    @property
    def is_llm_live(self) -> bool:
        return self.is_groq_live or self.is_gemini_live

    @property
    def mock_mode(self) -> bool:
        return not (self.is_serpapi_live and self.is_llm_live)

settings = Settings()
