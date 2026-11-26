import pytest
from pathlib import Path
from app.core.config import Settings
from app.database.session import normalized_url
from app.llm.factory import create_llm, descriptor
from app.main import evaluation_report_path

def test_provider_switching_is_configuration_only():
    ollama=Settings(llm_provider="ollama",ollama_model="qwen3:8b")
    gemini=Settings(llm_provider="gemini",gemini_api_key="test",gemini_model="gemini-test")
    openai=Settings(llm_provider="openai",openai_api_key="test",openai_model="gpt-test")
    assert descriptor(ollama).provider=="ollama"
    assert descriptor(ollama).model=="qwen3:8b"
    assert descriptor(gemini).provider=="gemini"
    assert descriptor(gemini).configured is True
    assert descriptor(openai).provider=="openai"
    assert descriptor(openai).model=="gpt-test"
    assert openai.active_llm_model=="gpt-test"
    assert ollama.active_llm_model=="qwen3:8b"
    assert gemini.active_llm_model=="gemini-test"

def test_missing_gemini_key_is_explicitly_unconfigured():
    assert descriptor(Settings(llm_provider="gemini",gemini_api_key=None)).configured is False

def test_gemini_defaults_are_production_safe_and_ollama_is_unchanged():
    gemini=Settings(_env_file=None,llm_provider="gemini",gemini_api_key="test")
    ollama=Settings(_env_file=None,llm_provider="ollama")
    assert gemini.gemini_model=="gemini-3.8-flash"
    assert gemini.gemini_timeout_seconds==40
    assert ollama.ollama_model=="qwen3:8b"
    assert ollama.llm_timeout_seconds==60

def test_gemini_factory_uses_supported_timeout_and_retry_parameters():
    model=create_llm(Settings(_env_file=None,llm_provider="gemini",gemini_api_key="test",gemini_model="test-model",gemini_timeout_seconds=40))
    assert model.model in {"test-model", "models/test-model"}
    assert model.timeout==40
    assert model.max_retries==0

def test_development_secret_default_is_allowed_without_production_credentials():
    settings=Settings(_env_file=None,app_env="development")
    assert settings.secret_key=="local-development-only-secret"

def test_production_requires_explicit_secret_key():
    with pytest.raises(ValueError,match="SECRET_KEY must be explicitly configured"):
        Settings(_env_file=None,app_env="production")

def test_production_rejects_empty_or_whitespace_secret_key():
    for value in ("", "   "):
        with pytest.raises(ValueError,match="SECRET_KEY must be explicitly configured"):
            Settings(_env_file=None,app_env="production",secret_key=value)

@pytest.mark.parametrize("placeholder", [
    "change-me-in-production",
    "LOCAL-DEVELOPMENT-ONLY-SECRET",
    "Replace-With-A-Random-Local-Development-Secret",
])
def test_production_rejects_known_placeholders_case_insensitively(placeholder):
    with pytest.raises(ValueError,match="SECRET_KEY must be explicitly configured"):
        Settings(_env_file=None,app_env="production",secret_key=placeholder)

def test_production_rejects_short_secret_key():
    with pytest.raises(ValueError,match="SECRET_KEY must be explicitly configured"):
        Settings(_env_file=None,app_env="production",secret_key="short-secret")

def test_production_accepts_explicit_secret_key():
    settings=Settings(_env_file=None,app_env="production",secret_key="test-only-production-secret-with-32-plus-chars")
    assert settings.app_env=="production"

def test_render_configuration_sets_production_environment():
    render_config=Path(__file__).resolve().parents[2]/"render.yaml"
    assert "- key: APP_ENV\n        value: production" in render_config.read_text(encoding="utf-8")

def test_factory_constructs_ollama_without_network_call():
    model=create_llm(Settings(llm_provider="ollama",ollama_base_url="http://127.0.0.1:11434",ollama_model="qwen3:8b"))
    assert model.__class__.__name__ == "ChatOllama"

def test_postgres_urls_are_normalized_for_psycopg():
    assert normalized_url("postgresql://user:pass@host/db").startswith("postgresql+psycopg://")
    assert normalized_url("sqlite:///./test.db")=="sqlite:///./test.db"

def test_evaluation_report_path_is_repository_relative():
    assert evaluation_report_path().as_posix().endswith("backend/evaluation/results/latest.json")
