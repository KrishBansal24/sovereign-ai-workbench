from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.services.knowledge_service import knowledge_service
from app.services.document_service import DocumentNotFoundError
from app.services.embedding_service import EmbeddingError
from app.services.ollama_service import OllamaUnavailableError, ollama_service
from app.services.task_classifier import Classification
from app.services.model_router import model_router

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
class Search(BaseModel): query: str = Field(min_length=1); top_k: int = Field(default=settings.rag_top_k, ge=1, le=20)
class Ask(BaseModel): question: str = Field(min_length=1)
def fail(error):
    if isinstance(error, DocumentNotFoundError): raise HTTPException(404, "Document not found.")
    if isinstance(error, (EmbeddingError, OllamaUnavailableError)): raise HTTPException(503, "Local embedding service is unavailable.")
    raise HTTPException(422, str(error))
@router.post("/documents/{document_id}/index")
def index(document_id: str):
    try: return knowledge_service.index(document_id)
    except Exception as error: fail(error)
@router.get("/documents")
def documents(): return {"documents": __import__('app.services.vector_store_service', fromlist=['vector_store']).vector_store.documents()}
@router.delete("/documents/{document_id}")
def remove(document_id: str):
    if not knowledge_service.remove(document_id): raise HTTPException(404, "Indexed document not found.")
    return {"document_id": document_id, "removed": True}
@router.post("/search")
def search(request: Search):
    try: return {"query": request.query, "results": knowledge_service.search(request.query, request.top_k)}
    except Exception as error: fail(error)
@router.post("/ask")
def ask(request: Ask):
    try: results = knowledge_service.search(request.question, settings.rag_top_k)
    except Exception as error: fail(error)
    if not results: return {"answer": "The local knowledge base does not provide sufficient information.", "sources": [], "processing": "local"}
    context = "\n\n".join(f"[{r['chunk_id']}] {r['text']}" for r in results)
    selected, routing = model_router.route(Classification("document_analysis", .9, "rag"))
    prompt = f"Use only this local context. If insufficient, say so.\nCONTEXT:\n{context}\n\nQUESTION: {request.question}"
    try: answer = ollama_service.chat_with_model(selected.ollama_model, prompt)
    except Exception as error: fail(error)
    return {"answer": answer, "model": selected.ollama_model, "sources": [{k:r[k] for k in ('document_id','filename','chunk_id')} for r in results], "processing": "local"}
