from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What is this document about?"])
    top_k: int = Field(default=4, ge=1, le=10)
    use_documents: bool = True
    session_id: str | None = None


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    used_model: str | None = None


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_added: int


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunks: int
