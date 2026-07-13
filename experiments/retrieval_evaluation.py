import argparse
import time
from pathlib import Path

from app.database import SessionLocal
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


def evaluate(dataset_path: Path, corpus_path: Path, modes: list[str], output: Path) -> dict:
    queries = read_jsonl(dataset_path)
    embedding = DemoEmbeddingService()
    raw_results = []
    retrieval_parameters = {}
    with SessionLocal() as db:
        parent_map = seed_demo(db, corpus_path, embedding)
        try:
            service = RetrievalService(embedding)
            for mode in modes:
                for query in queries:
                    relevant = [
                        child
                        for parent in query["relevant_chunk_ids"]
                        for child in parent_map[int(parent)]
                    ]
                    started = time.perf_counter()
                    output_result = service.retrieve(
                        db,
                        DEMO_USER_ID,
                        query["question"],
                        mode=mode,
                        top_k=10,
                    )
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    returned = [source.source_id for source in output_result.sources]
                    metrics = ranked_metrics(returned, relevant)
                    retrieval_parameters[mode] = output_result.parameters
                    raw_results.append(
                        {
                            "query_id": query["query_id"],
                            "question": query["question"],
                            "category": query["category"],
                            "difficulty": query["difficulty"],
                            "retrieval_mode": mode,
                            "relevant_chunk_ids": relevant,
                            "returned_chunk_ids": returned,
                            "latency_ms": elapsed_ms,
                            "metrics": metrics,
                            "retrieval_parameters": output_result.parameters,
                        }
                    )
                    db.rollback()
        finally:
            cleanup_demo(db)

    summaries = {
        mode: mean_metrics([row for row in raw_results if row["retrieval_mode"] == mode])
        for mode in modes
    }
    result = {
        **base_result(
            dataset_version=DEMO_DATASET_VERSION,
            retrieval_config={"modes": modes, "top_k": 10, "parameters": retrieval_parameters},
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
    parser.add_argument("--output", type=Path, default=Path("experiments/results/demo/retrieval_evaluation"))
    args = parser.parse_args()
    result = evaluate(args.dataset, args.corpus, args.modes, args.output)
    for mode, summary in result["summary"].items():
        print(mode, summary)


if __name__ == "__main__":
    main()
