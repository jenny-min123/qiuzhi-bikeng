"""公司快照截图录入接口（F-02 / F-03 的数据入口）。

- POST /snapshot/extract  上传截图 → OCR → 候选字段（不自动保存）
- POST /company-snapshots 人工确认后的字段写入快照并失效缓存
- GET  /company-snapshots 查看当前快照

这是本地管理接口，默认只建议在 127.0.0.1 使用；对外部署前必须加鉴权。
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import db, ocr
from ..config import settings
from ..schemas import (
    SnapshotExtractResponse,
    SnapshotUpsertRequest,
    SnapshotUpsertResponse,
)
from ..tools.snapshot_extract import extract_snapshot_fields
from ..tools.snapshot_store import (
    load_snapshot_file,
    unlocked_rules,
    upsert_record,
    validate_record,
)

router = APIRouter(tags=["snapshots"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.post("/snapshot/extract", response_model=SnapshotExtractResponse)
async def extract_snapshot_endpoint(file: UploadFile = File(...)) -> SnapshotExtractResponse:
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="图片超过 10MB，请压缩后再上传")

    result = await ocr.recognize(content, file.filename or "")
    if not result.configured:
        raise HTTPException(status_code=503, detail=result.note)
    if not result.text.strip():
        raise HTTPException(status_code=422, detail=result.note or "未识别到文字")

    return SnapshotExtractResponse(
        **extract_snapshot_fields(result.text, blocks=result.blocks)
    )


@router.post("/company-snapshots", response_model=SnapshotUpsertResponse)
def upsert_snapshot_endpoint(payload: SnapshotUpsertRequest) -> SnapshotUpsertResponse:
    company = payload.company.strip()
    record = payload.model_dump(exclude={"company"}, exclude_none=True)

    # 网页表单未涉及的字段（例如脚本录入的扩展字段）在更新时保留原值
    existing = (load_snapshot_file().get("companies") or {}).get(company)
    if isinstance(existing, dict):
        record = {**existing, **record}

    errors = validate_record(record)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "快照字段校验失败", "errors": errors},
        )

    action, similar = upsert_record(company, record)
    if action == "conflict":
        raise HTTPException(
            status_code=409,
            detail={"message": "存在名称相近的主体", "similar": similar},
        )

    # 快照变更后，旧的工商查询缓存必须失效
    db.cache_delete(f"evidence:2:工商信息:{company.lower()}")
    db.cache_delete(f"company:{company.lower()}")

    return SnapshotUpsertResponse(
        action=action,
        company=company,
        unlocked_rules=unlocked_rules(record),
        snapshot_path=str(settings.snapshot_path),
    )


@router.get("/company-snapshots")
def list_snapshots_endpoint() -> dict:
    data = load_snapshot_file()
    companies = data.get("companies") or {}
    return {
        "companies": [
            {"company": name, **facts}
            for name, facts in companies.items()
            if isinstance(facts, dict)
        ]
    }
