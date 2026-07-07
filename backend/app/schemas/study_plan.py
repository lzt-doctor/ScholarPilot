from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudyPlanGenerateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)
    background: str | None = None
    weeks: int = Field(default=8, ge=1, le=52)
    hours_per_week: int = Field(default=10, ge=1, le=80)


class StudyPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal: str
    plan_content: str
    created_at: datetime

