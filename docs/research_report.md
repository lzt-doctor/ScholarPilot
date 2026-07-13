# ScholarPilot Research Report

## Problem definition

Given a user-scoped collection of academic PDF chunks and a natural-language query, retrieve a ranked set of evidence chunks, optionally generate an answer grounded in those chunks, and expose enough metadata to audit the retrieval and generation path.

The research questions are:

1. How do exact vector, HNSW, BM25 and RRF hybrid retrieval compare under the same query set?
2. How do chunk size, overlap, top-k and `ef_search` affect ranking metrics and latency?
3. Can model identity, citations and failure states be represented without overstating answer correctness?

## Method

Exact and HNSW use pgvector cosine distance. BM25 uses deterministic jieba tokenization with `HMM=False`. Hybrid retrieval merges BM25 and vector ranks with Reciprocal Rank Fusion. All database queries and lexical caches are scoped by `user_id`.

The document embedding identity is the tuple `(model, dimension, version)`. Retrieval rejects incompatible indexed documents. `evidence_strength` is a rule over retrieval scores and is deliberately not interpreted as correctness probability.

## Dataset

The committed `demo-v1` dataset contains five synthetic chunks and five queries with chunk-level relevance labels. It exists only to exercise the pipeline. It is too small and too directly worded to support comparative scientific claims.

Query schema:

- `query_id`
- `question`
- `relevant_chunk_ids`
- `category`
- `difficulty`

## Metrics

- Recall@5 and Recall@10: fraction of relevant chunks present in the first K results.
- MRR: reciprocal rank of the first relevant result.
- nDCG@10: binary relevance ranking quality in the first ten results.
- Latency: mean, P50, P95 and P99 wall-clock query duration.
- Throughput: completed queries divided by total measured wall time.

## Experiment design

`retrieval_evaluation.py` compares the four retrieval modes. `latency_benchmark.py` warms each mode with every query, then repeats every demo query and records each measured timing. `ablation.py` executes an actual configuration matrix over retrieval mode, chunk size, overlap, top-k and HNSW `ef_search`; demo text is re-chunked and re-indexed per configuration.

Every JSON and CSV artifact contains the Git commit, UTC timestamp, dataset version, full retrieval configuration, embedding model, environment and raw per-query results.

## Results

The following values were actually generated on 2026-07-13 UTC from commit
`e15a49932876510ec0f21bf59d456d327b422135` with `git_dirty=true`. They describe only
`demo-v1` and the deterministic demo embedding.

| Mode | Recall@5 | Recall@10 | MRR | nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| Exact | 1.000 | 1.000 | 1.000 | 1.000 |
| HNSW | 1.000 | 1.000 | 1.000 | 1.000 |
| BM25 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid | 1.000 | 1.000 | 1.000 | 1.000 |

All methods scored perfectly because the dataset contains only five directly worded queries. This
is a pipeline check, not evidence that the methods are equivalent or generally accurate.

After five warm-up queries per mode, 25 measured queries per mode produced:

| Mode | Mean ms | P50 ms | P95 ms | P99 ms | QPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exact | 1.388 | 1.367 | 1.619 | 1.636 | 675.14 |
| HNSW | 1.314 | 1.307 | 1.442 | 1.560 | 713.43 |
| BM25 | 0.753 | 0.758 | 0.878 | 0.896 | 1187.48 |
| Hybrid | 1.591 | 1.577 | 1.757 | 1.761 | 592.53 |

The ablation executed 48 real configurations and stored 240 per-query rows. The lowest observed
Recall@5 was `0.7167` for Exact with chunk size 160, overlap 60 and top-k 5. This setting expanded
the five parent chunks into 15 child chunks, so top-k 5 could not cover every child marked relevant.
The ablation's per-configuration latency includes index/cache rebuild effects and should not be
compared directly with the warmed latency table.

Measured artifacts:

- `experiments/results/demo/retrieval_evaluation.json` and `.csv`
- `experiments/results/demo/latency_benchmark.json` and `.csv`
- `experiments/results/demo/ablation.json` and `.csv`

Reproduce with:

```bash
make eval-demo
```

## Threats to validity

- The demo corpus is synthetic, tiny and lexically aligned with its queries.
- The deterministic demo embedding is a token-hash control, not a sentence-transformer quality proxy.
- HNSW behavior on five documents cannot represent large-collection recall or latency.
- Cold starts, concurrent users, GPU inference and production network variance are not measured.
- Chunk relevance is binary and manually authored for the synthetic dataset.

## Interpretation boundary

Passing the demo evaluation means the experimental code, retrieval modes and result serialization executed. It does not establish production quality, hallucination prevention, answer correctness or superiority of one retrieval method on real academic documents.
