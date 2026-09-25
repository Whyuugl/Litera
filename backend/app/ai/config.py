import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AISettings:
    provider: str
    api_key: str
    model: str
    base_url: str
    temperature: float
    max_output_tokens: int


@lru_cache
def ai_settings() -> AISettings:
    provider = os.getenv("AI_PROVIDER", "openai-compatible").strip().lower()
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()
    if provider != "openai-compatible":
        raise RuntimeError("AI_PROVIDER must be openai-compatible")
    if not api_key or not model:
        raise RuntimeError("AI_API_KEY and AI_MODEL must be configured")
    try:
        temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))
        max_output_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "900"))
    except ValueError as exc:
        raise RuntimeError("AI temperature and token settings must be numeric") from exc
    if not 0 <= temperature <= 2 or max_output_tokens <= 0:
        raise RuntimeError("AI temperature or token limit is outside the allowed range")
    return AISettings(provider, api_key, model, base_url, temperature, max_output_tokens)
