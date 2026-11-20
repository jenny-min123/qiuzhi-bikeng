"""OCR 统一入口（F-09）。

V3 4.9 / 6.7：F-01 与 F-06 共用同一 OCR 入口，含身份证号的图片必须
本地 OCR 或上传即删。当前框架只定义了接口与降级行为：
- 未接入 OCR 引擎时返回 configured=False，路由层明确返回 503；
- 不返回空字符串冒充识别结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings


@dataclass
class OcrResult:
    configured: bool
    text: str = ""
    entities: list[dict] = field(default_factory=list)
    engine: str = "disabled"
    note: str = ""


async def recognize(image_bytes: bytes, filename: str = "") -> OcrResult:
    """识别截图文本与主体名。

    后续接入本地 OCR（PaddleOCR / tesseract）或「上传即删」的远端引擎时，
    只改本函数，路由与前端契约不变。
    """
    if settings.ocr_engine == "disabled":
        return OcrResult(
            configured=False,
            engine="disabled",
            note="OCR 引擎未接入（V3 F-09，开发序位第 5 周）。请先粘贴 JD 文本。",
        )

    # 预留：按 OCR_ENGINE 分派到具体实现
    return OcrResult(
        configured=False,
        engine=settings.ocr_engine,
        note=f"OCR_ENGINE={settings.ocr_engine} 尚未实现，当前框架不返回伪造文本。",
    )
