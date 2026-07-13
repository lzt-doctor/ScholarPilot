"""Add traceable retrieval metadata and HNSW index.

Revision ID: 0002_research
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

from app.config import settings


revision = "0002_research"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("embedding_model", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("embedding_dimension", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("embedding_version", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("indexing_status", sa.String(32), nullable=True))
    op.add_column("documents", sa.Column("indexing_error", sa.String(255), nullable=True))
    op.execute(
        "UPDATE documents SET "
        "embedding_model = 'legacy-unknown', "
        "embedding_dimension = 384, embedding_version = 'legacy', "
        "indexing_status = 'requires_reindex' "
        "WHERE embedding_model IS NULL"
    )
    for column in ["embedding_model", "embedding_dimension", "embedding_version", "indexing_status"]:
        op.alter_column("documents", column, nullable=False)
    op.create_index("ix_documents_indexing_status", "documents", ["indexing_status"])

    op.add_column("chat_messages", sa.Column("runtime_metadata", sa.JSON(), nullable=True))
    op.add_column("chat_messages", sa.Column("evidence_strength", sa.String(20), nullable=True))
    op.add_column("chat_messages", sa.Column("citation_validity", sa.Boolean(), nullable=True))
    op.add_column("chat_messages", sa.Column("cited_source_ids", sa.JSON(), nullable=True))

    m = max(2, min(int(settings.hnsw_m), 100))
    ef_construction = max(4, min(int(settings.hnsw_ef_construction), 1000))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = {m}, ef_construction = {ef_construction})"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    for column in ["cited_source_ids", "citation_validity", "evidence_strength", "runtime_metadata"]:
        op.drop_column("chat_messages", column)
    op.drop_index("ix_documents_indexing_status", table_name="documents")
    for column in ["indexing_error", "indexing_status", "embedding_version", "embedding_dimension", "embedding_model"]:
        op.drop_column("documents", column)
