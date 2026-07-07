from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, chat, dashboard, documents, mistakes, study_plan


app = FastAPI(
    title="ScholarPilot API",
    description="Agentic RAG academic Q&A and study planning system.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(study_plan.router)
app.include_router(mistakes.router)
app.include_router(dashboard.router)

