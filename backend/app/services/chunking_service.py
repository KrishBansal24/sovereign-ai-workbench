from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    chunk_index: int
    text: str
    character_count: int


class ChunkingService:
    def chunk(self, document_id: str, text: str) -> list[TextChunk]:
        size, overlap = settings.rag_chunk_size, settings.rag_chunk_overlap
        chunks: list[TextChunk] = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = text.rfind("\n", start, end)
                if boundary > start + size // 2:
                    end = boundary
            value = text[start:end].strip()
            if value:
                index = len(chunks)
                chunks.append(TextChunk(f"{document_id}:{index}", index, value, len(value)))
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
        return chunks


chunking_service = ChunkingService()
