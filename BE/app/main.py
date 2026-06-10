from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.rag_service import RagService
from app.schemas import ChatRequest, ChatResponse, DocumentInfo, UploadResponse


settings = get_settings()
rag_service = RagService(settings)

app = FastAPI(
    title="RAG Chatbot API",
    description="FastAPI backend for document upload and retrieval augmented chatbot answers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "indexed_chunks": len(rag_service.chunks),
    }


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    try:
        document_id, chunks_added = await rag_service.add_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "uploaded-document",
        chunks_added=chunks_added,
    )


@app.get("/documents", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    return rag_service.list_documents()


@app.delete("/documents")
def clear_documents() -> dict[str, str]:
    rag_service.reset()
    return {"status": "documents and index cleared"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    sources = rag_service.retrieve(request.question, request.top_k) if request.use_documents else []
    answer, used_model = await rag_service.answer(request.question, sources, request.use_documents)
    return ChatResponse(answer=answer, sources=sources, used_model=used_model)
