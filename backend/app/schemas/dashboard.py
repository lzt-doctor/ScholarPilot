from pydantic import BaseModel


class DashboardSummary(BaseModel):
    documents_count: int
    chunks_count: int
    chat_sessions_count: int
    mistakes_count: int
    study_plans_count: int
    recent_documents: list[dict]
    mistakes_by_subject: list[dict]
    documents_by_category: list[dict]

