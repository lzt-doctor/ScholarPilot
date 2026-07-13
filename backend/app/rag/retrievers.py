from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import RLock
from typing import Any

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentChunk
from app.rag.types import RetrievedSource, RetrievalOutput
from app.services.embeddings import EmbeddingService


jieba.setLogLevel(20)


class Retriever(ABC):
    mode: str

    @abstractmethod
    def retrieve(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> RetrievalOutput:
        raise NotImplementedError


class _VectorRetriever(Retriever):
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    def _query_rows(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> list[Any]:
        query_embedding = self.embedding_service.embed_text(query)
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        return (
            db.query(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(
                Document.user_id == user_id,
                Document.indexing_status == "ready",
            )
            .order_by(distance, DocumentChunk.id)
            .limit(top_k)
            .all()
        )

    def _to_sources(self, rows: list[Any]) -> list[RetrievedSource]:
        sources: list[RetrievedSource] = []
        for rank, (chunk, document, distance) in enumerate(rows, start=1):
            similarity = None
            if distance is not None:
                similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            sources.append(
                RetrievedSource(
                    source_id=chunk.id,
                    document_id=document.id,
                    document_name=document.filename,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    similarity=similarity,
                    relevance_score=similarity,
                    vector_rank=rank,
                )
            )
        return sources


class ExactVectorRetriever(_VectorRetriever):
    mode = "exact"

    def retrieve(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> RetrievalOutput:
        db.execute(text("SET LOCAL enable_indexscan = off"))
        db.execute(text("SET LOCAL enable_bitmapscan = off"))
        sources = self._to_sources(self._query_rows(db, user_id, query, top_k))
        return RetrievalOutput(
            sources=sources,
            mode="exact",
            parameters={"top_k": top_k, "distance": "cosine", "index": "disabled"},
        )


class HNSWVectorRetriever(_VectorRetriever):
    mode = "hnsw"

    def __init__(self, embedding_service: EmbeddingService, ef_search: int | None = None) -> None:
        super().__init__(embedding_service)
        self.ef_search = ef_search or settings.hnsw_ef_search

    def retrieve(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> RetrievalOutput:
        ef_search = max(1, min(int(self.ef_search), 1000))
        db.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
        db.execute(text("SET LOCAL enable_seqscan = off"))
        sources = self._to_sources(self._query_rows(db, user_id, query, top_k))
        return RetrievalOutput(
            sources=sources,
            mode="hnsw",
            parameters={
                "top_k": top_k,
                "distance": "cosine",
                "m": settings.hnsw_m,
                "ef_construction": settings.hnsw_ef_construction,
                "ef_search": ef_search,
                "index": "ix_document_chunks_embedding_hnsw",
            },
        )


def tokenize(text_value: str) -> list[str]:
    return [
        token.lower().strip()
        for token in jieba.cut_for_search(text_value, HMM=False)
        if token.strip()
    ]


@dataclass
class _BM25Entry:
    source_id: int
    document_id: int
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str
    tokens: list[str]


@dataclass
class _BM25Index:
    entries: list[_BM25Entry]
    engine: BM25Okapi | None


class BM25IndexCache:
    def __init__(self) -> None:
        self._indexes: dict[int, _BM25Index] = {}
        self._lock = RLock()

    def get_or_build(self, db: Session, user_id: int) -> _BM25Index:
        with self._lock:
            cached = self._indexes.get(user_id)
            if cached is not None:
                return cached
            rows = (
                db.query(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .filter(
                    Document.user_id == user_id,
                    Document.indexing_status == "ready",
                )
                .order_by(DocumentChunk.id)
                .all()
            )
            entries = [
                _BM25Entry(
                    source_id=chunk.id,
                    document_id=document.id,
                    document_name=document.filename,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    tokens=tokenize(chunk.chunk_text),
                )
                for chunk, document in rows
            ]
            engine = BM25Okapi([entry.tokens for entry in entries]) if entries else None
            index = _BM25Index(entries=entries, engine=engine)
            self._indexes[user_id] = index
            return index

    def invalidate(self, user_id: int) -> None:
        with self._lock:
            self._indexes.pop(user_id, None)

    def clear(self) -> None:
        with self._lock:
            self._indexes.clear()


bm25_cache = BM25IndexCache()


class BM25Retriever(Retriever):
    mode = "bm25"

    def __init__(self, cache: BM25IndexCache | None = None) -> None:
        self.cache = cache or bm25_cache

    def retrieve(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> RetrievalOutput:
        query_tokens = tokenize(query)
        index = self.cache.get_or_build(db, user_id)
        if not query_tokens or not index.engine:
            return RetrievalOutput([], "bm25", {"top_k": top_k, "tokenizer": "jieba"})

        scores = index.engine.get_scores(query_tokens)
        query_terms = set(query_tokens)
        candidates: list[tuple[float, float, _BM25Entry]] = []
        for score, entry in zip(scores, index.entries, strict=True):
            overlap = len(query_terms.intersection(entry.tokens)) / max(len(query_terms), 1)
            if overlap > 0:
                candidates.append((float(score), overlap, entry))
        candidates.sort(key=lambda item: (-item[0], item[2].source_id))

        sources: list[RetrievedSource] = []
        for rank, (score, overlap, entry) in enumerate(candidates[:top_k], start=1):
            sources.append(
                RetrievedSource(
                    source_id=entry.source_id,
                    document_id=entry.document_id,
                    document_name=entry.document_name,
                    page_number=entry.page_number,
                    chunk_index=entry.chunk_index,
                    chunk_text=entry.chunk_text,
                    lexical_score=score,
                    relevance_score=overlap,
                    lexical_rank=rank,
                )
            )
        return RetrievalOutput(
            sources,
            "bm25",
            {"top_k": top_k, "tokenizer": "jieba", "algorithm": "BM25Okapi"},
        )


def reciprocal_rank_fusion(
    lexical: list[RetrievedSource],
    vector: list[RetrievedSource],
    *,
    rrf_k: int,
    top_k: int,
) -> list[RetrievedSource]:
    merged: dict[int, RetrievedSource] = {}
    for rank, source in enumerate(lexical, start=1):
        source.lexical_rank = rank
        source.fused_score = 1.0 / (rrf_k + rank)
        merged[source.source_id] = source
    for rank, vector_source in enumerate(vector, start=1):
        existing = merged.get(vector_source.source_id)
        if existing is None:
            vector_source.vector_rank = rank
            vector_source.fused_score = 1.0 / (rrf_k + rank)
            merged[vector_source.source_id] = vector_source
            continue
        existing.vector_rank = rank
        existing.similarity = vector_source.similarity
        existing.fused_score = (existing.fused_score or 0.0) + 1.0 / (rrf_k + rank)

    for source in merged.values():
        lexical_signal = source.relevance_score if source.lexical_rank else None
        vector_signal = source.similarity if source.vector_rank else None
        if lexical_signal is not None and vector_signal is not None:
            source.relevance_score = (float(lexical_signal) + float(vector_signal)) / 2
        elif vector_signal is not None:
            source.relevance_score = float(vector_signal)
        elif lexical_signal is not None:
            source.relevance_score = float(lexical_signal) * 0.8

    return sorted(
        merged.values(),
        key=lambda source: (-(source.fused_score or 0.0), source.source_id),
    )[:top_k]


class HybridRetriever(Retriever):
    mode = "hybrid"

    def __init__(
        self,
        embedding_service: EmbeddingService,
        *,
        candidate_k: int | None = None,
        rrf_k: int | None = None,
        vector_mode: str | None = None,
        ef_search: int | None = None,
        cache: BM25IndexCache | None = None,
    ) -> None:
        self.candidate_k = candidate_k or settings.retrieval_candidate_k
        self.rrf_k = rrf_k or settings.hybrid_rrf_k
        self.vector_mode = vector_mode or settings.hybrid_vector_mode
        self.lexical = BM25Retriever(cache)
        self.vector: Retriever
        if self.vector_mode == "exact":
            self.vector = ExactVectorRetriever(embedding_service)
        else:
            self.vector = HNSWVectorRetriever(embedding_service, ef_search=ef_search)

    def retrieve(
        self, db: Session, user_id: int, query: str, top_k: int
    ) -> RetrievalOutput:
        candidate_k = max(top_k, self.candidate_k)
        lexical_output = self.lexical.retrieve(db, user_id, query, candidate_k)
        vector_output = self.vector.retrieve(db, user_id, query, candidate_k)
        sources = reciprocal_rank_fusion(
            lexical_output.sources,
            vector_output.sources,
            rrf_k=self.rrf_k,
            top_k=top_k,
        )
        return RetrievalOutput(
            sources,
            "hybrid",
            {
                "top_k": top_k,
                "candidate_k": candidate_k,
                "rrf_k": self.rrf_k,
                "vector_mode": self.vector_mode,
                "vector_parameters": vector_output.parameters,
                "lexical_parameters": lexical_output.parameters,
            },
        )


def incompatible_document_ids(
    db: Session, user_id: int, embedding_service: EmbeddingService
) -> list[int]:
    identity = embedding_service.identity
    rows = (
        db.query(Document.id)
        .filter(
            Document.user_id == user_id,
            Document.indexing_status.in_(["ready", "requires_reindex"]),
            or_(
                Document.embedding_model != identity.model,
                Document.embedding_dimension != identity.dimension,
                Document.embedding_version != identity.version,
                Document.indexing_status == "requires_reindex",
            ),
        )
        .all()
    )
    return [int(row[0]) for row in rows]
