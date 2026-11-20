"""FastAPI 入口：挂路由 + CORS + 启动时初始化 SQLite。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .api import (
    routes_analyze,
    routes_export,
    routes_ocr,
    routes_phrases,
    routes_subject,
)
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="大专生求职避坑一站式平台 · 投递前静态筛查 + 求职过程中主体监测 + 事后证据留存",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_analyze.router)
app.include_router(routes_ocr.router)
app.include_router(routes_export.router)
app.include_router(routes_phrases.router)
app.include_router(routes_subject.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """健康检查，只暴露布尔标志，不泄露任何 key。"""
    from . import llm

    return {
        "status": "ok",
        "version": settings.version,
        "llm_configured": llm.enabled(),
        "ocr_engine": settings.ocr_engine,
        "amap_configured": bool(settings.amap_api_key),
    }
