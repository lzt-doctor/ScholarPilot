from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceRead(BaseModel):
    source_id: int
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity: float | None = None
    # Backward-compatible for chat history created by the initial MVP.
    score: float | None = None
    lexical_score: float | None = None
    relevance_score: float | None = None
    lexical_rank: int | None = None
    vector_rank: int | None = None
    fused_score: float | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)
    retrieval_mode: Literal["exact", "hnsw", "bm25", "hybrid"] = "hybrid"
    ef_search: int | None = Field(default=None, ge=1, le=1000)


class RuntimeMetadata(BaseModel):
    active_embedding_backend: str
    embedding_model: str
    embedding_dimension: int
    embedding_version: str
    embedding_model_loaded: bool
    embedding_fallback_allowed: bool
    embedding_fallback_active: bool
    embedding_status: str
    llm_provider: str
    llm_model: str
    llm_mode: str
    llm_status: str
    llm_error_code: str | None = None
    retrieval_mode: str
    retrieval_parameters: dict[str, Any]


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRead]
    evidence_strength: Literal["high", "medium", "low"]
    # Deprecated compatibility field for clients built against the MVP.
    confidence: Literal["high", "medium", "low"]
    citation_validity: bool
    cited_source_ids: list[int]
    runtime_metadata: RuntimeMetadata
    session_id: int


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    sources: list[dict[str, Any]] | None = None
    runtime_metadata: dict[str, Any] | None = None
    evidence_strength: str | None = None
    citation_validity: bool | None = None
    cited_source_ids: list[int] | None = None
    created_at: datetime
