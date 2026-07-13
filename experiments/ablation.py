import argparse
import itertools
import statistics
import time
from pathlib import Path

from app.database import SessionLocal
from app.models import Document, DocumentChunk
from app.rag.services import RetrievalService
from experiments.common import (
    DEMO_DATASET_VERSION,
    DEMO_USER_ID,
    DemoEmbeddingService,
    base_result,
    cleanup_demo,
    mean_metrics,
    ranked_metrics,
    read_jsonl,
    seed_demo,
    write_result_files,
)


def configurations() -> list[dict]:
    configs = []
    for mode, chunk_size, overlap, top_k in itertools.product(
        ["exact", "hnsw", "bm25", "hybrid"],
        [160, 320],
        [20, 60],
        [5, 10],
    ):
        ef_values = [20, 80] if mode in {"hnsw", "hybrid"} else [40]
        for ef_search in ef_values:
            configs.append(
                {
                    "mode": mode,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "top_k": top_k,
                    "ef_search": ef_search,
                }
            )
    return configs


def run_ablation(dataset_path: Path, corpus_path: Path, output: Path) -> dict:
    queries = read_jsonl(dataset_path)
    embedding = DemoEmbeddingService()
    raw_results = []
    summaries = []
    configs = configurations()
    with SessionLocal() as db:
        try:
            service = RetrievalService(embedding)
            for config_id, config in enumerate(configs, start=1):
                parent_map = seed_demo(
                    db,
                    corpus_path,
                    embedding,
                    chunk_size=config["chunk_size"],
                    overlap=config["overlap"],
                )
                config_rows = []
                for query in queries:
                    relevant = [
                        child
                        for parent in query["relevant_chunk_ids"]
                        for child in parent_map[int(parent)]
                    ]
                    started = time.perf_counter()
                    retrieval = service.retrieve(
                        db,
                        DEMO_USER_ID,
                        query["question"],
                        mode=config["mode"],
                        top_k=config["top_k"],
                        ef_search=config["ef_search"],
                    )
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    returned = [source.source_id for source in retrieval.sources]
                    row = {
                        "config_id": config_id,
                        "query_id": query["query_id"],
                        "retrieval_config": config,
                        "relevant_chunk_ids": relevant,
                        "returned_chunk_ids": returned,
                        "latency_ms": elapsed_ms,
                        "metrics": ranked_metrics(returned, relevant),
                        "retrieval_parameters": retrieval.parameters,
                    }
                    raw_results.append(row)
                    config_rows.append(row)
                    db.rollback()
                summaries.append(
                    {
                        "config_id": config_id,
                        "retrieval_config": config,
                        "chunk_count": db.query(DocumentChunk)
                        .join(Document, Document.id == DocumentChunk.document_id)
                        .filter(Document.user_id == DEMO_USER_ID)
                        .count(),
                        "mean_latency_ms": statistics.fmean(
                            row["latency_ms"] for row in config_rows
                        ),
                        **mean_metrics(config_rows),
                    }
                )
        finally:
            cleanup_demo(db)

    result = {
        **base_result(
            dataset_version=DEMO_DATASET_VERSION,
            retrieval_config={"ablation_matrix": configs},
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
    parser.add_argument("--output", type=Path, default=Path("experiments/results/demo/ablation"))
    args = parser.parse_args()
    result = run_ablation(args.dataset, args.corpus, args.output)
    print(f"completed {len(result['summary'])} actual demo configurations")


if __name__ == "__main__":
    main()
