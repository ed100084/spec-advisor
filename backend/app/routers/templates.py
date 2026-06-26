"""規格書範本 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Template
from app.services.llm import generate_template

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateGenerate(BaseModel):
    category: str
    description: str


class TemplateSave(BaseModel):
    name: str
    category: str
    content: str


@router.post("/generate")
async def gen_template(req: TemplateGenerate):
    content = await generate_template(req.category, req.description)
    return {"content": content}


@router.post("")
async def save_template(req: TemplateSave, db: AsyncSession = Depends(get_db)):
    template = Template(name=req.name, category=req.category, content=req.content)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "created_at": template.created_at.isoformat(),
    }


@router.get("")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Template).order_by(Template.created_at.desc()))
    templates = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "created_at": t.created_at.isoformat(),
        }
        for t in templates
    ]


@router.get("/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(404, "範本不存在")
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "content": template.content,
        "created_at": template.created_at.isoformat(),
    }
