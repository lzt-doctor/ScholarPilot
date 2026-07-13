from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    page_number: int
    chunk_index: int
    chunk_text: str
    section_title: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    upload_time: datetime
    summary: str | None = None
    category: str | None = None
    embedding_model: str
    embedding_dimension: int
    embedding_version: str
    indexing_status: str
    indexing_error: str | None = None


class DocumentDetail(DocumentRead):
    chunks: list[DocumentChunkRead] = []
