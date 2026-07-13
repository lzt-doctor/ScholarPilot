from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "ScholarPilot"
    api_prefix: str = ""
    environment: str = "development"

    database_url: str = (
        "postgresql+psycopg2://scholarpilot:scholarpilot@db:5432/scholarpilot"
    )
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    upload_dir: str = "uploads"

    # EMBEDDING_MODEL is the preferred public env var; EMBEDDING_MODEL_NAME remains
    # for backward compatibility with the initial MVP configuration.
    embedding_model: str | None = None
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    embedding_version: str = "1"
    embedding_backend: str = "auto"
    allow_embedding_fallback: bool = False
    rag_top_k: int = 4
    max_chunk_chars: int = 1000
    chunk_overlap_chars: int = 120
    max_upload_size_mb: int = 20

    retrieval_mode: str = "hybrid"
    retrieval_candidate_k: int = 20
    retrieval_min_relevance: float = 0.25
    hybrid_rrf_k: int = 60
    hybrid_vector_mode: str = "hnsw"
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    hnsw_ef_search: int = 40

    llm_provider: str = "mock"
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_embedding_model(self) -> str:
        return self.embedding_model or self.embedding_model_name


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
