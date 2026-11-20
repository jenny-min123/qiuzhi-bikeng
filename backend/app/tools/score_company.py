"""score_company：多源证据加权评分 + 缺失信号下的动态权重归一化。

实现 V3 6.5：
    available = [s for s in signals if s.retrieved]
    total_w   = sum(s.weight for s in available)
    score     = 100 - sum(s.penalty for s in available) * (100 / total_w)

没有拿到任何证据时返回 score=None、available=False，不给「看起来完整」的假分数。
可用证据覆盖不足 40% 时返回 score=None、level=unknown，避免单一弱信号
直接得出「低风险」结论；缺失来源仍会完整列出。
"""

from __future__ import annotations

from ..providers.base import EvidenceResult


def _confidence(coverage: float) -> str:
    if coverage >= 0.75:
        return "高"
    if coverage >= 0.4:
        return "中"
    return "低"


def _level(score: int) -> str:
    if score >= 70:
        return "low_risk"
    if score >= 40:
        return "medium_risk"
    return "high_risk"


def score_company(evidence: list[EvidenceResult]) -> dict:
    missing = [e.source for e in evidence if not e.retrieved]
    available = [e for e in evidence if e.retrieved]

    if not available:
        return {
            "score": None,
            "level": "unknown",
            "confidence": "低",
            "available": False,
            "coverage": 0.0,
            "missing_sources": missing,
            "deductions": [],
        }

    total_weight = sum(e.weight for e in available) or 1.0
    registered_weight = sum(e.weight for e in evidence) or total_weight
    penalty = sum(max(e.penalty, 0.0) for e in available)

    raw = 100.0 - penalty * (100.0 / total_weight)
    score = max(0, min(100, round(raw)))
    coverage = total_weight / registered_weight if registered_weight else 0.0

    deductions = []
    for item in available:
        if item.penalty <= 0:
            continue
        fact = str(item.detail.get("summary") or item.note or item.source)
        deductions.append(
            {
                "evidence_id": item.evidence_id,
                "source": item.source,
                "item": item.source,
                "fact": fact,
                "penalty": item.penalty,
                "explanation": f"{item.source}显示：{fact}，扣 {item.penalty:g} 分。",
            }
        )

    # 覆盖不足 40% 时不给出可信度等级：单一弱信号不足以支撑「低风险」结论
    if coverage < 0.4:
        return {
            "score": None,
            "level": "unknown",
            "confidence": "低",
            "available": True,
            "coverage": round(coverage, 2),
            "missing_sources": missing,
            "deductions": deductions,
        }

    return {
        "score": score,
        "level": _level(score),
        "confidence": _confidence(coverage),
        "available": True,
        "coverage": round(coverage, 2),
        "missing_sources": missing,
        "deductions": deductions,
    }
