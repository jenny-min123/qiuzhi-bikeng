"""OCR 接口：/ocr（F-09 截图统一入口）。"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import ocr
from ..schemas import OcrResponse

router = APIRouter(tags=["ocr"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.post("/ocr", response_model=OcrResponse)
async def ocr_endpoint(file: UploadFile = File(...)) -> OcrResponse:
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="图片超过 10MB，请压缩后再上传")

    result = await ocr.recognize(content, file.filename or "")
    if not result.configured:
        # 明确告知未接入，而不是返回空文本冒充识别成功
        raise HTTPException(status_code=503, detail=result.note)

    return OcrResponse(text=result.text, entities=result.entities)
