import hashlib
import math
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Callable, Protocol

import numpy as np

from app.config import settings


class EmbeddingError(RuntimeError):
    code = "embedding_error"


class EmbeddingUnavailableError(EmbeddingError):
    code = "embedding_unavailable"


class EmbeddingDimensionError(EmbeddingError):
    code = "embedding_dimension_mismatch"


class EncoderModel(Protocol):
    def encode(self, texts: list[str], normalize_embeddings: bool = True): ...


@dataclass(frozen=True)
class EmbeddingIdentity:
    model: str
    dimension: int
    version: str


@dataclass(frozen=True)
class EmbeddingRuntimeStatus:
    active_embedding_backend: str
    embedding_model: str
    embedding_dimension: int
    embedding_version: str
    embedding_model_loaded: bool
    embedding_fallback_allowed: bool
    embedding_fallback_active: bool
    embedding_status: str

    def as_dict(self) -> dict:
        return asdict(self)


class EmbeddingService:
    """Generate embeddings without hiding model-loading or dimension failures."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        dimension: int | None = None,
        version: str | None = None,
        backend: str | None = None,
        allow_fallback: bool | None = None,
        model_factory: Callable[[str], EncoderModel] | None = None,
    ) -> None:
        self.model_name = model_name or settings.resolved_embedding_model
        self.dimension = dimension or settings.embedding_dimension
        self.version = version or settings.embedding_version
        self.backend = (backend or settings.embedding_backend).lower()
        self.allow_fallback = (
            settings.allow_embedding_fallback
            if allow_fallback is None
            else allow_fallback
        )
        self._model_factory = model_factory or self._default_model_factory
        self._model: EncoderModel | None = None
        self._model_load_failed = False
        self._fallback_active = False

    @property
    def identity(self) -> EmbeddingIdentity:
        return EmbeddingIdentity(self.model_name, self.dimension, self.version)

    @property
    def active_backend(self) -> str:
        if self._fallback_active or self.backend == "hash":
            return "hash"
        return "sentence-transformers"

    @staticmethod
    def _default_model_factory(model_name: str) -> EncoderModel:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    def _load_model(self) -> EncoderModel | None:
        if self.backend not in {"auto", "sentence-transformers", "hash"}:
            raise EmbeddingUnavailableError(
                f"Unsupported embedding backend: {self.backend}"
            )
        if self.backend == "hash":
            if not self.allow_fallback:
                raise EmbeddingUnavailableError(
                    "Hash embedding requires ALLOW_EMBEDDING_FALLBACK=true"
                )
            self._fallback_active = True
            return None
        if self._model is not None:
            return self._model
        if self._model_load_failed and not self.allow_fallback:
            raise EmbeddingUnavailableError("Embedding model is not available")
        try:
            self._model = self._model_factory(self.model_name)
            self._model_load_failed = False
            return self._model
        except Exception as exc:
            self._model_load_failed = True
            if self.allow_fallback:
                self._fallback_active = True
                return None
            raise EmbeddingUnavailableError(
                f"Unable to load embedding model '{self.model_name}'"
            ) from exc

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        if model is None:
            vectors = [self._hash_embedding(text) for text in texts]
        else:
            try:
                encoded = model.encode(texts, normalize_embeddings=True)
                vectors = [np.asarray(vector, dtype=float).tolist() for vector in encoded]
            except Exception as exc:
                raise EmbeddingUnavailableError("Embedding inference failed") from exc
        self._validate_dimensions(vectors)
        return vectors

    def _validate_dimensions(self, vectors: list[list[float]]) -> None:
        invalid = [len(vector) for vector in vectors if len(vector) != self.dimension]
        if invalid:
            raise EmbeddingDimensionError(
                f"Configured dimension is {self.dimension}, model returned {invalid[0]}"
            )

    def _hash_embedding(self, text: str) -> list[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
        if not tokens:
            tokens = [text.lower()[:32] or "empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(float(np.dot(vector, vector))) or 1.0
        return (vector / norm).astype(float).tolist()

    def runtime_status(self) -> EmbeddingRuntimeStatus:
        if self._model_load_failed and not self._fallback_active:
            status = "error"
        elif self._fallback_active:
            status = "fallback"
        elif self._model is not None:
            status = "ready"
        else:
            status = "not_loaded"
        return EmbeddingRuntimeStatus(
            active_embedding_backend=self.active_backend,
            embedding_model=self.model_name,
            embedding_dimension=self.dimension,
            embedding_version=self.version,
            embedding_model_loaded=self._model is not None,
            embedding_fallback_allowed=self.allow_fallback,
            embedding_fallback_active=self._fallback_active,
            embedding_status=status,
        )


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
