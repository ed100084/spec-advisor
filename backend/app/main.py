from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import documents, analysis, reviews, templates, knowledge, bid


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Spec Advisor API",
    description="規格書檢視與建議系統",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(reviews.router)
app.include_router(templates.router)
app.include_router(knowledge.router)
app.include_router(bid.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
