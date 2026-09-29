from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIProviderError(Exception):
    pass


@dataclass(frozen=True)
class GeneratedText:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(self, system: str, prompt: str) -> GeneratedText:
        raise NotImplementedError

    async def generate_structured(self, system: str, prompt: str) -> GeneratedText:
        return await self.generate(system, prompt)


class EmbeddingProvider(ABC):
    name: str
    model: str
    dimensions: int

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]
