import hashlib

import numpy as np

from app.services.embeddings import (
    EmbeddingIdentity,
    EmbeddingRuntimeStatus,
)


class DeterministicFakeEmbedding:
    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self.model_name = "test/deterministic"
        self.version = "test-v1"

    @property
    def identity(self) -> EmbeddingIdentity:
        return EmbeddingIdentity(self.model_name, self.dimension, self.version)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = np.zeros(self.dimension, dtype=float)
            for token in text.lower().split():
                digest = hashlib.sha256(token.encode()).digest()
                vector[int.from_bytes(digest[:4], "big") % self.dimension] += 1.0
            norm = np.linalg.norm(vector) or 1.0
            vectors.append((vector / norm).tolist())
        return vectors

    def runtime_status(self) -> EmbeddingRuntimeStatus:
        return EmbeddingRuntimeStatus(
            active_embedding_backend="fake",
            embedding_model=self.model_name,
            embedding_dimension=self.dimension,
            embedding_version=self.version,
            embedding_model_loaded=True,
            embedding_fallback_allowed=False,
            embedding_fallback_active=False,
            embedding_status="ready",
        )
