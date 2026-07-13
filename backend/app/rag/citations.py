import re
from dataclasses import dataclass

from app.rag.types import RetrievedSource


_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class CitationValidation:
    valid: bool
    cited_source_ids: list[int]
    cited_numbers: list[int]


def validate_citations(
    answer: str,
    sources: list[RetrievedSource],
    *,
    require_citation: bool = True,
) -> CitationValidation:
    numbers: list[int] = []
    for value in _CITATION_PATTERN.findall(answer):
        number = int(value)
        if number not in numbers:
            numbers.append(number)

    in_range = all(1 <= number <= len(sources) for number in numbers)
    has_required = bool(numbers) if require_citation and sources else True
    valid = in_range and has_required
    source_ids = [sources[number - 1].source_id for number in numbers if 1 <= number <= len(sources)]
    return CitationValidation(valid, source_ids, numbers)
