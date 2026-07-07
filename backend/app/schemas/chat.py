from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceRead(BaseModel):
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity: float | None = None
    # Backward-compatible for chat history created by the initial MVP.
    score: float | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRead]
    confidence: str
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
    created_at: datetime
