"""scan_phrases：风险话术规则扫描（不使用 LLM）。

数据源：app/data/phrases.json，词条摘自五部门联合风险提示原文。
输出：命中话术 + 字符级 span + 类别 + 扣分 + 模板解释。
前端据 span 做原文高亮（V3 5.3 / 全栈方案 8.1：必须是字符偏移）。
"""

from __future__ import annotations

import json
from functools import lru_cache

from ..config import settings


@lru_cache(maxsize=1)
def _categories() -> tuple[dict, ...]:
    with settings.phrases_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return tuple(data.get("categories", []))


def _level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _explain(fragment: str, category: str, penalty: float, paragraph: int) -> str:
    return (
        f"「{fragment}」出现在原文第 {paragraph} 段，该类话术在五部门风险提示中"
        f"被列为{category}，扣 {penalty:g} 分。"
    )


def scan_phrases(text: str) -> dict:
    """返回 {score, level, hits[]}。纯确定性，可离线运行。"""
    if not text or not text.strip():
        return {"score": 0, "level": "low", "hits": []}

    lowered = text.lower()
    candidates: list[dict] = []

    for cat_index, category in enumerate(_categories(), start=1):
        cat_type = category.get("type", "未分类")
        penalty = float(category.get("weight", 0))
        for word in category.get("words", []):
            if not word:
                continue
            needle = word.lower()
            start = lowered.find(needle)
            while start != -1:
                end = start + len(word)
                candidates.append(
                    {
                        "type": cat_type,
                        "category_index": cat_index,
                        "span": (start, end),
                        "fragment": text[start:end],
                        "penalty": penalty,
                    }
                )
                start = lowered.find(needle, start + 1)

    # 重叠时保留更长的命中；等长保留扣分更高的；再按出现位置排序
    candidates.sort(
        key=lambda c: (-(c["span"][1] - c["span"][0]), -c["penalty"], c["span"][0])
    )
    selected: list[dict] = []
    for cand in candidates:
        start, end = cand["span"]
        if all(end <= s["span"][0] or start >= s["span"][1] for s in selected):
            selected.append(cand)

    selected.sort(key=lambda c: c["span"][0])

    hits: list[dict] = []
    for index, cand in enumerate(selected, start=1):
        start = cand["span"][0]
        paragraph = text.count("\n", 0, start) + 1
        hits.append(
            {
                "evidence_id": f"ph_{index:03d}",
                "type": cand["type"],
                "span": cand["span"],
                "fragment": cand["fragment"],
                "penalty": cand["penalty"],
                "explanation": _explain(
                    cand["fragment"], cand["type"], cand["penalty"], paragraph
                ),
            }
        )

    total_penalty = sum(h["penalty"] for h in hits)
    score = max(0, min(100, int(round(total_penalty))))
    return {"score": score, "level": _level(score), "hits": hits}
