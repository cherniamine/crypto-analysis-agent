from dataclasses import dataclass
from app.core.config import Settings, get_settings

@dataclass(frozen=True)
class LLMDescriptor:
    provider: str
    model: str
    configured: bool

def descriptor(settings: Settings | None = None) -> LLMDescriptor:
    s=settings or get_settings(); provider=s.llm_provider.lower()
    configured=bool((provider=="ollama" and s.ollama_model) or (provider=="gemini" and s.gemini_api_key and s.gemini_model) or (provider=="openai" and s.openai_api_key and s.openai_model))
    model=s.ollama_model if provider=="ollama" else s.gemini_model if provider=="gemini" else s.openai_model
    return LLMDescriptor(provider,model,configured)

def create_llm(settings: Settings | None = None):
    s=settings or get_settings(); d=descriptor(s)
    if d.provider=="ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=s.ollama_model,base_url=s.ollama_base_url,temperature=0,timeout=s.llm_timeout_seconds)
    if d.provider=="gemini":
        if not s.gemini_api_key: raise RuntimeError("GEMINI_API_KEY is not configured")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=s.gemini_model,google_api_key=s.gemini_api_key,temperature=0,timeout=s.llm_timeout_seconds,max_retries=2)
    if d.provider=="openai":
        from langchain_openai import ChatOpenAI
        if not s.openai_api_key: raise RuntimeError("OPENAI_API_KEY is not configured")
        return ChatOpenAI(model=s.openai_model,api_key=s.openai_api_key,temperature=0,timeout=s.llm_timeout_seconds,max_retries=2)
    raise RuntimeError(f"Unsupported LLM provider: {d.provider}")
