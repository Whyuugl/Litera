import httpx

from app.ai.config import AISettings
from app.ai.providers.base import AIProviderError, GeneratedText, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai-compatible"

    def __init__(self, settings: AISettings):
        self.settings = settings
        self.model = settings.model

    async def generate(self, system: str, prompt: str) -> GeneratedText:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.settings.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": self.settings.temperature,
                        "max_tokens": self.settings.max_output_tokens,
                    },
                )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"].strip()
                if not content:
                    raise ValueError("empty response")
                usage = body.get("usage", {})
                return GeneratedText(
                    content,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                )
        except Exception as exc:
            raise AIProviderError("AI provider request failed") from exc
