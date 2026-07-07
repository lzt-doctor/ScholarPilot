from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage, ChatSession, User
from app.rag.agents import RetrievalAgent
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse, ChatSessionRead
from app.services.llm_client import get_llm_client
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    session = _get_or_create_session(db, current_user.id, payload)

    retrieval_agent = RetrievalAgent()
    sources = retrieval_agent.retrieve(
        db=db,
        user_id=current_user.id,
        question=payload.question,
        top_k=payload.top_k,
    )
    context = "\n\n".join(
        (
            f"[{source.document_name} p.{source.page_number} "
            f"chunk {source.chunk_index} similarity {source.similarity or 0:.2f}] "
            f"{source.chunk_text}"
        )
        for source in sources
    )
    answer = await get_llm_client().generate_answer(payload.question, context)
    confidence = _estimate_confidence([source.similarity for source in sources])
    source_payload = [source.__dict__ for source in sources]

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.question))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            sources=source_payload,
        )
    )
    db.commit()

    return ChatResponse(
        answer=answer,
        sources=source_payload,
        confidence=confidence,
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

    title = payload.question[:40] or "新的问答会话"
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.flush()
    return session


def _estimate_confidence(similarities: list[float | None]) -> str:
    usable = [score for score in similarities if score is not None]
    reliable = [score for score in usable if score >= 0.55]
    if not usable or max(usable) < 0.25:
        return "low"
    best = max(usable)
    if best >= 0.72 and len(reliable) >= 2:
        return "high"
    if best >= 0.4 or reliable:
        return "medium"
    return "low"
