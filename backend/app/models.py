import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))  # pdf, docx, xlsx
    file_size: Mapped[int] = mapped_column(Integer)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    analysis_type: Mapped[str] = mapped_column(String(50))  # binding_check, reasonability, full
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="analyses")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    reviewer_name: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped["Document"] = relationship(back_populates="reviews")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
