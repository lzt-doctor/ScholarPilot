from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ChatMessage, ChatSession, User
from app.rag.citations import validate_citations
from app.rag.evidence import estimate_evidence_strength, has_sufficient_evidence
from app.rag.services import RetrievalService
from app.rag.types import EmbeddingVersionMismatchError
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse, ChatSessionRead
from app.services.embeddings import EmbeddingError, get_embedding_service
from app.services.llm_client import LLMResult, get_llm_client
from app.utils.dependencies import get_current_user


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    session = _get_or_create_session(db, current_user.id, payload)
    embedding_service = get_embedding_service()
    retrieval_service = RetrievalService(embedding_service)
    try:
        retrieval = retrieval_service.retrieve(
            db=db,
            user_id=current_user.id,
            question=payload.question,
            mode=payload.retrieval_mode,
            top_k=payload.top_k,
            ef_search=payload.ef_search,
        )
    except EmbeddingVersionMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": exc.code,
                "message": "文档向量版本与当前模型不一致，请重新索引后再检索。",
                "document_ids": exc.document_ids,
            },
        ) from exc
    except EmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": "Embedding 服务不可用，请检查运行配置。"},
        ) from exc

    sources = retrieval.sources
    evidence_strength = estimate_evidence_strength(sources)
    if has_sufficient_evidence(sources, settings.retrieval_min_relevance):
        context = "\n\n".join(
            (
                f"[{number}] {source.document_name}, 第 {source.page_number} 页, "
                f"chunk {source.chunk_index}\n{source.chunk_text}"
            )
            for number, source in enumerate(sources, start=1)
        )
        llm_result = await get_llm_client().generate_answer(payload.question, context)
        citation = validate_citations(
            llm_result.content,
            sources,
            require_citation=llm_result.succeeded,
        )
    else:
        llm_result = LLMResult(
            content="知识库证据不足。请补充相关资料、重新索引文档或调整问题后重试。",
            provider=settings.llm_provider,
            model=settings.llm_model,
            mode="not_called",
            status="skipped_insufficient_evidence",
        )
        citation = validate_citations(llm_result.content, sources, require_citation=False)

    source_payload = [source.as_dict() for source in sources]
    embedding_metadata = embedding_service.runtime_status().as_dict()
    llm_metadata = llm_result.runtime_metadata()
    runtime_metadata = {
        **embedding_metadata,
        "llm_provider": llm_metadata["provider"],
        "llm_model": llm_metadata["model"],
        "llm_mode": llm_metadata["mode"],
        "llm_status": llm_metadata["status"],
        "llm_error_code": llm_metadata["error_code"],
        "retrieval_mode": retrieval.mode,
        "retrieval_parameters": retrieval.parameters,
    }

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.question))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=llm_result.content,
            sources=source_payload,
            runtime_metadata=runtime_metadata,
            evidence_strength=evidence_strength,
            citation_validity=citation.valid,
            cited_source_ids=citation.cited_source_ids,
        )
    )
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "chat_persistence_failed", "message": "问答记录保存失败。"},
        ) from exc

    return ChatResponse(
        answer=llm_result.content,
        sources=source_payload,
        evidence_strength=evidence_strength,
        confidence=evidence_strength,
        citation_validity=citation.valid,
        cited_source_ids=citation.cited_source_ids,
        runtime_metadata=runtime_metadata,
        session_id=session.id,
    )


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.delete(session)
    db.commit()


@router.get("/history", response_model=list[ChatMessageRead])
def history(
    session_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    query = db.query(ChatMessage).join(ChatSession).filter(ChatSession.user_id == current_user.id)
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        query = query.filter(ChatMessage.session_id == session_id)
    return query.order_by(ChatMessage.created_at.asc()).limit(limit).all()


def _get_or_create_session(db: Session, user_id: int, payload: ChatRequest) -> ChatSession:
    if payload.session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == payload.session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return session
    session = ChatSession(user_id=user_id, title=payload.question[:40] or "新的问答会话")
    db.add(session)
    db.flush()
    return session
