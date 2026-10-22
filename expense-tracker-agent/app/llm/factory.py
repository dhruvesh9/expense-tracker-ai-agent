from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAIProvider

# name used in .env  ->  class that implements it
PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider  # lazy: built on first use, so importing the app doesn't need a key
    if _provider is None:
        name = get_settings().llm.lower()
        if name not in PROVIDERS:
            raise ValueError(f"Unknown LLM '{name}'. Choose one of: {', '.join(PROVIDERS)}")
        _provider = PROVIDERS[name]()
    return _provider
