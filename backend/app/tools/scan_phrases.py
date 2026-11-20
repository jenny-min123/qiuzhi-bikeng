"""scan_phrases：风险话术规则扫描（不使用 LLM）。

数据源：app/data/phrases.json，词条摘自五部门联合风险提示原文。
输出：命中话术 + 字符级 span + 类别 + 扣分 + 模板解释。
前端据 span 做原文高亮（V3 5.3 / 全栈方案 8.1：必须是字符偏移）。
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from ..config import settings

# V3 6.6 边界裁决规则：培训话术只有与收费 / 贷款 / 包就业 / 录用结果绑定时才判风险；
# 免费、入职后、本公司内部实施、不与录用结果挂钩时放行。
_TRAINING_BENIGN_CUES = (
    "免费",
    "不收取任何费用",
    "不收费",
    "不与录用结果挂钩",
    "不带强制",
    "本公司内部",
    "内部实施",
    "正常发放工资",
    "带薪",
    "入职后",
    "公司提供",
)
_TRAINING_FEE_CUES = (
    "费用",
    "收费",
    "分期",
    "贷款",
    "押金",
    "保证金",
    "材料费",
    "实训费",
    "培训费",
    "先学后付",
    "包就业",
    "包上岗",
    "包分配",
    "入职前",
    "上岗前",
    "录用前",
)
_SENTENCE_END = re.compile(r"[。！？!?；;\n]")
_SALARY_RANGE = re.compile(
    r"(\d{1,3}(?:\.\d+)?)\s*[-~—至]\s*(\d{1,3}(?:\.\d+)?)\s*[kK]"
)
_SALARY_FLOOR_K = 8.0


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


def _sentence_at(text: str, index: int) -> str:
    """取命中位置所在的句子，供边界规则判断上下文。"""
    left = 0
    for match in _SENTENCE_END.finditer(text, 0, index):
        left = match.end()
    match = _SENTENCE_END.search(text, index)
    right = match.start() if match else len(text)
    return text[left:right]


def _benign_training_context(text: str, index: int) -> bool:
    """培训类话术是否属于正规场景（免费 / 入职后 / 本公司实施 / 不挂钩录用）。"""
    sentence = _sentence_at(text, index)
    has_benign = any(cue in sentence for cue in _TRAINING_BENIGN_CUES)

    # 先剔除「不收取任何费用」「免费」等否定表达，避免把其中的「费用」当成收费线索
    sanitized = sentence
    for phrase in ("不收取任何费用", "不收费", "免费", "不带强制"):
        sanitized = sanitized.replace(phrase, "")

    has_fee = any(cue in sanitized for cue in _TRAINING_FEE_CUES)
    return has_benign and not has_fee


def scan_phrases(text: str) -> dict:
    """返回 {score, level, hits[]}。纯确定性，可离线运行。"""
    if not text or not text.strip():
        return {"score": 0, "level": "low", "hits": []}

    lowered = text.lower()
    candidates: list[dict] = []

    for category in _categories():
        cat_type = category.get("type", "未分类")
        penalty = float(category.get("weight", 0))
        for word in category.get("words", []):
            if not word:
                continue
            needle = word.lower()
            start = lowered.find(needle)
            while start != -1:
                end = start + len(word)
                if (
                    cat_type == "能力打压类"
                    and ("培训" in word or "实训" in word)
                    and _benign_training_context(text, start)
                ):
                    # 正规培训场景：放行，不产生命中
                    start = lowered.find(needle, start + 1)
                    continue
                candidates.append(
                    {
                        "type": cat_type,
                        "span": (start, end),
                        "fragment": text[start:end],
                        "penalty": penalty,
                    }
                )
                start = lowered.find(needle, start + 1)

    # 组合信号（V3 4.3 ⑥）：零门槛话术 + 8K 以上薪资区间 = 高薪诱饵。
    # 单独一个薪资区间不判风险，避免把正常 JD 的薪资范围误伤。
    if any(c["type"] == "零门槛类" for c in candidates):
        for match in _SALARY_RANGE.finditer(text):
            if float(match.group(1)) < _SALARY_FLOOR_K:
                continue
            fragment = match.group(0)
            paragraph = text.count("\n", 0, match.start()) + 1
            candidates.append(
                {
                    "type": "高薪异常类",
                    "span": match.span(),
                    "fragment": fragment,
                    "penalty": 10.0,
                    "explanation": (
                        f"「{fragment}」出现在原文第 {paragraph} 段，同时 JD 存在"
                        f"零门槛话术且薪资下限达到 {_SALARY_FLOOR_K:g}K，"
                        f"属于「零经验 + 高薪」组合信号，扣 10 分。"
                    ),
                }
            )

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
                "explanation": cand.get("explanation")
                or _explain(cand["fragment"], cand["type"], cand["penalty"], paragraph),
            }
        )

    total_penalty = sum(h["penalty"] for h in hits)
    score = max(0, min(100, int(round(total_penalty))))
    return {"score": score, "level": _level(score), "hits": hits}
