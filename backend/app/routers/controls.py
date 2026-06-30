"""資通系統防護基準控制措施管理 API"""
import json
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import ControlBaselineVersion, ControlMeasure
from app.services.llm import call_llm_json
from app.services.parser import parse_file

router = APIRouter(prefix="/api/controls", tags=["controls"])

LEVEL_ORDER = {"普": 0, "中": 1, "高": 2}


class ControlMeasureUpdate(BaseModel):
    domain: str | None = None
    item: str | None = None
    level: str | None = None
    requirement: str | None = None
    source_text: str | None = None
    sort_order: int | None = None


class ControlMeasureCreate(BaseModel):
    version_id: str
    domain: str
    item: str
    level: str = "普"
    requirement: str
    source_text: str = ""
    sort_order: int | None = None


@router.post("/import")
async def import_control_baseline(
    name: str = Form(...),
    source: str = Form(""),
    effective_date: str = Form(""),
    expected_count: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".xlsx", ".xls", ".md", ".markdown", ".txt"}:
        raise HTTPException(400, f"不支援的檔案格式: {suffix}")

    temp_path = Path(settings.upload_dir) / f"controls_import{suffix}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        content = parse_file(str(temp_path))
    except Exception as exc:
        raise HTTPException(500, f"檔案解析失敗: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)

    version = ControlBaselineVersion(
        name=name,
        source_filename=file.filename,
        source=source,
        effective_date=effective_date,
    )
    db.add(version)
    await db.flush()

    measures = await extract_control_measures(content, expected_count=expected_count)
    for index, measure in enumerate(measures):
        db.add(ControlMeasure(
            version_id=version.id,
            domain=measure.get("domain", "未分類"),
            item=measure.get("item", "未命名控制項"),
            level=normalize_level(measure.get("level", "普")),
            requirement=measure.get("requirement", ""),
            source_text=measure.get("source_text", ""),
            sort_order=index,
        ))

    await db.commit()
    warnings = []
    if expected_count and len(measures) < expected_count:
        warnings.append(f"預期 {expected_count} 項，但只匯入 {len(measures)} 項，請檢查 PDF 解析或補登缺漏項。")
    return {
        "version_id": version.id,
        "name": version.name,
        "imported_count": len(measures),
        "expected_count": expected_count,
        "warnings": warnings,
    }


@router.get("/versions")
async def list_versions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ControlBaselineVersion).order_by(ControlBaselineVersion.created_at.desc())
    )
    versions = result.scalars().all()
    items = []
    for version in versions:
        count_result = await db.execute(
            select(ControlMeasure).where(ControlMeasure.version_id == version.id)
        )
        measures = count_result.scalars().all()
        items.append({
            "id": version.id,
            "name": version.name,
            "source_filename": version.source_filename,
            "source": version.source,
            "effective_date": version.effective_date,
            "status": version.status,
            "measure_count": len(measures),
            "created_at": version.created_at.isoformat(),
        })
    return items


@router.get("/measures")
async def list_measures(
    version_id: str | None = None,
    level: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ControlMeasure).order_by(ControlMeasure.domain, ControlMeasure.item, ControlMeasure.sort_order)
    if version_id:
        query = query.where(ControlMeasure.version_id == version_id)
    if level:
        allowed = levels_to_include(level)
        query = query.where(ControlMeasure.level.in_(allowed))
    result = await db.execute(query)
    measures = result.scalars().all()
    return [measure_dict(m) for m in measures]


@router.post("/measures")
async def create_measure(req: ControlMeasureCreate, db: AsyncSession = Depends(get_db)):
    version = await db.get(ControlBaselineVersion, req.version_id)
    if not version:
        raise HTTPException(404, "基準版本不存在")
    measure = ControlMeasure(
        version_id=req.version_id,
        domain=req.domain.strip() or "未分類",
        item=req.item.strip() or "未命名控制項",
        level=normalize_level(req.level),
        requirement=req.requirement.strip(),
        source_text=req.source_text.strip(),
        sort_order=req.sort_order if req.sort_order is not None else 9999,
    )
    db.add(measure)
    await db.commit()
    await db.refresh(measure)
    return measure_dict(measure)


@router.patch("/measures/{measure_id}")
async def update_measure(measure_id: str, req: ControlMeasureUpdate, db: AsyncSession = Depends(get_db)):
    measure = await db.get(ControlMeasure, measure_id)
    if not measure:
        raise HTTPException(404, "控制措施不存在")
    for field, value in req.model_dump(exclude_none=True).items():
        if field == "level":
            value = normalize_level(value)
        setattr(measure, field, value)
    await db.commit()
    await db.refresh(measure)
    return measure_dict(measure)


