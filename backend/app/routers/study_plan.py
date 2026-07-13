from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyPlan, User
from app.rag.services import StudyPlannerService
from app.schemas.study_plan import StudyPlanGenerateRequest, StudyPlanRead
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


@router.post("/generate", response_model=StudyPlanRead, status_code=status.HTTP_201_CREATED)
async def generate_study_plan(
    payload: StudyPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlan:
    result = await StudyPlannerService().generate(
        goal=payload.goal,
        background=payload.background,
        weeks=payload.weeks,
        hours_per_week=payload.hours_per_week,
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
    plan = StudyPlan(
        user_id=current_user.id,
        goal=payload.goal,
        plan_content=result.content,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[StudyPlanRead])
def list_study_plans(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[StudyPlan]:
    return (
        db.query(StudyPlan)
        .filter(StudyPlan.user_id == current_user.id)
        .order_by(StudyPlan.created_at.desc())
        .all()
    )
