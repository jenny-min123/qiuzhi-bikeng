"""OCR 统一入口（F-09）。

本地 OCR（RapidOCR + onnxruntime），图片不出本机，符合 V3 6.7 的隐私要求：
含身份证号、付款信息的截图不上传第三方。
未安装引擎或加载失败时明确返回 configured=False，不返回伪造文本。
"""

from __future__ import annotations

import asyncio
import io
import os
import site
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings
from .tools.company_names import extract_company_names

_engine = None
_engine_loaded = False
_engine_error = ""


@dataclass
class OcrResult:
    configured: bool
    text: str = ""
    entities: list[dict] = field(default_factory=list)
    engine: str = "disabled"
    note: str = ""
    # 每行文字及其坐标框 [x0, y0, x1, y1]，供表格类截图按位置配对字段
    blocks: list[dict] = field(default_factory=list)


def _dll_directories() -> list[str]:
    """onnxruntime 在部分 Windows 机器上缺 MSVCP140_1.dll，这里补充搜索目录。"""
    candidates: list[str] = []
    env_dir = os.getenv("MSVC_DLL_DIR")
    if env_dir:
        candidates.append(env_dir)
    candidates.append(str(Path(__file__).resolve().parent.parent / "vendor" / "msvc"))
    try:
        user_site = site.getusersitepackages()
        candidates.append(user_site)
        candidates.append(str(Path(user_site).parent / "Scripts"))
    except Exception:
        pass
    return [path for path in candidates if path and Path(path).is_dir()]


def _prepare_dll_path() -> None:
    if os.name != "nt":
        return
    for directory in _dll_directories():
        try:
            os.add_dll_directory(directory)
        except (OSError, AttributeError):
            continue


def _load_engine():
    global _engine, _engine_loaded, _engine_error
    if _engine_loaded:
        return _engine
    _engine_loaded = True

    if (settings.ocr_engine or "").lower() == "disabled":
        _engine_error = "OCR 已在配置中关闭（OCR_ENGINE=disabled）"
        return None

    _prepare_dll_path()
    try:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    except Exception as exc:
        _engine = None
        _engine_error = (
            f"OCR 引擎加载失败：{exc}。请安装 rapidocr-onnxruntime；"
            "Windows 若提示 MSVCP140_1.dll 缺失，运行 "
            "python scripts/setup_ocr_dlls.py，或安装 Microsoft VC++ 运行库。"
        )
    return _engine


async def recognize(image_bytes: bytes, filename: str = "") -> OcrResult:
    if (settings.ocr_engine or "").lower() == "disabled":
        return OcrResult(
            configured=False,
            engine="disabled",
            note="OCR 已在配置中关闭（OCR_ENGINE=disabled）。",
        )

    engine = await asyncio.to_thread(_load_engine)
    if engine is None:
        return OcrResult(configured=False, engine="unavailable", note=_engine_error)

    try:
        import numpy as np
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        result, _ = await asyncio.to_thread(engine, np.array(image))
    except Exception as exc:
        return OcrResult(
            configured=False,
            engine="rapidocr",
            note=f"OCR 识别失败：{exc}",
        )

    lines: list[str] = []
    blocks: list[dict] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        lines.append(text)
        try:
            points = item[0]
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            blocks.append(
                {"text": text, "bbox": [min(xs), min(ys), max(xs), max(ys)]}
            )
        except (TypeError, ValueError, IndexError):
            continue

    text = "\n".join(lines)
    entities = [
        {"type": "company", "name": name} for name in extract_company_names(text)
    ]
    return OcrResult(
        configured=True,
        text=text,
        entities=entities,
        engine="rapidocr",
        note="" if text else "未识别到文字，请换一张更清晰的截图或手动粘贴。",
        blocks=blocks,
    )
