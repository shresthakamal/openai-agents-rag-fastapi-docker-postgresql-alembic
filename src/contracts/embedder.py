from abc import ABC, abstractmethod


class Embedder(ABC):
    @abstractmethod
    async def get_embedding(self, texts: str | list[str], *, input_type: str) -> list[list[float]]:
        pass

    @abstractmethod
    async def get_reranked_context(self, query: str, contexts: list[str], top_k: int | None = None):
        pass
