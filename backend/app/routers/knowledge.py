"""知識庫管理 API - 法規、院內規章、產業標準"""
import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import KnowledgeBase, KnowledgeChunk
from app.services.parser import parse_file

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

CATEGORY_LABELS = {
    "law": "政府法規",
    "internal_rule": "院內規章",
    "standard": "產業標準",
    "custom": "自訂規則",
}


class KnowledgeCreate(BaseModel):
    name: str
    category: str
    source: str = ""
    content: str


class KnowledgeUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    source: str | None = None
    content: str | None = None
    enabled: bool | None = None



async def rebuild_chunks_for_knowledge(kb_id: str, content: str, db: AsyncSession):
    """Delete old chunks and create new ones with embeddings."""
    from app.services.embedding import chunk_text, compute_embeddings

    # Delete existing chunks
    old = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_id == kb_id))
    for chunk in old.scalars().all():
        await db.delete(chunk)

    if not content or not content.strip():
        return 0

    # Create new chunks
    chunks = chunk_text(content)
    if not chunks:
        return 0

    # Compute embeddings in batch
    embeddings = compute_embeddings(chunks)

    for i, (text, emb) in enumerate(zip(chunks, embeddings)):
        db.add(KnowledgeChunk(
            knowledge_id=kb_id,
            chunk_text=text,
            chunk_index=i,
            embedding=emb,
        ))

    return len(chunks)

@router.post("")
async def create_knowledge(req: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    kb = KnowledgeBase(
        name=req.name,
        category=req.category,
        source=req.source,
        content=req.content,
    )
    db.add(kb)
    await commit_with_retry(db)
    await db.refresh(kb)
    # Build chunks and embeddings in background
    try:
        n = await rebuild_chunks_for_knowledge(kb.id, kb.content, db)
        await db.commit()
    except Exception as e:
        logging.getLogger(__name__).warning("Embedding failed for chunk, skipping: %s", e)
    return _to_dict(kb)


@router.post("/upload")
async def upload_knowledge(
    name: str = Form(...),
    category: str = Form(...),
    source: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上傳文件作為知識庫（PDF/Word/Excel/Markdown/TXT）"""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".xlsx", ".xls", ".md", ".markdown", ".txt"}:
        raise HTTPException(400, f"不支援的檔案格式: {suffix}")

    # Save temp file and parse
    temp_path = Path(settings.upload_dir) / f"kb_temp_{uuid.uuid4().hex}{suffix}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        content = parse_file(str(temp_path))
    except Exception as e:
        raise HTTPException(500, f"檔案解析失敗: {e}")
    finally:
        temp_path.unlink(missing_ok=True)

    kb = KnowledgeBase(
        name=name,
        category=category,
        source=source or file.filename,
        content=content,
    )
    db.add(kb)
    await commit_with_retry(db)
    await db.refresh(kb)
    try:
        n = await rebuild_chunks_for_knowledge(kb.id, kb.content, db)
        await db.commit()
    except Exception as e:
        logging.getLogger(__name__).warning("Embedding failed for chunk, skipping: %s", e)
    return _to_dict(kb)


@router.get("")
async def list_knowledge(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.category, KnowledgeBase.name))
    items = result.scalars().all()
    return [_to_dict(k) for k in items]


@router.get("/categories")
async def get_categories():
    return CATEGORY_LABELS


@router.get("/{kb_id}")
async def get_knowledge(kb_id: str, db: AsyncSession = Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知識庫項目不存在")
    return _to_dict(kb, include_content=True)


@router.patch("/{kb_id}")
async def update_knowledge(kb_id: str, req: KnowledgeUpdate, db: AsyncSession = Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知識庫項目不存在")

    content_changed = req.content is not None
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(kb, field, value)

    await db.commit()
    await db.refresh(kb)

    if content_changed:
        try:
            await rebuild_chunks_for_knowledge(kb.id, kb.content, db)
            await db.commit()
        except Exception as e:
            logging.getLogger(__name__).warning("Embedding failed for chunk, skipping: %s", e)

    return _to_dict(kb)


@router.delete("/{kb_id}")
async def delete_knowledge(kb_id: str, db: AsyncSession = Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(404, "知識庫項目不存在")
    old_chunks = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_id == kb_id))
    for chunk in old_chunks.scalars().all():
        await db.delete(chunk)
    await db.delete(kb)
    await db.commit()
    return {"message": "已刪除"}



@router.post("/re-embed")
async def re_embed_all(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase))
    items = result.scalars().all()
    total_chunks = 0
    for kb in items:
        n = await rebuild_chunks_for_knowledge(kb.id, kb.content, db)
        total_chunks += n
    await db.commit()
    return {"message": f"已重建 {len(items)} 個知識庫，共 {total_chunks} 個 chunks"}

def _to_dict(kb: KnowledgeBase, include_content: bool = False):
    d = {
        "id": kb.id,
        "name": kb.name,
        "category": kb.category,
        "category_label": CATEGORY_LABELS.get(kb.category, kb.category),
        "source": kb.source,
        "enabled": kb.enabled,
        "content_length": len(kb.content) if kb.content else 0,
        "created_at": kb.created_at.isoformat(),
    }
    if include_content:
        d["content"] = kb.content
    return d


async def commit_with_retry(db: AsyncSession, retries: int = 5):
    for attempt in range(retries):
        try:
            await db.commit()
            return
        except Exception as exc:
            await db.rollback()
            if "database is locked" not in str(exc).lower() or attempt == retries - 1:
                raise HTTPException(500, f"資料庫寫入失敗: {exc}")
            await asyncio.sleep(0.5 * (attempt + 1))
