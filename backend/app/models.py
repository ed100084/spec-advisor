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
    department: Mapped[str] = mapped_column(String(100), default="")
    project: Mapped[str] = mapped_column(String(200), default="")
    is_information_system: Mapped[bool] = mapped_column(default=False)
    security_responsibility_level: Mapped[str] = mapped_column(String(1), default="A")
    confidentiality_level: Mapped[str] = mapped_column(String(1), default="普")
    integrity_level: Mapped[str] = mapped_column(String(1), default="普")
    availability_level: Mapped[str] = mapped_column(String(1), default="普")
    legal_compliance_level: Mapped[str] = mapped_column(String(1), default="普")
    protection_level: Mapped[str] = mapped_column(String(1), default="普")
    system_importance: Mapped[str] = mapped_column(String(255), default="")
    processes_personal_data: Mapped[bool] = mapped_column(default=False)
    personal_data_description: Mapped[str] = mapped_column(String(500), default="")
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


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    analysis_type: Mapped[str] = mapped_column(String(50))
    knowledge_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(255), default="等待執行")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


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


class BidTemplate(Base):
    """投標須知範本"""
    __tablename__ = "bid_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    procurement_type: Mapped[str] = mapped_column(String(20))  # goods, services, engineering
    file_path: Mapped[str] = mapped_column(String(500))
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BidNotice(Base):
    """AI 產生的投標須知"""
    __tablename__ = "bid_notices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("bid_templates.id"))
    result: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))  # law, internal_rule, standard, custom
    source: Mapped[str] = mapped_column(String(255), default="")  # 來源說明
    content: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ControlBaselineVersion(Base):
    """資通系統防護基準版本"""
    __tablename__ = "control_baseline_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255))
    source_filename: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    effective_date: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ControlMeasure(Base):
    """資通系統防護基準控制措施"""
    __tablename__ = "control_measures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("control_baseline_versions.id"))
    domain: Mapped[str] = mapped_column(String(100))
    item: Mapped[str] = mapped_column(String(150))
    level: Mapped[str] = mapped_column(String(1))  # 普, 中, 高
    requirement: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
