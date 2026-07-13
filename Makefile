.PHONY: test build verify eval-demo

GIT_COMMIT := $(shell git rev-parse HEAD)
GIT_DIRTY := $(if $(shell git status --porcelain),true,false)

test:
	docker compose build backend
	docker compose run --rm --no-deps backend pytest

build:
	docker compose build

verify: build
	docker compose config >/dev/null
	docker compose run --rm --no-deps backend ruff check app tests experiments
	docker compose run --rm --no-deps backend pytest
	cd frontend && npm run build

eval-demo:
	docker compose up -d db
	docker compose run --rm backend python -m app.migration_runner
	docker compose run --rm -e GIT_COMMIT=$(GIT_COMMIT) -e GIT_DIRTY=$(GIT_DIRTY) backend python -m experiments.retrieval_evaluation
	docker compose run --rm -e GIT_COMMIT=$(GIT_COMMIT) -e GIT_DIRTY=$(GIT_DIRTY) backend python -m experiments.latency_benchmark
	docker compose run --rm -e GIT_COMMIT=$(GIT_COMMIT) -e GIT_DIRTY=$(GIT_DIRTY) backend python -m experiments.ablation
