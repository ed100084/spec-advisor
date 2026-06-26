"""協作審閱 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Review

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    document_id: str
    reviewer_name: str
    comment: str


class ReviewUpdate(BaseModel):
    status: str  # approved, rejected, pending


@router.post("")
async def create_review(req: ReviewCreate, db: AsyncSession = Depends(get_db)):
    review = Review(
        document_id=req.document_id,
        reviewer_name=req.reviewer_name,
        comment=req.comment,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return {
        "id": review.id,
        "document_id": review.document_id,
        "reviewer_name": review.reviewer_name,
        "comment": review.comment,
        "status": review.status,
        "created_at": review.created_at.isoformat(),
    }


@router.get("/document/{doc_id}")
async def get_reviews(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review).where(Review.document_id == doc_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return [
        {
            "id": r.id,
            "reviewer_name": r.reviewer_name,
            "comment": r.comment,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.patch("/{review_id}")
async def update_review_status(review_id: str, req: ReviewUpdate, db: AsyncSession = Depends(get_db)):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(404, "審閱記錄不存在")

    review.status = req.status
    await db.commit()
    return {"id": review.id, "status": review.status}
