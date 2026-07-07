from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, DocumentChunk, User
from app.schemas.document import DocumentDetail, DocumentRead
from app.services.embeddings import get_embedding_service
from app.services.pdf_parser import parse_pdf, split_pages_to_chunks, summarize_pages
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("未分类"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    upload_dir = settings.upload_path / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    stored_name = f"{uuid4().hex}_{safe_name}"
    file_path = upload_dir / stored_name

    try:
        content = await file.read()
        file_path.write_bytes(content)

        pages = parse_pdf(file_path)
        if not pages:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF")

        chunks = split_pages_to_chunks(pages)
        embeddings = get_embedding_service().embed_texts([chunk.chunk_text for chunk in chunks])

        document = Document(
            user_id=current_user.id,
            filename=safe_name,
            file_type="pdf",
            summary=summarize_pages(pages),
            category=category or "未分类",
            file_path=str(file_path),
        )
        db.add(document)
        db.flush()

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    embedding=embedding,
                    section_title=chunk.section_title,
                )
            )

        db.commit()
        db.refresh(document)
        return document
    except HTTPException:
        db.rollback()
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        db.rollback()
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}") from exc


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.upload_time.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(document.file_path) if document.file_path else None
    db.delete(document)
    db.commit()
    if file_path and file_path.exists():
        file_path.unlink(missing_ok=True)
