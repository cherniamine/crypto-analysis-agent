from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS={"","change-me-in-production","local-development-only-secret","replace-in-production","generate-a-long-random-secret","replace-with-a-random-local-development-secret"}
MIN_PRODUCTION_SECRET_LENGTH=32

class Settings(BaseSettings):
    app_name: str = "Crypto Intelligence Agent"
    app_env: str = "development"
    openai_api_key: str | None = None
    freecryptoapi_api_key: str | None = None
    newsapi_api_key: str | None = None
    database_url: str = "sqlite:///./data/crypto_agent.db"
    secret_key: str = "local-development-only-secret"
    openai_model: str = "gpt-4o-mini"
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    news_evidence_limit: int = 5
    evidence_context_char_budget: int = 18000
    llm_timeout_seconds: int = 60
    model_config = SettingsConfigDict(env_file=(str(Path(__file__).resolve().parents[3] / ".env"), str(Path(__file__).resolve().parents[3] / ".env.local"), ".env"), extra="ignore")

    @model_validator(mode="after")
    def validate_security_configuration(self):
        if self.app_env.lower() in {"production","prod"}:
            normalized_secret=self.secret_key.strip()
            insecure_placeholders={value.lower() for value in INSECURE_SECRET_KEYS}
            if not normalized_secret or normalized_secret.lower() in insecure_placeholders or len(normalized_secret)<MIN_PRODUCTION_SECRET_LENGTH:
                raise ValueError("SECRET_KEY must be explicitly configured with at least 32 characters when APP_ENV=production")
        return self

    @property
    def active_llm_model(self) -> str:
        provider=self.llm_provider.lower()
        return self.ollama_model if provider=="ollama" else self.gemini_model if provider=="gemini" else self.openai_model

    def validate_runtime(self) -> list[str]:
        errors=[]
        if self.llm_provider.lower() not in {"ollama", "gemini", "openai"}: errors.append("LLM_PROVIDER must be ollama, gemini, or openai")
        if not self.database_url.startswith(("sqlite:", "postgresql:", "postgres:")): errors.append("DATABASE_URL must use sqlite or postgresql")
        return errors

@lru_cache
def get_settings() -> Settings:
    return Settings()
