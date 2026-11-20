"""分析接口：/analyze、/analyze/stream（SSE）、/batch、/reports/{id}。"""

from __future__ import annotations

import asyncio
import json
from collections import Counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db
from ..orchestrator import analyze
from ..schemas import (
    AnalyzeReport,
    AnalyzeRequest,
    BatchItem,
    BatchRequest,
    BatchResponse,
)
from ..tools.scan_phrases import scan_phrases

router = APIRouter(tags=["analyze"])


def _suggest_jd_only(level: str) -> str:
    if level == "high":
        return "建议放弃"
    if level == "medium":
        return "谨慎投递"
    return "建议投递"


@router.post("/analyze", response_model=AnalyzeReport)
async def analyze_endpoint(payload: AnalyzeRequest) -> AnalyzeReport:
    return await analyze(payload.jd_text, payload.company_name)


@router.post("/analyze/stream")
async def analyze_stream(payload: AnalyzeRequest) -> StreamingResponse:
    """SSE 推送分析进度，最后推送 event: report。"""
    queue: asyncio.Queue = asyncio.Queue()

    async def progress(stage: str, message: str) -> None:
        await queue.put(("progress", {"stage": stage, "message": message}))

    async def run() -> None:
        try:
            report = await analyze(
                payload.jd_text, payload.company_name, progress=progress
            )
            await queue.put(("report", report.model_dump(mode="json")))
        except Exception as exc:  # 兜底：任何异常都通过 SSE 告知前端
            await queue.put(("error", {"message": f"分析失败：{exc}"}))
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())

    async def event_stream():
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield (
                    f"event: {event}\n"
                    f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                )
                if event in ("report", "error"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/batch", response_model=BatchResponse)
async def batch_endpoint(payload: BatchRequest) -> BatchResponse:
    items: list[BatchItem] = []
    distribution = {"high": 0, "medium": 0, "low": 0}
    categories: Counter[str] = Counter()

    for index, jd_text in enumerate(payload.jd_list):
        result = await asyncio.to_thread(scan_phrases, jd_text)
        items.append(
            BatchItem(
                jd_index=index,
                score=result["score"],
                level=result["level"],
                suggestion=_suggest_jd_only(result["level"]),
            )
        )
        distribution[result["level"]] += 1
        for hit in result["hits"]:
            categories[hit["type"]] += 1

    return BatchResponse(
        items=items,
        risk_distribution=distribution,
        risk_categories=dict(categories),
    )


@router.get("/reports/{report_id}")
async def get_report_endpoint(report_id: str) -> dict:
    report = db.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    return report
