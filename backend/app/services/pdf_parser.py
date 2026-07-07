from dataclasses import dataclass
from pathlib import Path
import re

import fitz

from app.config import settings


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class TextChunk:
    page_number: int
    chunk_index: int
    chunk_text: str
    section_title: str | None = None


def parse_pdf(file_path: str | Path) -> list[PageText]:
    """Extract text from every page of a PDF with PyMuPDF."""

    pages: list[PageText] = []
    with fitz.open(file_path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page_number=index, text=normalize_text(text)))
    return pages


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def guess_section_title(text: str) -> str | None:
    for line in text.splitlines():
        candidate = line.strip()
        if 4 <= len(candidate) <= 80 and not candidate.endswith((".", "。", ",")):
            return candidate[:80]
    return None


def split_pages_to_chunks(pages: list[PageText]) -> list[TextChunk]:
    """Split pages by paragraphs, preserving page numbers for citations."""

    chunks: list[TextChunk] = []
    max_chars = settings.max_chunk_chars
    overlap = settings.chunk_overlap_chars

    for page in pages:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page.text) if p.strip()]
        current = ""
        chunk_index = 0

        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= max_chars:
                current = f"{current}\n\n{paragraph}".strip()
                continue

            if current:
                chunks.append(
                    TextChunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        chunk_text=current,
                        section_title=guess_section_title(current),
                    )
                )
                chunk_index += 1
                current = current[-overlap:] if overlap and len(current) > overlap else ""

            if len(paragraph) > max_chars:
                for start in range(0, len(paragraph), max_chars - overlap):
                    piece = paragraph[start : start + max_chars]
                    chunks.append(
                        TextChunk(
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            chunk_text=piece,
                            section_title=guess_section_title(piece),
                        )
                    )
                    chunk_index += 1
                current = ""
            else:
                current = f"{current}\n\n{paragraph}".strip()

        if current:
            chunks.append(
                TextChunk(
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    chunk_text=current,
                    section_title=guess_section_title(current),
                )
            )

    return chunks


def summarize_pages(pages: list[PageText], max_chars: int = 500) -> str:
    combined = " ".join(page.text for page in pages)
    if len(combined) <= max_chars:
        return combined
    return combined[:max_chars].rstrip() + "..."

