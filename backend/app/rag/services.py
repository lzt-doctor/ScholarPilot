from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document
from app.rag.retrievers import (
    BM25Retriever,
    ExactVectorRetriever,
    HNSWVectorRetriever,
    HybridRetriever,
    bm25_cache,
    incompatible_document_ids,
)
from app.rag.types import (
    EmbeddingVersionMismatchError,
    RetrievalMode,
    RetrievalOutput,
)
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm_client import (
    LLMClient,
    LLMResult,
    get_llm_client,
    parse_mistake_analysis,
)


class RetrievalService:
    """Select and run a reproducible retrieval strategy for one user."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or get_embedding_service()

    def retrieve(
        self,
        db: Session,
        user_id: int,
        question: str,
        *,
        mode: RetrievalMode = "hybrid",
        top_k: int | None = None,
        ef_search: int | None = None,
    ) -> RetrievalOutput:
        mismatches = incompatible_document_ids(db, user_id, self.embedding_service)
        if mismatches:
            raise EmbeddingVersionMismatchError(mismatches)

        limit = top_k or settings.rag_top_k
        has_ready_documents = (
            db.query(Document.id)
            .filter(Document.user_id == user_id, Document.indexing_status == "ready")
            .first()
            is not None
        )
        if not has_ready_documents:
            return RetrievalOutput([], mode, {"top_k": limit, "reason": "no_ready_documents"})
        if mode == "exact":
            retriever = ExactVectorRetriever(self.embedding_service)
        elif mode == "hnsw":
            retriever = HNSWVectorRetriever(self.embedding_service, ef_search=ef_search)
        elif mode == "bm25":
            retriever = BM25Retriever()
        elif mode == "hybrid":
            retriever = HybridRetriever(self.embedding_service, ef_search=ef_search)
        else:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
        return retriever.retrieve(db, user_id, question, limit)

    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        bm25_cache.invalidate(user_id)


class StudyPlannerService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def generate(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> LLMResult:
        return await self.llm_client.generate_study_plan(
            goal=goal,
            background=background,
            weeks=weeks,
            hours_per_week=hours_per_week,
        )


class MistakeAnalysisService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def analyze(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> tuple[dict[str, str], LLMResult]:
        result = await self.llm_client.analyze_mistake(
            question_text=question_text,
            user_answer=user_answer,
            correct_answer=correct_answer,
        )
        return parse_mistake_analysis(result.content), result
