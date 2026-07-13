import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, DocumentChunk, User
from app.rag.services import RetrievalService
from app.schemas.document import DocumentDetail, DocumentRead
from app.services.embeddings import EmbeddingError, EmbeddingService, get_embedding_service
from app.services.pdf_parser import parse_pdf, split_pages_to_chunks, summarize_pages
from app.utils.dependencies import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])
_READ_BLOCK_SIZE = 1024 * 1024


async def _read_validated_pdf(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_file_type", "message": "仅支持 PDF 文件。"},
        )
    maximum = settings.max_upload_size_mb * 1024 * 1024
    content = bytearray()
    while block := await file.read(_READ_BLOCK_SIZE):
        content.extend(block)
        if len(content) > maximum:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "file_too_large",
                    "message": f"PDF 大小不能超过 {settings.max_upload_size_mb} MB。",
                },
            )
    if not bytes(content[:1024]).lstrip().startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_pdf_content", "message": "文件内容不是有效的 PDF。"},
        )
    return bytes(content)


def _process_document_file(file_path: Path, embedding_service: EmbeddingService):
    pages = parse_pdf(file_path)
    if not pages:
        raise ValueError("no_extractable_text")
    chunks = split_pages_to_chunks(pages)
    if not chunks:
        raise ValueError("no_chunks")
    embeddings = embedding_service.embed_texts([chunk.chunk_text for chunk in chunks])
    return pages, chunks, embeddings


def _replace_chunks(
    db: Session,
    document: Document,
    chunks,
    embeddings: list[list[float]],
) -> None:
    document.chunks.clear()
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


def _set_index_failure(db: Session, document_id: int, code: str) -> None:
    db.rollback()
    document = db.get(Document, document_id)
    if document:
        document.indexing_status = "failed"
        document.indexing_error = code
        db.commit()


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("未分类"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    content = await _read_validated_pdf(file)
    upload_dir = settings.upload_path / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "document.pdf").name
    file_path = upload_dir / f"{uuid4().hex}_{safe_name}"
    await run_in_threadpool(file_path.write_bytes, content)

    embedding_service = get_embedding_service()
    identity = embedding_service.identity
    document = Document(
        user_id=current_user.id,
        filename=safe_name,
        file_type="pdf",
        category=(category or "未分类")[:100],
        file_path=str(file_path),
        embedding_model=identity.model,
        embedding_dimension=identity.dimension,
        embedding_version=identity.version,
        indexing_status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        pages, chunks, embeddings = await run_in_threadpool(
            _process_document_file, file_path, embedding_service
        )
        document.summary = summarize_pages(pages)
        _replace_chunks(db, document, chunks, embeddings)
        document.indexing_status = "ready"
        document.indexing_error = None
        db.commit()
        db.refresh(document)
        RetrievalService.invalidate_user_cache(current_user.id)
        return document
    except EmbeddingError as exc:
        logger.exception("Embedding failed while indexing document %s", document.id)
        _set_index_failure(db, document.id, exc.code)
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "message": "文档已保存，但 embedding 生成失败。",
                "document_id": document.id,
            },
        ) from exc
    except Exception as exc:
        logger.exception("PDF processing failed for document %s", document.id)
        _set_index_failure(db, document.id, "pdf_processing_failed")
        raise HTTPException(
            status_code=422,
            detail={
                "code": "pdf_processing_failed",
                "message": "PDF 无法解析或没有可提取文本。",
                "document_id": document.id,
            },
        ) from exc


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


@router.post("/{document_id}/reindex", response_model=DocumentRead)
async def reindex_document(
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
    file_path = Path(document.file_path) if document.file_path else None
    if not file_path or not file_path.is_file():
        raise HTTPException(
            status_code=409,
            detail={"code": "source_file_missing", "message": "原始 PDF 不存在，无法重新索引。"},
        )

    embedding_service = get_embedding_service()
    document.indexing_status = "processing"
    document.indexing_error = None
    db.commit()
    RetrievalService.invalidate_user_cache(current_user.id)
    try:
        pages, chunks, embeddings = await run_in_threadpool(
            _process_document_file, file_path, embedding_service
        )
        identity = embedding_service.identity
        document = db.get(Document, document_id)
        document.summary = summarize_pages(pages)
        document.embedding_model = identity.model
        document.embedding_dimension = identity.dimension
        document.embedding_version = identity.version
        _replace_chunks(db, document, chunks, embeddings)
        document.indexing_status = "ready"
        db.commit()
        db.refresh(document)
        RetrievalService.invalidate_user_cache(current_user.id)
        return document
    except EmbeddingError as exc:
        logger.exception("Embedding failed while reindexing document %s", document_id)
        _set_index_failure(db, document_id, exc.code)
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": "重新索引失败，请检查 embedding 配置。"},
        ) from exc
    except Exception as exc:
        logger.exception("Reindex failed for document %s", document_id)
        _set_index_failure(db, document_id, "reindex_failed")
        raise HTTPException(
            status_code=422,
            detail={"code": "reindex_failed", "message": "重新索引失败，原始 PDF 可能已损坏。"},
        ) from exc


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
    RetrievalService.invalidate_user_cache(current_user.id)
    if file_path and file_path.exists():
        file_path.unlink(missing_ok=True)
