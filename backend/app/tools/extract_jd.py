"""extract_jd：JD 结构化抽取（8 个工具中唯一使用 LLM 的一个）。

V3 5.3：LLM 只负责理解，不判风险；返回字段必须受 JSON schema 约束。
未配置 LLM 或调用失败时，退回确定性正则抽取，并在 extracted_by 中如实标注。
"""

from __future__ import annotations

import re

from .. import llm
from ..schemas import JDInfo

_SYSTEM_PROMPT = """你是招聘 JD 信息抽取器。只做信息抽取，不做风险判断。
输出一个 JSON 对象，字段如下（没有把握的字段一律填 null，禁止猜测）：
{
  "company": "招聘方公司全称，没有则 null",
  "position": "岗位名称",
  "salary": "薪资原文，如 8-15K",
  "education": "学历要求原文",
  "claimed_headcount": "JD 宣称的公司规模，如 500人以上",
  "visit_address": "面试 / 到访 / 工作地址，没有则 null"
}
要求：只输出 JSON，不要解释，不要 markdown 代码块。"""

_PREFIXES = ("招聘", "诚聘", "急聘", "公司名称", "企业名称", "公司", "企业", "位于")
_POSITION_PATTERN = re.compile(r"(?:岗位|职位|招聘|诚聘)[：:\s]*([^\n，,。；;|]{2,25})")
_COMPANY_PATTERN = re.compile(
    r"([一-龥A-Za-z0-9（）()·]{2,32}?"
    r"(?:有限责任公司|股份有限公司|有限公司|集团公司|集团|工作室|研究院|事务所))"
)
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().strip("：:，,。；;\"'")
    return value or None


def _extract_company(text: str) -> str | None:
    matches = _COMPANY_PATTERN.findall(text)
    if not matches:
        return None
    name = max(matches, key=len)
    changed = True
    while changed:
        changed = False
        for prefix in _PREFIXES:
            if name.startswith(prefix) and len(name) - len(prefix) >= 6:
                name = name[len(prefix) :]
                changed = True
    return name or None


def _extract_position(text: str) -> str | None:
    match = _POSITION_PATTERN.search(text)
    if match:
        return _clean(match.group(1))
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return _clean(first_line[:25]) or None


def _extract_salary(text: str) -> str | None:
    match = re.search(
        r"(?:月薪|薪资|工资|待遇|薪酬|综合薪资)[：:\s]*"
        r"([0-9][0-9kK千万元./\-~—至 ]{1,25})",
        text,
    )
    if match:
        return _clean(match.group(1))
    match = re.search(
        r"(\d{1,3}(?:\.\d+)?\s*[kK千]?\s*[-~—至]\s*"
        r"\d{1,3}(?:\.\d+)?\s*[kK千万])",
        text,
    )
    return _clean(match.group(1)) if match else None


def _extract_education(text: str) -> str | None:
    match = re.search(r"(大专|专科|本科|硕士|博士|高中|中专|不限学历)", text)
    return match.group(1) if match else None


def _extract_headcount(text: str) -> str | None:
    match = re.search(
        r"(?:规模|团队|员工|人数|公司)[^\d\n]{0,8}(\d+\s*(?:人以上|余人|多人|人))", text
    )
    if match:
        return _clean(match.group(1))
    match = re.search(r"(\d+\s*(?:人以上|余人|多人))", text)
    return _clean(match.group(1)) if match else None


def _extract_address(text: str) -> str | None:
    match = re.search(
        r"(?:面试地址|到访地址|工作地址|上班地址|公司地址|地址)[：:\s]*"
        r"([^\n。；;]{2,50})",
        text,
    )
    return _clean(match.group(1)) if match else None


def _regex_extract(text: str) -> JDInfo:
    return JDInfo(
        text=text,
        company=_extract_company(text),
        position=_extract_position(text),
        salary=_extract_salary(text),
        education=_extract_education(text),
        claimed_headcount=_extract_headcount(text),
        visit_address=_extract_address(text),
        extracted_by="regex_fallback",
    )


async def extract_jd(text: str) -> JDInfo:
    if llm.enabled():
        for _ in range(2):  # 解析失败重试一次（全栈方案 8.2）
            data = await llm.chat_json(_SYSTEM_PROMPT, text[:12000])
            if not data:
                continue
            try:
                return JDInfo(
                    text=text,
                    company=_clean(data.get("company")),
                    position=_clean(data.get("position")),
                    salary=_clean(data.get("salary")),
                    education=_clean(data.get("education")),
                    claimed_headcount=_clean(data.get("claimed_headcount")),
                    visit_address=_clean(data.get("visit_address")),
                    extracted_by="llm",
                )
            except Exception:
                continue
    return _regex_extract(text)
