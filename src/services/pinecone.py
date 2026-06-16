from pinecone import Pinecone, PineconeAsyncio, ServerlessSpec

from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


class AsyncPineconeServerlessHook:
    _instances: dict[str, "AsyncPineconeServerlessHook"] = {}

    @classmethod
    async def get_instance(cls, index_name: str, host: str) -> "AsyncPineconeServerlessHook":
        """Get or create a singleton instance for an index."""
        if index_name not in cls._instances:
            instance = cls(index_name, host)
            await instance._initialize()
            cls._instances[index_name] = instance
        return cls._instances[index_name]

    def __init__(self, index_name: str, host: str) -> None:
        self.index_name = index_name
        self.host = host
        self.pc: Pinecone | None = None
        self.async_pc: PineconeAsyncio | None = None

    async def _initialize(self) -> None:
        """Initialize Pinecone connection and ensure index exists."""
        if not settings.pinecone_serverless_api_key:
            raise RuntimeError("PINECONE_SERVERLESS_API_KEY is not configured")

        self.pc = Pinecone(api_key=settings.pinecone_serverless_api_key)
        self.async_pc = PineconeAsyncio(api_key=settings.pinecone_serverless_api_key)

        has_index = await self.async_pc.has_index(self.index_name)

        if not has_index:
            await self.async_pc.create_index(
                name=self.index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                deletion_protection="disabled",
            )
            logger.info("Created index %s", self.index_name)
        else:
            logger.info("Index %s already exists", self.index_name)

    async def get_async_index(self):
        """Get the async index object."""
        if not self.pc:
            await self._initialize()
        return self.pc.IndexAsyncio(host=self.host)

    async def upsert_document(
        self,
        vectors: list[dict],
        namespace: str | None = None,
    ) -> dict:
        """Upsert vectors to the index."""
        async with await self.get_async_index() as index:
            return await index.upsert(vectors=vectors, namespace=namespace, batch_size=32)

    async def query_document(
        self,
        *,
        vector: list[float],
        sparse_vector: dict | None = None,
        top_k: int = 20,
        filter: dict | None = None,
        namespace: str | None = None,
        alpha: float = 0.5,
    ) -> dict:
        """Query the index with dense and optional sparse vectors."""
        query_kwargs: dict = {
            "vector": vector,
            "top_k": top_k,
            "namespace": namespace,
            "include_values": True,
            "include_metadata": True,
            "filter": filter,
        }
        if sparse_vector is not None:
            query_kwargs["sparse_vector"] = sparse_vector
            query_kwargs["alpha"] = alpha

        async with await self.get_async_index() as index:
            return await index.query(**query_kwargs)

    async def delete_document(self, id: str, namespace: str | None = None) -> bool:
        """Delete document by ID prefix."""
        namespace = str(namespace) if namespace else None
        logger.info("Deleting document with ID: %s", id)

        async with await self.get_async_index() as index:
            ids_to_delete: list[str] = []
            async for batch in index.list(prefix=f"{id}#", namespace=namespace):
                if batch:
                    ids_to_delete.extend(batch)

            if ids_to_delete:
                batch_size = 1000
                for i in range(0, len(ids_to_delete), batch_size):
                    batch_ids = ids_to_delete[i : i + batch_size]
                    logger.info(
                        "Deleting batch %s with %s IDs",
                        i // batch_size + 1,
                        len(batch_ids),
                    )
                    await index.delete(ids=batch_ids, namespace=namespace)

            return True

    async def delete_namespace(self, namespace: str | None = None) -> bool:
        """Delete all vectors in a namespace."""
        namespace = str(namespace) if namespace else None
        async with await self.get_async_index() as index:
            await index.delete(delete_all=True, namespace=namespace)
            return True

    async def update_metadata(
        self,
        id: str,
        categories: list[str],
        namespace: str | None = None,
    ) -> bool:
        """Update metadata for documents with ID prefix."""
        namespace = str(namespace) if namespace else None
        logger.info("Updating document with ID: %s", id)

        async with await self.get_async_index() as index:
            ids_to_update: list[str] = []
            async for batch in index.list(prefix=f"{id}#", namespace=namespace):
                if batch:
                    ids_to_update.extend(batch)

            for doc_id in ids_to_update:
                await index.update(
                    id=doc_id,
                    namespace=namespace,
                    set_metadata={"categories": categories},
                )

            return True

    async def cleanup(self) -> None:
        """Cleanup resources and close connections."""
        if self.async_pc:
            try:
                await self.async_pc.close()
            except Exception as exc:
                logger.error("Error during Pinecone cleanup: %s", exc)
            finally:
                self.async_pc = None

    @classmethod
    async def cleanup_all(cls) -> None:
        """Close all singleton instances."""
        for instance in list(cls._instances.values()):
            await instance.cleanup()
        cls._instances.clear()


async def get_generic_hook() -> AsyncPineconeServerlessHook:
    return await AsyncPineconeServerlessHook.get_instance(
        index_name=settings.pinecone_index,
        host=settings.pinecone_host,
    )


async def get_pinecone_client() -> AsyncPineconeServerlessHook:
    return await get_generic_hook()
