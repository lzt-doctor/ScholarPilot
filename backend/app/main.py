from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import auth, chat, dashboard, documents, mistakes, study_plan
from app.services.embeddings import get_embedding_service
from app.services.llm_client import get_llm_runtime_status


app = FastAPI(
    title="ScholarPilot API",
    description="Traceable RAG retrieval system for academic documents.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/details")
def health_details() -> dict:
    database_status = "unavailable"
    pgvector_status = "unavailable"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            database_status = "ok"
            installed = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar_one()
            pgvector_status = "ok" if installed else "missing"
    except Exception:
        pass
    healthy = database_status == "ok" and pgvector_status == "ok"
    return {
        "status": "ok" if healthy else "degraded",
        "service": settings.app_name,
        **get_embedding_service().runtime_status().as_dict(),
        **get_llm_runtime_status(),
        "database_status": database_status,
        "pgvector_status": pgvector_status,
    }


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(study_plan.router)
app.include_router(mistakes.router)
app.include_router(dashboard.router)
