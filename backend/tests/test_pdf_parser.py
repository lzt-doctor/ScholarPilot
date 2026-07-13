from app.config import settings
from app.services.pdf_parser import PageText, split_pages_to_chunks


def test_pdf_chunk_split_preserves_page_and_overlap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_chunk_chars", 40)
    monkeypatch.setattr(settings, "chunk_overlap_chars", 8)
    pages = [PageText(page_number=3, text="A" * 55 + "\n\n" + "B" * 30)]

    chunks = split_pages_to_chunks(pages)

    assert len(chunks) >= 2
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(len(chunk.chunk_text) <= 40 for chunk in chunks)
