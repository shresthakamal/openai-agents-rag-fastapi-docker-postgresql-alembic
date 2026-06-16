import json

from agents import function_tool

from config import settings
from rag.simple import search_similar_chunks
from utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
async def search_knowledge_base(query: str, top_k: int = settings.rag_top_k) -> str:
    """Search the knowledge base for content most relevant to a user question.

    Use this tool when the user asks about news, articles, products, policies,
    or other factual topics that may exist in the indexed knowledge base.

    Args:
        query: A focused search query derived from the user's question.
        top_k: Maximum number of relevant chunks to return.
    """
    logger.info("[search_knowledge_base] searching for query: %s", query)

    results = await search_similar_chunks(query=query, top_k=top_k)
    return json.dumps(results, indent=2)
