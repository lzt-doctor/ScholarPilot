from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ChatSession,
    Document,
    DocumentChunk,
    MistakeRecord,
    StudyPlan,
    User,
)
from app.schemas.dashboard import DashboardSummary
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> DashboardSummary:
    documents_count = db.query(Document).filter(Document.user_id == current_user.id).count()
    chunks_count = (
        db.query(DocumentChunk)
        .join(Document)
        .filter(Document.user_id == current_user.id)
        .count()
    )
    chat_sessions_count = (
        db.query(ChatSession).filter(ChatSession.user_id == current_user.id).count()
    )
    mistakes_count = (
        db.query(MistakeRecord).filter(MistakeRecord.user_id == current_user.id).count()
    )
    study_plans_count = (
        db.query(StudyPlan).filter(StudyPlan.user_id == current_user.id).count()
    )

    recent_documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.upload_time.desc())
        .limit(5)
        .all()
    )
    mistakes_by_subject = (
        db.query(MistakeRecord.subject, func.count(MistakeRecord.id))
        .filter(MistakeRecord.user_id == current_user.id)
        .group_by(MistakeRecord.subject)
        .all()
    )
    documents_by_category = (
        db.query(Document.category, func.count(Document.id))
        .filter(Document.user_id == current_user.id)
        .group_by(Document.category)
        .all()
    )

    return DashboardSummary(
        documents_count=documents_count,
        chunks_count=chunks_count,
        chat_sessions_count=chat_sessions_count,
        mistakes_count=mistakes_count,
        study_plans_count=study_plans_count,
        recent_documents=[
            {
                "id": item.id,
                "filename": item.filename,
                "category": item.category,
                "upload_time": item.upload_time.isoformat(),
            }
            for item in recent_documents
        ],
        mistakes_by_subject=[
            {"name": name or "未分类", "value": count}
            for name, count in mistakes_by_subject
        ],
        documents_by_category=[
            {"name": name or "未分类", "value": count}
            for name, count in documents_by_category
        ],
    )

