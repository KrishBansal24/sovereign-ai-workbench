"""Text chunking for local RAG indexing.

Chunking keeps adjacent text overlap so a fact near a boundary remains
retrievable without embedding entire documents as one vector.
"""

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class TextChunk:
    """A text segment produced from one locally stored source document.

    The identifier combines the source document ID and ordered chunk index so
    later retrieval results can always be traced to their original content.
    """
    chunk_id: str
    chunk_index: int
    text: str
    character_count: int


class ChunkingService:
    """Split extracted document text into overlapping, source-traceable chunks."""

    def chunk(self, document_id: str, text: str) -> list[TextChunk]:
        """Create chunks using configured character limits and overlap.

        Args:
            document_id: Controlled source document identifier.
            text: Previously extracted local document text.

        Returns:
            Ordered chunks whose IDs preserve document and chunk position.
        """
        chunk_size = settings.rag_chunk_size
        overlap = settings.rag_chunk_overlap
        chunks: list[TextChunk] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            # Prefer a newline boundary when it retains most of the planned
            # chunk; this preserves readable document structure for RAG.
            if end < len(text):
                boundary = text.rfind("\n", start, end)
                if boundary > start + chunk_size // 2:
                    end = boundary
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_index = len(chunks)
                chunks.append(
                    TextChunk(
                        chunk_id=f"{document_id}:{chunk_index}",
                        chunk_index=chunk_index,
                        text=chunk_text,
                        character_count=len(chunk_text),
                    )
                )
            if end == len(text):
                break
            # Advance by less than a full chunk to retain nearby context at
            # boundaries. The +1 guard guarantees progress for bad settings.
            start = max(end - overlap, start + 1)
        return chunks


chunking_service = ChunkingService()
