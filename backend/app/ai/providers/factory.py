from app.ai.config import ai_settings, embedding_settings
from app.ai.providers.base import EmbeddingProvider, LLMProvider
from app.ai.providers.openai_compatible import OpenAICompatibleEmbeddingProvider, OpenAICompatibleProvider


def get_provider() -> LLMProvider:
    settings = ai_settings()
    return OpenAICompatibleProvider(settings)


def get_embedding_provider() -> EmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider(embedding_settings())
