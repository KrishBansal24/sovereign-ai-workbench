"""Knowledge-base routes delegating local RAG work to application services.

These routes orchestrate request validation and HTTP error mapping only.
Chunking, embedding, vector retrieval, and local model execution remain in the
services package so the API boundary stays thin and auditable.
"""

import re
from typing import NoReturn

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.documents.document_service import DocumentNotFoundError
from app.services.knowledge.embedding_service import EmbeddingError
from app.services.knowledge.knowledge_service import IndexingResult, RetrievedChunk, knowledge_service
from app.services.llm.model_router import model_router
from app.services.llm.ollama_service import OllamaUnavailableError, ollama_service
from app.services.llm.task_classifier import Classification
from app.services.knowledge.vector_store_service import vector_store


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
MAX_ANSWER_SOURCES = 2
# Answering requires stronger evidence than exploratory search. A weak nearest
# neighbour may still be useful to inspect, but it must not trigger a model
# response that could turn it into an unsupported claim.
MIN_ANSWER_SIMILARITY = 0.55
_QUESTION_STOPWORDS = frozenset({
    "a", "an", "and", "according", "all", "answer", "any", "are", "as", "at", "available",
    "based", "be", "brief", "bullet", "by", "cite", "claim", "clearly", "describe", "do",
    "document", "documents", "evidence", "explain", "for", "following", "from", "has", "have",
    "how", "i", "in", "indexed", "information", "is", "it", "knowledge", "list", "local",
    "of", "only", "or", "pages", "please", "point", "points", "provide", "provided", "relevant",
    "reliably", "report", "short", "source", "sources", "summarize", "supported", "the", "this",
    "to", "use", "using", "was", "what", "when", "where", "which", "who", "why", "with", "would",
})
_MONTHS = frozenset({
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
})


def _normalise_anchor(token: str) -> str:
    """Apply a tiny, predictable morphology normalisation for evidence checks."""
    if token.endswith("ating"):
        return f"{token[:-5]}ate"
    if token.endswith("ation"):
        return f"{token[:-5]}ate"
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _has_sufficient_answer_evidence(question: str, results: list[RetrievedChunk]) -> bool:
    """Return whether retrieved text supports the specific terms in a question.

    Semantic retrieval can rank a vaguely related chunk highly. Before asking a
    model to phrase an answer, require concrete question anchors to appear in
    retrieved local context. Dates and numbers are strict anchors: a request
    scoped to ``August 2026`` cannot be grounded by evidence that does not
    mention that period. This is answer-generation-only; search remains open.
    """
    question_tokens = re.findall(r"[a-z0-9]+", question.lower())
    evidence_tokens = {
        _normalise_anchor(token)
        for result in results
        for token in re.findall(r"[a-z0-9]+", result["text"].lower())
    }
    strict_anchors = {
        token for token in question_tokens if token.isdigit() or token in _MONTHS
    }
    if strict_anchors and not all(_normalise_anchor(token) in evidence_tokens for token in strict_anchors):
        return False

    anchors = {
        _normalise_anchor(token)
        for token in question_tokens
        if token not in _QUESTION_STOPWORDS and len(token) >= 4 and not token.isdigit()
    }
    if len(anchors) <= 2:
        return not anchors or bool(anchors & evidence_tokens)
    covered = len(anchors & evidence_tokens)
    return covered >= 2 and covered / len(anchors) >= 0.4


class SearchRequest(BaseModel):
    """Validated semantic-search request against locally indexed documents."""

    query: str = Field(min_length=1, description="Question or phrase to retrieve local evidence for.")
    top_k: int = Field(
        default=settings.rag_top_k,
        ge=1,
        le=20,
        description="Maximum number of highest-similarity source chunks to return.",
    )


class AskRequest(BaseModel):
    """Validated question answered only from retrieved local source chunks."""

    question: str = Field(min_length=1, description="Question to answer from the local knowledge base.")


