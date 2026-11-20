"""导出接口：/export（F-04，开发序位第 8 周）。

报告数据此刻已经能按 report_id 取出；PDF / 长图渲染器尚未接入，
接口返回 501 并说明原因，不返回伪造文件。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import ExportRequest

router = APIRouter(tags=["export"])


@router.post("/export")
async def export_endpoint(payload: ExportRequest) -> dict:
    report = db.get_report(payload.report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    raise HTTPException(
        status_code=501,
        detail="PDF / 长图导出渲染器尚未接入（V3 开发序位第 8 周）。报告 JSON 已可通过 GET /reports/{report_id} 获取。",
    )
