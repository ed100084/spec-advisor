"""投標須知產生 API"""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import BidTemplate, BidNotice, Document
from app.services.parser import parse_file
from app.services.llm import generate_bid_notice

router = APIRouter(prefix="/api/bid", tags=["bid"])

PROCUREMENT_TYPES = {
    "goods": "財物",
    "services": "勞務",
    "engineering": "工程",
}


# === 投標須知範本管理 ===

@router.post("/templates")
async def upload_bid_template(
    name: str = Form(...),
    procurement_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".xlsx", ".xls", ".txt"}:
        raise HTTPException(400, f"不支援的檔案格式: {suffix}")

    tmpl = BidTemplate(
        name=name,
        procurement_type=procurement_type,
    )
    save_path = Path(settings.upload_dir) / f"bid_tmpl_{tmpl.id}{suffix}"
    tmpl.file_path = str(save_path)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if suffix == ".txt":
            tmpl.content_text = save_path.read_text(encoding="utf-8")
        else:
            tmpl.content_text = parse_file(str(save_path))
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"檔案解析失敗: {e}")

    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)

    return {
        "id": tmpl.id,
        "name": tmpl.name,
        "procurement_type": tmpl.procurement_type,
        "procurement_type_label": PROCUREMENT_TYPES.get(tmpl.procurement_type, tmpl.procurement_type),
        "content_preview": tmpl.content_text[:300] if tmpl.content_text else "",
        "created_at": tmpl.created_at.isoformat(),
    }


@router.get("/templates")
async def list_bid_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BidTemplate).order_by(BidTemplate.created_at.desc()))
    templates = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "procurement_type": t.procurement_type,
            "procurement_type_label": PROCUREMENT_TYPES.get(t.procurement_type, t.procurement_type),
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.delete("/templates/{tmpl_id}")
async def delete_bid_template(tmpl_id: str, db: AsyncSession = Depends(get_db)):
    tmpl = await db.get(BidTemplate, tmpl_id)
    if not tmpl:
        raise HTTPException(404, "範本不存在")
    Path(tmpl.file_path).unlink(missing_ok=True)
    await db.delete(tmpl)
    await db.commit()
    return {"message": "已刪除"}


# === 投標須知產生 ===

class GenerateRequest(BaseModel):
    document_id: str
    template_id: str


@router.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, req.document_id)
    if not doc or not doc.content_text:
        raise HTTPException(404, "規格書不存在或內容為空")

    tmpl = await db.get(BidTemplate, req.template_id)
    if not tmpl or not tmpl.content_text:
        raise HTTPException(404, "投標須知範本不存在或內容為空")

    result_text = await generate_bid_notice(
        spec_content=doc.content_text,
        template_content=tmpl.content_text,
        procurement_type=PROCUREMENT_TYPES.get(tmpl.procurement_type, tmpl.procurement_type),
    )

    notice = BidNotice(
        document_id=req.document_id,
        template_id=req.template_id,
        result=result_text,
    )
    db.add(notice)
    await db.commit()

    return {
        "id": notice.id,
        "document": doc.filename,
        "template": tmpl.name,
        "result": result_text,
        "created_at": notice.created_at.isoformat(),
    }


@router.get("/history")
async def get_history(document_id: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(BidNotice).order_by(BidNotice.created_at.desc())
    if document_id:
        query = query.where(BidNotice.document_id == document_id)
    result = await db.execute(query)
    notices = result.scalars().all()

    items = []
    for n in notices:
        doc = await db.get(Document, n.document_id)
        tmpl = await db.get(BidTemplate, n.template_id)
        items.append({
            "id": n.id,
            "document": doc.filename if doc else "已刪除",
            "template": tmpl.name if tmpl else "已刪除",
            "result": n.result,
            "created_at": n.created_at.isoformat(),
        })
    return items
