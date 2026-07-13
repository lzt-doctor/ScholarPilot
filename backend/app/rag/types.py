from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RetrievalMode = Literal["exact", "hnsw", "bm25", "hybrid"]


@dataclass
class RetrievedSource:
    source_id: int
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity: float | None = None
    lexical_score: float | None = None
    relevance_score: float | None = None
    lexical_rank: int | None = None
    vector_rank: int | None = None
    fused_score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalOutput:
    sources: list[RetrievedSource]
    mode: RetrievalMode
    parameters: dict[str, Any] = field(default_factory=dict)


class RetrievalError(RuntimeError):
    code = "retrieval_error"


class EmbeddingVersionMismatchError(RetrievalError):
    code = "embedding_version_mismatch"

    def __init__(self, document_ids: list[int]) -> None:
        self.document_ids = document_ids
        super().__init__("Document embeddings do not match the active embedding model")
