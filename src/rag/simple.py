from config import settings
from services.pinecone import get_generic_hook
from services.voyage import voyage_embedder
from utils.logging import get_logger

logger = get_logger(__name__)
embedder = voyage_embedder


def _metadata_to_document(metadata: dict) -> str:
    title = metadata.get("title", "")
    summary = metadata.get("summary", "")
    content = metadata.get("content") or metadata.get("text") or metadata.get("chunk_text") or ""

    parts = [part for part in (title, summary, content) if part]
    return ". ".join(parts)


def _metadata_to_chunk(metadata: dict, *, relevance_score: float | None = None) -> dict:
    return {
        "text": _metadata_to_document(metadata),
        "title": metadata.get("title"),
        "summary": metadata.get("summary"),
        "source": metadata.get("source"),
        "url": metadata.get("url"),
        "news_id": metadata.get("news_id"),
        "relevance_score": relevance_score,
    }


async def search_similar_chunks(
    *,
    query: str,
    top_k: int | None = None,
    namespace: str | None = None,
) -> dict:
    """Retrieve the most relevant knowledge-base chunks for a query."""
    if not settings.pinecone_serverless_api_key:
        return {
            "query": query,
            "chunks": [],
            "total": 0,
            "error": "RAG is not configured. Missing Pinecone API key.",
        }

    result_top_k = top_k or settings.rag_top_k
    candidate_k = max(result_top_k, settings.rag_candidate_k)
    pinecone_namespace = namespace or settings.pinecone_namespace
    pinecone_hook = await get_generic_hook()

    try:
        logger.info("[rag] generating embedding for query")
        query_embeddings = await embedder.get_embedding(texts=query, input_type="query")
        search_results = await pinecone_hook.query_document(
            vector=query_embeddings[0],
            top_k=candidate_k,
            namespace=pinecone_namespace,
        )

        matches = search_results.get("matches", [])
        if not matches:
            return {"query": query, "chunks": [], "total": 0}

        documents: list[str] = []
        metadata_rows: list[dict] = []

        for match in matches:
            metadata = match.get("metadata") or {}
            document = _metadata_to_document(metadata)
            if not document:
                continue
            documents.append(document)
            metadata_rows.append(metadata)

        if not documents:
            return {"query": query, "chunks": [], "total": 0}

        logger.info("[rag] reranking %s documents", len(documents))
        reranked = await embedder.get_reranked_context(
            query=query,
            contexts=documents,
            top_k=min(result_top_k, len(documents)),
        )

        chunks = [
            _metadata_to_chunk(
                metadata_rows[result.index],
                relevance_score=result.relevance_score,
            )
            for result in reranked.results
        ]

        return {"query": query, "chunks": chunks, "total": len(chunks)}
    except Exception as exc:
        logger.error(f"[rag] search_similar_chunks failed: {exc}")
        return {
            "query": query,
            "chunks": [],
            "total": 0,
            "error": str(exc),
        }
