"""Create the original ScholarPilot schema.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

from app.config import settings


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("upload_time", sa.DateTime(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("category", sa.String(100)),
        sa.Column("file_path", sa.String(500)),
    )
    op.create_index("ix_documents_id", "documents", ["id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.embedding_dimension), nullable=False),
        sa.Column("section_title", sa.String(255)),
    )
    op.create_index("ix_document_chunks_id", "document_chunks", ["id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_page_number", "document_chunks", ["page_number"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_sessions_id", "chat_sessions", ["id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    op.create_table(
        "mistake_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("error_reason", sa.Text()),
        sa.Column("knowledge_point", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mistake_records_id", "mistake_records", ["id"])
    op.create_index("ix_mistake_records_subject", "mistake_records", ["subject"])
    op.create_index("ix_mistake_records_knowledge_point", "mistake_records", ["knowledge_point"])

    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("plan_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_study_plans_id", "study_plans", ["id"])


def downgrade() -> None:
    for table in [
        "study_plans",
        "mistake_records",
        "chat_messages",
        "chat_sessions",
        "document_chunks",
        "documents",
        "users",
    ]:
        op.drop_table(table)
