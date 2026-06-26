"""文件上傳與管理 API"""
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Document
from app.services.parser import parse_file

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}


@router.post("")
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支援的檔案格式: {suffix}")

    if file.size and file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"檔案大小超過 {settings.max_upload_size_mb}MB 限制")

    # Save file
    doc = Document(filename=file.filename, file_type=suffix.lstrip("."), file_size=file.size or 0)
    save_path = Path(settings.upload_dir) / f"{doc.id}{suffix}"
    doc.file_path = str(save_path)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse content
    try:
        doc.content_text = parse_file(str(save_path))
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"檔案解析失敗: {e}")

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "content_preview": doc.content_text[:500] if doc.content_text else "",
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.get("")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "content_text": doc.content_text,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文件不存在")

    Path(doc.file_path).unlink(missing_ok=True)
    await db.delete(doc)
    await db.commit()
    return {"message": "已刪除"}
