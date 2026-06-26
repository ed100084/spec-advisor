"""文件上傳與管理 API"""
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Document
from app.services.parser import parse_file

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(""),
    project: str = Form(""),
    security_responsibility_level: str = Form("A"),
    confidentiality_level: str = Form("普"),
    integrity_level: str = Form("普"),
    availability_level: str = Form("普"),
    legal_compliance_level: str = Form("普"),
    system_importance: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支援的檔案格式: {suffix}")

    if file.size and file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"檔案大小超過 {settings.max_upload_size_mb}MB 限制")

    doc = Document(
        filename=file.filename,
        file_type=suffix.lstrip("."),
        file_size=file.size or 0,
        department=department,
        project=project,
        security_responsibility_level=security_responsibility_level,
        confidentiality_level=confidentiality_level,
        integrity_level=integrity_level,
        availability_level=availability_level,
        legal_compliance_level=legal_compliance_level,
        protection_level=_derive_protection_level(
            confidentiality_level,
            integrity_level,
            availability_level,
            legal_compliance_level,
        ),
        system_importance=system_importance,
    )
    save_path = Path(settings.upload_dir) / f"{doc.id}{suffix}"
    doc.file_path = str(save_path)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        doc.content_text = parse_file(str(save_path))
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"檔案解析失敗: {e}")

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return _doc_dict(doc, preview=True)


@router.get("")
async def list_documents(
    department: str = Query(None),
    project: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).order_by(Document.uploaded_at.desc())
    if department:
        query = query.where(Document.department == department)
    if project:
        query = query.where(Document.project == project)
    result = await db.execute(query)
    docs = result.scalars().all()
    return [_doc_dict(d) for d in docs]


@router.get("/filters")
async def get_filters(db: AsyncSession = Depends(get_db)):
    """取得所有已使用的部門和專案名稱，供前端篩選"""
    dept_result = await db.execute(
        select(distinct(Document.department)).where(Document.department != "")
    )
    proj_result = await db.execute(
        select(distinct(Document.project)).where(Document.project != "")
    )
    return {
        "departments": [r[0] for r in dept_result],
        "projects": [r[0] for r in proj_result],
    }


@router.get("/{doc_id}")
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    return _doc_dict(doc, include_content=True)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")

    Path(doc.file_path).unlink(missing_ok=True)
    await db.delete(doc)
    await db.commit()
    return {"message": "已刪除"}


def _doc_dict(doc: Document, preview: bool = False, include_content: bool = False):
    d = {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "department": doc.department,
        "project": doc.project,
        "security_responsibility_level": doc.security_responsibility_level,
        "confidentiality_level": doc.confidentiality_level,
        "integrity_level": doc.integrity_level,
        "availability_level": doc.availability_level,
        "legal_compliance_level": doc.legal_compliance_level,
        "protection_level": doc.protection_level,
        "system_importance": doc.system_importance,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }
    if preview:
        d["content_preview"] = doc.content_text[:500] if doc.content_text else ""
    if include_content:
        d["content_text"] = doc.content_text
    return d


def _derive_protection_level(*levels: str) -> str:
    order = {"普": 0, "中": 1, "高": 2}
    normalized = [level if level in order else "普" for level in levels]
    return max(normalized, key=lambda level: order[level])
