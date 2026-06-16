import voyageai

from config import settings
from contracts.embedder import Embedder


class VoyageEmbedder(Embedder):
    def __init__(self) -> None:
        self._client: voyageai.AsyncClient | None = None

    @property
    def client(self) -> voyageai.AsyncClient:
        if self._client is None:
            if not settings.voyage_api_key:
                raise RuntimeError("VOYAGE_API_KEY is not configured")
            self._client = voyageai.AsyncClient(api_key=settings.voyage_api_key)
        return self._client

    async def get_embedding(self, texts: str | list[str], *, input_type: str) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]

        response = await self.client.embed(
            texts,
            model=settings.voyage_embed_model,
            input_type=input_type,
        )
        return response.embeddings

    async def get_reranked_context(self, query: str, contexts: list[str], top_k: int | None = None):
        return await self.client.rerank(
            query,
            contexts,
            model=settings.voyage_rerank_model,
            top_k=top_k or settings.voyage_rerank_top_k,
        )


voyage_embedder = VoyageEmbedder()
