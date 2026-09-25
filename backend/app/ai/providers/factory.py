from app.ai.config import ai_settings
from app.ai.providers.base import LLMProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider


def get_provider() -> LLMProvider:
    settings = ai_settings()
    return OpenAICompatibleProvider(settings)
