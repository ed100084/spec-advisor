"""背景分析任務服務"""
import asyncio

from app.database import async_session
from app.models import Analysis, AnalysisJob, Document
from app.services.llm import (
    analyze_binding,
    analyze_reasonability,
    analyze_full,
    analyze_cost,
    analyze_security,
    analyze_intellectual_property,
    analyze_improvement,
)

ANALYSIS_HANDLERS = {
    "binding_check": analyze_binding,
    "reasonability": analyze_reasonability,
    "cost": analyze_cost,
    "security": analyze_security,
    "intellectual_property": analyze_intellectual_property,
    "improvement": analyze_improvement,
    "full": analyze_full,
}

ANALYSIS_LABELS = {
    "binding_check": "綁標檢測",
    "reasonability": "合理性分析",
    "cost": "成本合理性",
    "security": "資安合規",
    "intellectual_property": "智財授權檢視",
    "improvement": "改善建議",
    "full": "完整分析",
}


def schedule_analysis_job(job_id: str):
    asyncio.create_task(run_analysis_job(job_id))


async def run_analysis_job(job_id: str):
    async with async_session() as db:
        job = await db.get(AnalysisJob, job_id)
        if not job:
            return
        job.status = "running"
        job.progress = 10
        job.message = "讀取規格書內容"
        await db.commit()

        doc = await db.get(Document, job.document_id)
        if not doc or not doc.content_text:
            job.status = "failed"
            job.error = "文件不存在或內容為空"
            job.message = "分析失敗"
            await db.commit()
            return

        handler = ANALYSIS_HANDLERS.get(job.analysis_type)
        if not handler:
            job.status = "failed"
            job.error = f"不支援的分析類型: {job.analysis_type}"
            job.message = "分析失敗"
            await db.commit()
            return

        try:
            job.progress = 30
            job.message = f"執行{ANALYSIS_LABELS.get(job.analysis_type, job.analysis_type)}"
            await db.commit()

            document_meta = {
                "is_information_system": doc.is_information_system,
                "security_responsibility_level": doc.security_responsibility_level,
                "confidentiality_level": doc.confidentiality_level,
                "integrity_level": doc.integrity_level,
                "availability_level": doc.availability_level,
                "legal_compliance_level": doc.legal_compliance_level,
                "protection_level": doc.protection_level,
                "system_importance": doc.system_importance,
                "processes_personal_data": doc.processes_personal_data,
                "personal_data_description": doc.personal_data_description,
            }
            result_text = await handler(
                doc.content_text,
                knowledge_ids=job.knowledge_ids,
                document_meta=document_meta,
            )

            analysis = Analysis(
                document_id=job.document_id,
                analysis_type=job.analysis_type,
                result={"analysis": result_text},
            )
            db.add(analysis)
            await db.flush()

            job.status = "completed"
            job.progress = 100
            job.message = "分析完成"
            job.result = {
                "analysis_id": analysis.id,
                "type": job.analysis_type,
                "result": result_text,
            }
            await db.commit()
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.message = "分析失敗"
            job.error = str(exc)
            await db.commit()
