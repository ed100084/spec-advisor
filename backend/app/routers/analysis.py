"""AI 分析 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, Analysis
from app.services.llm import analyze_binding, analyze_reasonability, analyze_full, compare_documents

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class CompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str


@router.post("/{doc_id}/binding")
async def check_binding(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc or not doc.content_text:
        raise HTTPException(404, "文件不存在或內容為空")

    result_text = await analyze_binding(doc.content_text)

    analysis = Analysis(
        document_id=doc_id,
        analysis_type="binding_check",
        result={"analysis": result_text},
    )
    db.add(analysis)
    await db.commit()

    return {"id": analysis.id, "type": "binding_check", "result": result_text}


@router.post("/{doc_id}/reasonability")
async def check_reasonability(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc or not doc.content_text:
        raise HTTPException(404, "文件不存在或內容為空")

    result_text = await analyze_reasonability(doc.content_text)

    analysis = Analysis(
        document_id=doc_id,
        analysis_type="reasonability",
        result={"analysis": result_text},
    )
    db.add(analysis)
    await db.commit()

    return {"id": analysis.id, "type": "reasonability", "result": result_text}


@router.post("/{doc_id}/full")
async def full_analysis(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc or not doc.content_text:
        raise HTTPException(404, "文件不存在或內容為空")

    result_text = await analyze_full(doc.content_text)

    analysis = Analysis(
        document_id=doc_id,
        analysis_type="full",
        result={"analysis": result_text},
    )
    db.add(analysis)
    await db.commit()

    return {"id": analysis.id, "type": "full", "result": result_text}


@router.post("/compare")
async def compare(req: CompareRequest, db: AsyncSession = Depends(get_db)):
    doc_a = await db.get(Document, req.doc_id_a)
    doc_b = await db.get(Document, req.doc_id_b)

    if not doc_a or not doc_a.content_text:
        raise HTTPException(404, f"文件 A ({req.doc_id_a}) 不存在或內容為空")
    if not doc_b or not doc_b.content_text:
        raise HTTPException(404, f"文件 B ({req.doc_id_b}) 不存在或內容為空")

    result_text = await compare_documents(doc_a.content_text, doc_b.content_text)

    return {
        "doc_a": {"id": doc_a.id, "filename": doc_a.filename},
        "doc_b": {"id": doc_b.id, "filename": doc_b.filename},
        "result": result_text,
    }


@router.get("/{doc_id}/history")
async def get_analysis_history(doc_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(
        select(Analysis)
        .where(Analysis.document_id == doc_id)
        .order_by(Analysis.created_at.desc())
    )
    analyses = result.scalars().all()
    return [
        {
            "id": a.id,
            "type": a.analysis_type,
            "result": a.result,
            "score": a.score,
            "created_at": a.created_at.isoformat(),
        }
        for a in analyses
    ]
