from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MistakeCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1)
    user_answer: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)


class MistakeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    question_text: str
    user_answer: str
    correct_answer: str
    error_reason: str | None = None
    knowledge_point: str | None = None
    created_at: datetime


class MistakeStatistics(BaseModel):
    by_subject: list[dict]
    by_knowledge_point: list[dict]
    total: int

