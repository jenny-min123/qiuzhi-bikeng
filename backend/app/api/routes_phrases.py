"""风险话术词库接口（F-08）。

返回 phrases.json 的分类体系，并在 168 条标注集上统计各类别的命中频次。
频次来自真实标注数据（dataset_full.csv），不是模拟数字。
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from functools import lru_cache

from fastapi import APIRouter

from ..config import settings
from ..tools.scan_phrases import scan_phrases

router = APIRouter(tags=["phrases"])


@lru_cache(maxsize=1)
def _catalog() -> dict:
    with settings.phrases_path.open(encoding="utf-8") as f:
        data = json.load(f)

    rows: list[dict] = []
    if settings.dataset_path.exists():
        with settings.dataset_path.open(encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("jd_text") or "").strip()]

    counts: Counter[str] = Counter()
    for row in rows:
        for hit in scan_phrases(row["jd_text"])["hits"]:
            counts[hit["type"]] += 1

    categories = []
    total_words = 0
    for category in data.get("categories", []):
        words = category.get("words", [])
        total_words += len(words)
        categories.append(
            {
                "type": category.get("type", "未分类"),
                "official_basis": category.get("official_basis", ""),
                "weight": category.get("weight", 0),
                "words": words,
                "word_count": len(words),
                "corpus_hits": counts.get(category.get("type"), 0),
            }
        )

    return {
        "meta": data.get("_meta", {}),
        "categories": categories,
        "total_words": total_words,
        "corpus": {
            "size": len(rows),
            "positive": sum(1 for r in rows if r.get("label") == "1"),
            "negative": sum(1 for r in rows if r.get("label") == "0"),
            "source": "backend/data/dataset_full.csv",
        },
    }


@router.get("/phrases")
def phrases_endpoint() -> dict:
    return _catalog()
