import argparse
import statistics
import time
from pathlib import Path

import numpy as np

from app.database import SessionLocal
from app.rag.services import RetrievalService
from experiments.common import (
    DEMO_DATASET_VERSION,
    DEMO_USER_ID,
    DemoEmbeddingService,
    base_result,
    cleanup_demo,
    read_jsonl,
    seed_demo,
    write_result_files,
)


def benchmark(
    dataset_path: Path,
    corpus_path: Path,
    modes: list[str],
    iterations: int,
    output: Path,
) -> dict:
    queries = read_jsonl(dataset_path)
    embedding = DemoEmbeddingService()
    raw_results = []
    summaries = {}
    with SessionLocal() as db:
        seed_demo(db, corpus_path, embedding)
        try:
            service = RetrievalService(embedding)
            for mode in modes:
                for query in queries:
                    service.retrieve(
                        db,
                        DEMO_USER_ID,
                        query["question"],
                        mode=mode,
                        top_k=10,
                    )
                    db.rollback()
                durations = []
                wall_started = time.perf_counter()
                for iteration in range(iterations):
                    for query in queries:
                        started = time.perf_counter()
                        result = service.retrieve(
                            db,
                            DEMO_USER_ID,
                            query["question"],
                            mode=mode,
                            top_k=10,
                        )
                        elapsed_ms = (time.perf_counter() - started) * 1000
                        durations.append(elapsed_ms)
                        raw_results.append(
                            {
                                "query_id": query["query_id"],
                                "iteration": iteration,
                                "retrieval_mode": mode,
                                "latency_ms": elapsed_ms,
                                "returned_chunk_ids": [source.source_id for source in result.sources],
                                "retrieval_parameters": result.parameters,
                            }
                        )
                        db.rollback()
                wall_seconds = time.perf_counter() - wall_started
                summaries[mode] = {
                    "mean_ms": statistics.fmean(durations),
                    "p50_ms": float(np.percentile(durations, 50)),
                    "p95_ms": float(np.percentile(durations, 95)),
                    "p99_ms": float(np.percentile(durations, 99)),
                    "queries_per_second": len(durations) / wall_seconds,
                    "sample_count": len(durations),
                }
        finally:
            cleanup_demo(db)

    result = {
        **base_result(
            dataset_version=DEMO_DATASET_VERSION,
            retrieval_config={
                "modes": modes,
                "top_k": 10,
                "iterations": iterations,
                "warmup_queries_per_mode": len(queries),
            },
            embedding_model=embedding.model_name,
        ),
        "summary": summaries,
        "raw_per_query_results": raw_results,
    }
    write_result_files(result, output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("experiments/datasets/demo_queries.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("experiments/datasets/demo_chunks.jsonl"))
    parser.add_argument("--modes", nargs="+", default=["exact", "hnsw", "bm25", "hybrid"])
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("experiments/results/demo/latency_benchmark"))
    args = parser.parse_args()
    result = benchmark(args.dataset, args.corpus, args.modes, args.iterations, args.output)
    for mode, summary in result["summary"].items():
        print(mode, summary)


if __name__ == "__main__":
    main()
