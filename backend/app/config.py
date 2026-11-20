"""全局配置。

原则（V3 第 3.1 / 5.9 节）：所有外部依赖都通过环境变量注入；
拿不到 key 或服务不可用时，系统走降级链，而不是伪造结果。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
DATA_DIR = APP_DIR / "data"

# .env 可选：没装 python-dotenv 也不影响运行
try:  # pragma: no cover - 取决于本地环境
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


@dataclass(frozen=True)
class Settings:
    app_name: str = "大专生求职避坑平台 API"
    version: str = "0.1.0"

    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    db_path: Path = BACKEND_DIR / "cache.sqlite3"
    phrases_path: Path = DATA_DIR / "phrases.json"
    alias_path: Path = DATA_DIR / "company_alias.json"
    dataset_path: Path = BACKEND_DIR / "data" / "dataset_full.csv"
    model_path: Path = DATA_DIR / "model.pkl"
    vectorizer_path: Path = DATA_DIR / "vectorizer.pkl"

    # 证据 / 工商查询结果缓存 24 小时（全栈方案 6.3）
    cache_ttl_seconds: int = 24 * 3600
    failed_cache_ttl_seconds: int = 5 * 60

    # LLM 只用于 extract_jd / 解释填槽（V3 5.3）
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")

    # 可插拔证据源
    amap_api_key: str = os.getenv("AMAP_API_KEY", "")

    # OCR 入口（F-09）。未接入时 /ocr 明确返回 503，不返回假文本。
    ocr_engine: str = os.getenv("OCR_ENGINE", "disabled")


settings = Settings()