def _raise_knowledge_error(error: Exception) -> NoReturn:
    """Translate known local-service failures into stable HTTP responses.

    Args:
        error: Exception raised while indexing, embedding, retrieving, or
            generating a locally grounded answer.
    """
    if isinstance(error, DocumentNotFoundError):
        raise HTTPException(status_code=404, detail="Document not found.") from error
    if isinstance(error, (EmbeddingError, OllamaUnavailableError)):
        raise HTTPException(
            status_code=503,
            detail="Local embedding service is unavailable.",
        ) from error
    raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/documents/{document_id}/index",
    summary="Index an uploaded document into the local knowledge base",
    description="Chunks, embeds, and stores document text through local RAG services.",
)
def index_document(document_id: str) -> IndexingResult:
    """Delegate document indexing to ``KnowledgeService``.

    Args:
        document_id: Server-issued ID of a stored source document.

    Returns:
        Indexing status and the configured local embedding model.
    """
    try:
        return knowledge_service.index(document_id)
    except Exception as error:
        _raise_knowledge_error(error)


@router.get(
    "/documents",
    summary="List documents currently indexed for local retrieval",
)
def list_indexed_documents() -> dict[str, list[dict[str, str]]]:
    """List indexed source documents from the persistent local vector store."""
    return {"documents": vector_store.documents()}


@router.delete(
    "/documents/{document_id}",
    summary="Remove one document's local knowledge index",
)
def remove_indexed_document(document_id: str) -> dict[str, str | bool]:
    """Remove vectors and source records for one document, not its file.

    Args:
        document_id: Server-issued ID of the indexed source document.

    Returns:
        Document ID and removal confirmation.
    """
    if not knowledge_service.remove(document_id):
        raise HTTPException(status_code=404, detail="Indexed document not found.")
    return {"document_id": document_id, "removed": True}


@router.post(
    "/search",
    summary="Retrieve source-traceable local knowledge chunks",
    description="Embeds the query locally and returns the highest-similarity indexed chunks.",
)
def search_knowledge(request: SearchRequest) -> dict[str, str | list[RetrievedChunk]]:
    """Delegate semantic retrieval to ``KnowledgeService``.

    Args:
        request: Query and result limit validated at the HTTP boundary.

    Returns:
        Original query and source-traceable local retrieval results.
    """
    try:
        return {
            "query": request.query,
            "results": knowledge_service.search(request.query, request.top_k),
        }
    except Exception as error:
        _raise_knowledge_error(error)


@router.post(
    "/ask",
    summary="Answer using retrieved local knowledge only",
    description="Retrieves local context and instructs a registered local model to remain grounded in it.",
)
def ask_knowledge(request: AskRequest) -> dict[str, object]:
    """Retrieve local evidence and ask a local model for a grounded answer.

    Args:
        request: Question to answer from indexed source chunks.

    Returns:
        Local answer, selected model, source identifiers, and processing mode.
    """
    try:
        # The local Qwen deployment has a 4K context window. Passing every
        # search chunk (up to five 3K-character chunks) can consume that
        # window before an answer is generated. Keep answer generation bounded
        # to the strongest evidence; explicit search remains configurable.
        results = knowledge_service.search(request.question, min(settings.rag_top_k, MAX_ANSWER_SOURCES))
        results = [
            result for result in results
            if result["similarity_score"] >= max(settings.rag_min_similarity, MIN_ANSWER_SIMILARITY)
        ]
    except Exception as error:
        _raise_knowledge_error(error)

    if not results or not _has_sufficient_answer_evidence(request.question, results):
        return {
            "answer": "The local knowledge base does not provide sufficient information.",
            "sources": [],
            "processing": "local",
        }

    # SECURITY: retrieved text is the only context passed to the local model;
    # the grounding instruction prohibits inventing facts outside these sources.
    context = "\n\n".join(
        f"[{result['chunk_id']}] {result['text']}" for result in results
    )
    selected_model, _routing = model_router.route(
        Classification("document_analysis", 0.9, "rag")
    )
    prompt = (
        "Use only this local context. If insufficient, say so.\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {request.question}"
    )
    try:
        answer = ollama_service.chat_with_model(selected_model.ollama_model, prompt)
    except Exception as error:
        _raise_knowledge_error(error)
    return {
        "answer": answer,
        "model": selected_model.ollama_model,
        "sources": [
            {
                "document_id": result["document_id"],
                "filename": result["filename"],
                "chunk_id": result["chunk_id"],
                "page_numbers": sorted({int(number) for number in re.findall(r"\[Page\s+(\d+)\]", result["text"])}),
            }
            for result in results
        ],
        "processing": "local",
    }
