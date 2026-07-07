from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="owner", cascade="all,delete")
    chat_sessions = relationship(
        "ChatSession", back_populates="owner", cascade="all,delete"
    )
    mistakes = relationship("MistakeRecord", back_populates="owner", cascade="all,delete")
    study_plans = relationship("StudyPlan", back_populates="owner", cascade="all,delete")

