"""公司主体名识别与同一性判断（V3 4.6 / 7.3）。

F-06 的技术支柱：判断「签约方是否等于招聘方」是同一性判断，
不需要任何工商数据，只需主体名归一化 + 别名匹配 + 用户确认。
"""

from __future__ import annotations

import re

COMPANY_PATTERN = re.compile(
    r"([一-龥A-Za-z0-9（）()·]{2,32}?"
    r"(?:有限责任公司|股份有限公司|有限公司|集团公司|集团|工作室|研究院|事务所)"
    r"(?:[一-龥]{0,8}(?:分公司|分店|办事处|营业部|门店))?)"
)
_PUNCT = re.compile(r"[\s（）()·,，。;；:：\-—_]")
_BRANCH_WORDS = ("分公司", "分店", "办事处", "营业部", "门店")
_LEADING_PREFIXES = (
    "招聘",
    "诚聘",
    "急聘",
    "公司名称",
    "企业名称",
    "甲方",
    "乙方",
    "收款方",
    "培训方",
    "签约方",
    "公司",
    "企业",
    "位于",
    "为",
    "是",
)


def normalize_company(name: str) -> str:
    return _PUNCT.sub("", name or "")


def same_subject(left: str, right: str) -> bool:
    """只接受全称一致或明确的分支机构后缀，避免「守望星辰」误配「星辰」。"""
    left_n = normalize_company(left)
    right_n = normalize_company(right)
    if not left_n or not right_n:
        return False
    if left_n == right_n:
        return True

    for short, long in ((left_n, right_n), (right_n, left_n)):
        if long.startswith(short):
            extra = long[len(short) :]
            if len(extra) <= 8 and any(word in extra for word in _BRANCH_WORDS):
                return True
    return False


def _strip_prefixes(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for prefix in _LEADING_PREFIXES:
            if name.startswith(prefix) and len(name) - len(prefix) >= 6:
                name = name[len(prefix) :]
                changed = True
    return name


def extract_company_names(text: str) -> list[str]:
    """按出现顺序提取公司全称，去重后返回。"""
    seen: set[str] = set()
    names: list[str] = []
    for match in COMPANY_PATTERN.finditer(text or ""):
        name = _strip_prefixes(match.group(1))
        key = normalize_company(name)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names
