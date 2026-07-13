from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MistakeRecord, User
from app.rag.services import MistakeAnalysisService
from app.schemas.mistake import MistakeCreate, MistakeRead, MistakeStatistics
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.post("", response_model=MistakeRead, status_code=status.HTTP_201_CREATED)
async def create_mistake(
    payload: MistakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MistakeRecord:
    analysis, result = await MistakeAnalysisService().analyze(
        question_text=payload.question_text,
        user_answer=payload.user_answer,
        correct_answer=payload.correct_answer,
    )
    if not result.succeeded:
        raise HTTPException(
            status_code=503,
            detail={
                "code": result.error_code or "llm_unavailable",
                "message": result.content,
                "llm_mode": result.mode,
            },
        )
    mistake = MistakeRecord(
        user_id=current_user.id,
        subject=payload.subject,
        question_text=payload.question_text,
        user_answer=payload.user_answer,
        correct_answer=payload.correct_answer,
        error_reason=analysis.get("error_reason"),
        knowledge_point=analysis.get("knowledge_point"),
    )
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    return mistake


@router.get("", response_model=list[MistakeRead])
def list_mistakes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[MistakeRecord]:
    return (
        db.query(MistakeRecord)
        .filter(MistakeRecord.user_id == current_user.id)
        .order_by(MistakeRecord.created_at.desc())
        .all()
    )


@router.get("/statistics", response_model=MistakeStatistics)
def mistake_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> MistakeStatistics:
    by_subject = (
        db.query(MistakeRecord.subject, func.count(MistakeRecord.id))
        .filter(MistakeRecord.user_id == current_user.id)
        .group_by(MistakeRecord.subject)
        .all()
    )
    by_point = (
        db.query(MistakeRecord.knowledge_point, func.count(MistakeRecord.id))
        .filter(MistakeRecord.user_id == current_user.id)
        .group_by(MistakeRecord.knowledge_point)
        .all()
    )
    total = db.query(MistakeRecord).filter(MistakeRecord.user_id == current_user.id).count()
    return MistakeStatistics(
        by_subject=[{"name": name or "未分类", "value": count} for name, count in by_subject],
        by_knowledge_point=[
            {"name": name or "未识别", "value": count} for name, count in by_point
        ],
        total=total,
    )
