"""AI 分析 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Analysis, AnalysisJob, Document
from app.services.analysis_jobs import ANALYSIS_LABELS, schedule_analysis_job
from app.services.llm import compare_documents

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    knowledge_ids: list[str] | None = None  # None = 用全部啟用的, [] = 不用知識庫


class CompareRequest(BaseModel):
    doc_id_a: str
    doc_id_b: str


async def create_analysis_job(
    doc_id: str,
    analysis_type: str,
    req: AnalysisRequest | None,
    db: AsyncSession,
):
    if req is None:
        req = AnalysisRequest()
    doc = await db.get(Document, doc_id)
    if not doc or not doc.content_text:
        raise HTTPException(404, "文件不存在或內容為空")

    job = AnalysisJob(
        document_id=doc_id,
        analysis_type=analysis_type,
        knowledge_ids=req.knowledge_ids,
        status="pending",
        progress=0,
        message="等待執行",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    schedule_analysis_job(job.id)
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "type": analysis_type,
        "type_label": ANALYSIS_LABELS.get(analysis_type, analysis_type),
    }


@router.post("/{doc_id}/binding")
async def check_binding(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "binding_check", req, db)


@router.post("/{doc_id}/reasonability")
async def check_reasonability(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "reasonability", req, db)


@router.post("/{doc_id}/full")
async def full_analysis(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "full", req, db)


@router.post("/{doc_id}/cost")
async def check_cost(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "cost", req, db)


@router.post("/{doc_id}/security")
async def check_security(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "security", req, db)


@router.post("/{doc_id}/intellectual-property")
async def check_intellectual_property(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "intellectual_property", req, db)


@router.post("/{doc_id}/improvement")
async def check_improvement(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "improvement", req, db)


@router.post("/{doc_id}/pia")
async def check_pia(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "pia", req, db)


@router.post("/{doc_id}/sla")
async def check_sla(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "sla", req, db)


@router.post("/{doc_id}/vendor-lockin")
async def check_vendor_lockin(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "vendor_lockin", req, db)


@router.post("/{doc_id}/interoperability")
async def check_interoperability(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "interoperability", req, db)


@router.post("/{doc_id}/isms")
async def check_isms(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "isms", req, db)


@router.post("/{doc_id}/bcp-dr")
async def check_bcp_dr(doc_id: str, req: AnalysisRequest = None, db: AsyncSession = Depends(get_db)):
    return await create_analysis_job(doc_id, "bcp_dr", req, db)


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


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(404, "分析任務不存在")
    return {
        "job_id": job.id,
        "document_id": job.document_id,
        "type": job.analysis_type,
        "type_label": ANALYSIS_LABELS.get(job.analysis_type, job.analysis_type),
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/jobs")
async def list_active_jobs(db: AsyncSession = Depends(get_db)):
    """取得所有 pending/running 的分析任務"""
    from sqlalchemy import select

    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.status.in_(["pending", "running"]))
        .order_by(AnalysisJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return [
        {
            "job_id": j.id,
            "document_id": j.document_id,
            "type": j.analysis_type,
            "type_label": ANALYSIS_LABELS.get(j.analysis_type, j.analysis_type),
            "status": j.status,
            "progress": j.progress,
            "message": j.message,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]


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
