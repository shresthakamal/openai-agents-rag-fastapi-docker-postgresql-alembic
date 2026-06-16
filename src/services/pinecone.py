from pinecone import Pinecone, PineconeAsyncio

from config import settings


class AsyncPineconeClient:
    _instances: dict[str, "AsyncPineconeClient"] = {}

    @classmethod
    async def get_instance(cls) -> "AsyncPineconeClient":
        index_name = settings.pinecone_index
        if index_name not in cls._instances:
            instance = cls(index_name=index_name, host=settings.pinecone_host)
            await instance._initialize()
            cls._instances[index_name] = instance
        return cls._instances[index_name]

    def __init__(self, *, index_name: str, host: str) -> None:
        self.index_name = index_name
        self.host = host
        self._pc: Pinecone | None = None
        self._async_pc: PineconeAsyncio | None = None

    async def _initialize(self) -> None:
        if not settings.pinecone_serverless_api_key:
            raise RuntimeError("PINECONE_SERVERLESS_API_KEY is not configured")

        self._pc = Pinecone(api_key=settings.pinecone_serverless_api_key)
        self._async_pc = PineconeAsyncio(api_key=settings.pinecone_serverless_api_key)

    async def get_async_index(self):
        if self._pc is None:
            await self._initialize()
        return self._pc.IndexAsyncio(host=self.host)

    async def query_document(
        self,
        *,
        vector: list[float],
        top_k: int = 20,
        filter: dict | None = None,
        namespace: str | None = None,
    ) -> dict:
        async with await self.get_async_index() as index:
            return await index.query(
                vector=vector,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter,
            )

    async def cleanup(self) -> None:
        if self._async_pc is not None:
            await self._async_pc.close()
            self._async_pc = None


async def get_pinecone_client() -> AsyncPineconeClient:
    return await AsyncPineconeClient.get_instance()
