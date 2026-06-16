from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestionSource:
    """Raw input passed into an ingestion pipeline."""

    content: str | bytes
    source_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Structured document produced by the parse stage."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """Cleaned and normalized document produced by the process stage."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """A single chunk ready for embedding and vector upsert."""

    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Summary of a completed ingestion run."""

    document_id: str
    chunks_upserted: int
    namespace: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IngestionPipeline(ABC):
    """Contract for document ingestion pipelines.

    Each implementation must provide four stages in order:
    parse -> process -> chunk -> upsert.
    """

    @abstractmethod
    async def parse(self, source: IngestionSource) -> ParsedDocument:
        """Extract structured text and metadata from a raw source."""

    @abstractmethod
    async def process(self, document: ParsedDocument) -> ProcessedDocument:
        """Clean, normalize, and enrich the parsed document."""

    @abstractmethod
    async def chunk(self, document: ProcessedDocument) -> list[DocumentChunk]:
        """Split the processed document into retrieval-ready chunks."""

    @abstractmethod
    async def upsert(
        self,
        chunks: list[DocumentChunk],
        *,
        namespace: str | None = None,
    ) -> IngestionResult:
        """Embed and persist chunks to the vector store."""

    async def run(
        self,
        source: IngestionSource,
        *,
        namespace: str | None = None,
    ) -> IngestionResult:
        """Execute the full ingestion pipeline."""
        parsed = await self.parse(source)
        processed = await self.process(parsed)
        chunks = await self.chunk(processed)
        return await self.upsert(chunks, namespace=namespace)
