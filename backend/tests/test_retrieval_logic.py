from app.models import Document, DocumentChunk, User
from app.rag.evidence import estimate_evidence_strength, has_sufficient_evidence
from app.rag.retrievers import (
    BM25IndexCache,
    BM25Retriever,
    incompatible_document_ids,
    reciprocal_rank_fusion,
)
from app.rag.types import RetrievedSource
from tests.fakes import DeterministicFakeEmbedding


def _source(source_id: int, relevance: float, **kwargs) -> RetrievedSource:
    return RetrievedSource(
        source_id=source_id,
        document_id=1,
        document_name="paper.pdf",
        page_number=1,
        chunk_index=source_id,
        chunk_text=f"chunk {source_id}",
        relevance_score=relevance,
        **kwargs,
    )


def test_rrf_fusion_rewards_results_present_in_both_rankings() -> None:
    lexical = [_source(1, 1.0, lexical_score=2.0), _source(2, 0.5, lexical_score=1.0)]
    vector = [_source(2, 0.8, similarity=0.8), _source(3, 0.7, similarity=0.7)]

    fused = reciprocal_rank_fusion(lexical, vector, rrf_k=60, top_k=3)

    assert fused[0].source_id == 2
    assert fused[0].lexical_rank == 2
    assert fused[0].vector_rank == 1
    assert fused[0].fused_score > fused[1].fused_score


def test_evidence_strength_and_minimum_threshold() -> None:
    high = [_source(1, 0.9), _source(2, 0.7)]
    weak = [_source(3, 0.2)]
    assert estimate_evidence_strength(high) == "high"
    assert estimate_evidence_strength(weak) == "low"
    assert has_sufficient_evidence(high, 0.25) is True
    assert has_sufficient_evidence(weak, 0.25) is False


def test_embedding_version_mismatch_is_detected(db_session) -> None:
    user = User(username="version-user", email="version@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    document = Document(
        user_id=user.id,
        filename="legacy.pdf",
        file_type="pdf",
        embedding_model="legacy/model",
        embedding_dimension=384,
        embedding_version="legacy",
        indexing_status="requires_reindex",
    )
    db_session.add(document)
    db_session.commit()

    mismatches = incompatible_document_ids(
        db_session, user.id, DeterministicFakeEmbedding()
    )

    assert mismatches == [document.id]


def test_bm25_ranking_and_user_isolation(db_session) -> None:
    first = User(username="first-user", email="first@example.com", password_hash="x")
    second = User(username="second-user", email="second@example.com", password_hash="x")
    db_session.add_all([first, second])
    db_session.flush()
    docs = [
        Document(
            user_id=first.id,
            filename="rag.pdf",
            file_type="pdf",
            embedding_model="test/deterministic",
            embedding_dimension=384,
            embedding_version="test-v1",
            indexing_status="ready",
        ),
        Document(
            user_id=second.id,
            filename="private.pdf",
            file_type="pdf",
            embedding_model="test/deterministic",
            embedding_dimension=384,
            embedding_version="test-v1",
            indexing_status="ready",
        ),
    ]
    db_session.add_all(docs)
    db_session.flush()
    fake = DeterministicFakeEmbedding()
    db_session.add_all(
        [
            DocumentChunk(
                document_id=docs[0].id,
                page_number=1,
                chunk_index=0,
                chunk_text="hybrid retrieval combines vector and lexical search",
                embedding=fake.embed_text("hybrid retrieval"),
            ),
            DocumentChunk(
                document_id=docs[0].id,
                page_number=2,
                chunk_index=1,
                chunk_text="database transaction isolation",
                embedding=fake.embed_text("database"),
            ),
            DocumentChunk(
                document_id=docs[1].id,
                page_number=1,
                chunk_index=0,
                chunk_text="private secret retrieval content",
                embedding=fake.embed_text("private secret"),
            ),
        ]
    )
    db_session.commit()
    retriever = BM25Retriever(BM25IndexCache())

    output = retriever.retrieve(db_session, first.id, "hybrid retrieval", 5)
    isolated = retriever.retrieve(db_session, first.id, "private secret", 5)

    assert output.sources[0].chunk_index == 0
    assert all(source.document_id == docs[0].id for source in output.sources)
    assert isolated.sources == []

    first_user_id = first.id
    expected_document_id = docs[0].id
    db_session.commit()
    db_session.expunge_all()
    cached_output = retriever.retrieve(db_session, first_user_id, "hybrid retrieval", 5)
    assert cached_output.sources[0].document_id == expected_document_id


def test_bm25_cache_requires_invalidation_after_index_change(db_session) -> None:
    user = User(username="cache-user", email="cache@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    document = Document(
        user_id=user.id,
        filename="cache.pdf",
        file_type="pdf",
        embedding_model="test/deterministic",
        embedding_dimension=384,
        embedding_version="test-v1",
        indexing_status="ready",
    )
    db_session.add(document)
    db_session.commit()
    cache = BM25IndexCache()
    retriever = BM25Retriever(cache)
    assert retriever.retrieve(db_session, user.id, "newterm", 5).sources == []

    fake = DeterministicFakeEmbedding()
    db_session.add(
        DocumentChunk(
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            chunk_text="newterm appears after indexing",
            embedding=fake.embed_text("newterm"),
        )
    )
    db_session.commit()
    assert retriever.retrieve(db_session, user.id, "newterm", 5).sources == []

    cache.invalidate(user.id)
    assert retriever.retrieve(db_session, user.id, "newterm", 5).sources[0].chunk_index == 0