@router.delete("/measures/{measure_id}")
async def delete_measure(measure_id: str, db: AsyncSession = Depends(get_db)):
    measure = await db.get(ControlMeasure, measure_id)
    if not measure:
        raise HTTPException(404, "控制措施不存在")
    await db.delete(measure)
    await db.commit()
    return {"message": "已刪除"}


@router.delete("/versions/{version_id}")
async def delete_version(version_id: str, db: AsyncSession = Depends(get_db)):
    version = await db.get(ControlBaselineVersion, version_id)
    if not version:
        raise HTTPException(404, "基準版本不存在")
    await db.execute(delete(ControlMeasure).where(ControlMeasure.version_id == version_id))
    await db.delete(version)
    await db.commit()
    return {"message": "已刪除"}


def levels_to_include(level: str) -> list[str]:
    normalized = normalize_level(level)
    rank = LEVEL_ORDER[normalized]
    return [name for name, value in LEVEL_ORDER.items() if value <= rank]


def normalize_level(level: str) -> str:
    return level if level in LEVEL_ORDER else "普"


def measure_dict(measure: ControlMeasure):
    return {
        "id": measure.id,
        "version_id": measure.version_id,
        "domain": measure.domain,
        "item": measure.item,
        "level": measure.level,
        "requirement": measure.requirement,
        "source_text": measure.source_text,
        "sort_order": measure.sort_order,
        "created_at": measure.created_at.isoformat(),
    }


async def extract_control_measures(content: str, expected_count: int | None = None) -> list[dict]:
    chunks = split_content(content, max_chars=5500)
    all_measures = []
    for chunk in chunks:
        prompt = f"""請從以下「資通系統防護基準」文字萃取控制措施，輸出有效 JSON。

每筆控制措施需要欄位：
- domain: 控制領域，例如「存取控制」
- item: 控制項，例如「帳號管理」、「最小權限」
- level: 僅能是「普」、「中」、「高」
- requirement: 該等級的具體要求，保留條列內容
- source_text: 原文片段

請只輸出：
{{"measures":[{{"domain":"","item":"","level":"普","requirement":"","source_text":""}}]}}

原文：
{chunk}
"""
        data = await call_llm_json(prompt)
        measures = data.get("measures", [])
        if isinstance(measures, list):
            all_measures.extend(m for m in measures if isinstance(m, dict))
    measures = dedupe_measures(all_measures)
    if expected_count and len(measures) < expected_count:
        measures = await recover_missing_measures(content, measures, expected_count)
    return measures


async def recover_missing_measures(content: str, current_measures: list[dict], expected_count: int) -> list[dict]:
    existing = "\n".join(
        f"- {m.get('domain','')} / {m.get('item','')} / {m.get('level','')} / {m.get('requirement','')[:80]}"
        for m in current_measures
    )
    prompt = f"""你正在校對資通系統防護基準控制措施匯入結果。

預期控制措施數量：{expected_count}
目前已萃取數量：{len(current_measures)}

請重新檢查原文，找出「目前已萃取清單」沒有包含的控制措施。
特別注意：
1. 同一控制項在「普 / 中 / 高」不同等級應視為不同控制措施。
2. 若文字提到「等級中之所有控制措施」或「等級普之所有控制措施」，不要把它當作唯一要求；仍須保留該等級自己的條列要求。
3. 跨頁、跨行、表格換列的要求也要萃取。

請只輸出：
{{"measures":[{{"domain":"","item":"","level":"普","requirement":"","source_text":""}}]}}

目前已萃取清單：
{existing[:12000]}

原文：
{content[:20000]}
"""
    data = await call_llm_json(prompt)
    missing = data.get("measures", [])
    if isinstance(missing, list):
        return dedupe_measures(current_measures + [m for m in missing if isinstance(m, dict)])
    return current_measures


def split_content(content: str, max_chars: int = 5500) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", content or "").strip()
    if not text:
        return []
    chunks = []
    current = ""
    for paragraph in re.split(r"\n{2,}", text):
        if len(current) + len(paragraph) + 2 > max_chars:
            if current:
                chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        chunks.append(current)
    return chunks


def dedupe_measures(measures: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for measure in measures:
        key = (
            measure.get("domain", "").strip(),
            measure.get("item", "").strip(),
            normalize_level(measure.get("level", "普")),
            measure.get("requirement", "").strip()[:80],
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(measure)
    return result
