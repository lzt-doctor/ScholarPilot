from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentChunk
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm_client import LLMClient, get_llm_client


@dataclass
class RetrievedSource:
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity: float | None = None


class RetrievalAgent:
    """Retrieve top-k chunks for a user question with pgvector cosine distance."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or get_embedding_service()

    def retrieve(
        self, db: Session, user_id: int, question: str, top_k: int | None = None
    ) -> list[RetrievedSource]:
        query_embedding = self.embedding_service.embed_text(question)
        limit = top_k or settings.rag_top_k
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")

        rows = (
            db.query(
                DocumentChunk,
                Document,
                distance,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.user_id == user_id)
            .order_by(distance)
            .limit(limit)
            .all()
        )

        sources: list[RetrievedSource] = []
        for chunk, document, distance in rows:
            similarity = (
                max(0.0, min(1.0, 1.0 - float(distance)))
                if distance is not None
                else None
            )
            sources.append(
                RetrievedSource(
                    document_id=document.id,
                    document_name=document.filename,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    similarity=similarity,
                )
            )
        return sources


class StudyPlannerAgent:
    """Generate a graduate-school-oriented study plan from a goal."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def generate(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> str:
        return await self.llm_client.generate_study_plan(
            goal=goal,
            background=background,
            weeks=weeks,
            hours_per_week=hours_per_week,
        )


class MistakeAnalysisAgent:
    """Analyze error reason and knowledge point for a mistake record."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def analyze(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> dict[str, str]:
        return await self.llm_client.analyze_mistake(
            question_text=question_text,
            user_answer=user_answer,
            correct_answer=correct_answer,
        )
