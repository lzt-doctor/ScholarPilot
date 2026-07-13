import numpy as np
import pytest

from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingService,
    EmbeddingUnavailableError,
)


class WrongDimensionModel:
    def encode(self, texts, normalize_embeddings=True):
        return np.ones((len(texts), 2))


def test_embedding_dimension_is_enforced() -> None:
    service = EmbeddingService(
        dimension=3,
        backend="sentence-transformers",
        allow_fallback=False,
        model_factory=lambda _name: WrongDimensionModel(),
    )
    with pytest.raises(EmbeddingDimensionError):
        service.embed_text("dimension check")


def test_embedding_load_failure_does_not_silently_fallback() -> None:
    def fail(_name):
        raise OSError("model missing")

    service = EmbeddingService(
        dimension=8,
        backend="sentence-transformers",
        allow_fallback=False,
        model_factory=fail,
    )
    with pytest.raises(EmbeddingUnavailableError):
        service.embed_text("no fallback")
    assert service.runtime_status().embedding_fallback_active is False


def test_hash_fallback_requires_explicit_permission() -> None:
    denied = EmbeddingService(dimension=8, backend="hash", allow_fallback=False)
    with pytest.raises(EmbeddingUnavailableError):
        denied.embed_text("denied")

    allowed = EmbeddingService(dimension=8, backend="hash", allow_fallback=True)
    assert len(allowed.embed_text("allowed")) == 8
    assert allowed.runtime_status().embedding_fallback_active is True
