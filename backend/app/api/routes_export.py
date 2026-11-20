"""导出接口：/export（F-04）。

报告数据来自数据库中的 AnalyzeReport JSON，导出过程不重新计算分数。
- format=pdf → reportlab 生成 A4 PDF
- format=png → Pillow 生成长图
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from .. import db
from ..report_export import render_pdf, render_png
from ..schemas import ExportRequest

router = APIRouter(tags=["export"])


@router.post("/export")
async def export_endpoint(payload: ExportRequest) -> Response:
    report = db.get_report(payload.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在或已过期")

    try:
        if payload.format == "pdf":
            content = render_pdf(report)
            media_type = "application/pdf"
            extension = "pdf"
        else:
            content = render_png(report)
            media_type = "image/png"
            extension = "png"
    except RuntimeError as exc:
        # 缺少中文字体等环境问题：明确报错，不返回损坏文件
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = f"{payload.report_id}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
