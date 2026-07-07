import hashlib
import math
import re
from functools import lru_cache

import numpy as np

from app.config import settings


class EmbeddingService:
    """Sentence-transformers first, deterministic local fallback second."""

    def __init__(self) -> None:
        self.dimension = settings.embedding_dimension
        self._model = None
        self._model_load_error: str | None = None

    def _load_model(self):
        if settings.embedding_backend == "hash":
            return None
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.resolved_embedding_model)
            return self._model
        except Exception as exc:  # pragma: no cover - depends on local model cache.
            self._model_load_error = str(exc)
            return None

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        if model is not None:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [vector.astype(float).tolist() for vector in vectors]
        return [self._hash_embedding(text) for text in texts]

    def _hash_embedding(self, text: str) -> list[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
        if not tokens:
            tokens = [text.lower()[:32] or "empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(float(np.dot(vector, vector))) or 1.0
        return (vector / norm).astype(float).tolist()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
