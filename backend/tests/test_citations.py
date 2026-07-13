from app.rag.citations import validate_citations
from app.rag.types import RetrievedSource


def _sources() -> list[RetrievedSource]:
    return [
        RetrievedSource(101, 1, "a.pdf", 1, 0, "a"),
        RetrievedSource(102, 1, "a.pdf", 2, 1, "b"),
    ]


def test_valid_citations_map_numbers_to_chunk_ids() -> None:
    result = validate_citations("结论来自资料 [2]，并由定义 [1] 支持。", _sources())
    assert result.valid is True
    assert result.cited_source_ids == [102, 101]


def test_invalid_or_missing_citations_are_rejected() -> None:
    assert validate_citations("错误编号 [3]", _sources()).valid is False
    assert validate_citations("没有引用", _sources()).valid is False
