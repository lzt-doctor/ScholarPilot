from app.rag.types import RetrievedSource


def estimate_evidence_strength(sources: list[RetrievedSource]) -> str:
    """Describe retrieval evidence strength, not answer correctness."""

    scores = [
        source.relevance_score
        if source.relevance_score is not None
        else source.similarity
        for source in sources
    ]
    usable = [float(score) for score in scores if score is not None]
    if not usable or max(usable) < 0.25:
        return "low"
    supported = [score for score in usable if score >= 0.55]
    if max(usable) >= 0.75 and len(supported) >= 2:
        return "high"
    if max(usable) >= 0.4 or supported:
        return "medium"
    return "low"


def has_sufficient_evidence(
    sources: list[RetrievedSource], minimum_relevance: float
) -> bool:
    scores = [
        source.relevance_score
        if source.relevance_score is not None
        else source.similarity
        for source in sources
    ]
    return any(score is not None and float(score) >= minimum_relevance for score in scores)
