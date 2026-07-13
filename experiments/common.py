import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, User
from app.rag.retrievers import bm25_cache
from app.services.embeddings import EmbeddingIdentity, EmbeddingRuntimeStatus


DEMO_USER_ID = -99999
DEMO_DATASET_VERSION = "demo-v1"


class DemoEmbeddingService:
    """Deterministic offline embedding used only by the committed demo experiment."""

    model_name = "demo/deterministic-token-hash"
    dimension = 384
    version = "demo-v1"

    @property
    def identity(self) -> EmbeddingIdentity:
        return EmbeddingIdentity(self.model_name, self.dimension, self.version)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        lowered = text.lower()
        tokens = lowered.replace("，", " ").replace("。", " ").split()
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimension] += 1.0
        norm = math.sqrt(float(np.dot(vector, vector))) or 1.0
        return (vector / norm).astype(float).tolist()

    def runtime_status(self) -> EmbeddingRuntimeStatus:
        return EmbeddingRuntimeStatus(
            active_embedding_backend="deterministic-demo",
            embedding_model=self.model_name,
            embedding_dimension=self.dimension,
            embedding_version=self.version,
            embedding_model_loaded=True,
            embedding_fallback_allowed=False,
            embedding_fallback_active=False,
            embedding_status="ready",
        )


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _split_text(text: str, chunk_size: int | None, overlap: int) -> list[str]:
    if not chunk_size or len(text) <= chunk_size:
        return [text]
    step = max(1, chunk_size - overlap)
    return [text[start : start + chunk_size] for start in range(0, len(text), step)]


def seed_demo(
    db: Session,
    corpus_path: str | Path,
    embedding_service: DemoEmbeddingService,
    *,
    chunk_size: int | None = None,
    overlap: int = 0,
) -> dict[int, list[int]]:
    cleanup_demo(db)
    db.add(
        User(
            id=DEMO_USER_ID,
            username="scholarpilot-demo-eval",
            email="scholarpilot-demo-eval@invalid.local",
            password_hash="not-a-login-account",
        )
    )
    corpus = read_jsonl(corpus_path)
    documents: dict[int, Document] = {}
    for row in corpus:
        document_id = int(row["document_id"])
        document = Document(
            id=document_id,
            user_id=DEMO_USER_ID,
            filename=row["document_name"],
            file_type="pdf",
            category="demo-evaluation",
            embedding_model=embedding_service.model_name,
            embedding_dimension=embedding_service.dimension,
            embedding_version=embedding_service.version,
            indexing_status="ready",
        )
        documents[document_id] = document
        db.add(document)
    db.flush()

    parent_to_children: dict[int, list[int]] = {}
    generated_id = -20000
    for row in corpus:
        parent_id = int(row["chunk_id"])
        parts = _split_text(row["text"], chunk_size, overlap)
        child_ids: list[int] = []
        for index, part in enumerate(parts):
            chunk_id = parent_id if len(parts) == 1 else generated_id
            generated_id -= 1
            child_ids.append(chunk_id)
            db.add(
                DocumentChunk(
                    id=chunk_id,
                    document_id=int(row["document_id"]),
                    page_number=int(row["page_number"]),
                    chunk_index=index,
                    chunk_text=part,
                    embedding=embedding_service.embed_text(part),
                    section_title="demo",
                )
            )
        parent_to_children[parent_id] = child_ids
    db.commit()
    bm25_cache.invalidate(DEMO_USER_ID)
    return parent_to_children


def cleanup_demo(db: Session) -> None:
    db.query(User).filter(User.id == DEMO_USER_ID).delete(synchronize_session=False)
    db.commit()
    bm25_cache.invalidate(DEMO_USER_ID)


def ranked_metrics(returned: list[int], relevant: list[int]) -> dict[str, float]:
    relevant_set = set(relevant)

    def recall(k: int) -> float:
        return len(relevant_set.intersection(returned[:k])) / max(len(relevant_set), 1)

    reciprocal_rank = 0.0
    for rank, chunk_id in enumerate(returned, start=1):
        if chunk_id in relevant_set:
            reciprocal_rank = 1.0 / rank
            break
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(returned[:10], start=1)
        if chunk_id in relevant_set
    )
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(10, len(relevant)) + 1))
    return {
        "recall_at_5": recall(5),
        "recall_at_10": recall(10),
        "mrr": reciprocal_rank,
        "ndcg_at_10": dcg / ideal if ideal else 0.0,
    }


def mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["recall_at_5", "recall_at_10", "mrr", "ndcg_at_10"]
    return {
        key: sum(float(row["metrics"][key]) for row in rows) / max(len(rows), 1)
        for key in keys
    }


def git_commit() -> str:
    configured = os.getenv("GIT_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def base_result(
    *,
    dataset_version: str,
    retrieval_config: Any,
    embedding_model: str,
) -> dict[str, Any]:
    return {
        "result_scope": "demo",
        "git_commit": git_commit(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset_version,
        "retrieval_config": retrieval_config,
        "embedding_model": embedding_model,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "database": "PostgreSQL + pgvector",
            "demo": True,
            "git_dirty": os.getenv("GIT_DIRTY", "unknown").lower(),
        },
    }


def write_result_files(result: dict[str, Any], output_prefix: str | Path) -> tuple[Path, Path]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    csv_path = prefix.with_suffix(".csv")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = result.get("raw_per_query_results", [])
    metadata = {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        for key, value in result.items()
        if key not in {"raw_per_query_results", "summary"}
    }
    flattened: list[dict[str, Any]] = []
    for row in rows:
        flat = dict(metadata)
        flat.update(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in row.items()
            }
        )
        flattened.append(flat)
    if not flattened:
        flattened = [metadata]
    fieldnames = sorted({key for row in flattened for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened)
    return json_path, csv_path
