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
