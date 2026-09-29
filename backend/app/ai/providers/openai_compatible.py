import httpx

from app.ai.config import AISettings, EmbeddingSettings
from app.ai.providers.base import AIProviderError, EmbeddingProvider, GeneratedText, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai-compatible"

    def __init__(self, settings: AISettings):
        self.settings = settings
        self.model = settings.model

    async def _generate(self, system: str, prompt: str, *, structured: bool) -> GeneratedText:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": self.settings.temperature,
                    "max_tokens": self.settings.max_output_tokens,
                }
                if structured:
                    payload["response_format"] = {"type": "json_object"}
                response = await client.post(
                    f"{self.settings.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.api_key}"},
                    json=payload,
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

    async def generate(self, system: str, prompt: str) -> GeneratedText:
        return await self._generate(system, prompt, structured=False)

    async def generate_structured(self, system: str, prompt: str) -> GeneratedText:
        return await self._generate(system, prompt, structured=True)


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = "openai-compatible"

    def __init__(self, settings: EmbeddingSettings):
        self.settings = settings
        self.model = settings.model
        self.dimensions = settings.dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.settings.base_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {self.settings.api_key}"},
                    json={"model": self.model, "input": texts, "dimensions": self.dimensions},
                )
                response.raise_for_status()
                data = sorted(response.json()["data"], key=lambda item: item["index"])
                vectors = [item["embedding"] for item in data]
                if len(vectors) != len(texts) or any(len(vector) != self.dimensions for vector in vectors):
                    raise ValueError("invalid embedding response dimensions")
                return vectors
        except Exception as exc:
            raise AIProviderError("Embedding provider request failed") from exc
