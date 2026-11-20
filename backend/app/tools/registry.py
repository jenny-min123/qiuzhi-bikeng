"""工具注册表：8 个确定性工具的统一入口（V3 5.3 / 全栈方案 5.2）。

Orchestrator 按固定 5 步调用这些工具，不搞开放 ReAct、不做 multi-agent。
"""

from __future__ import annotations

from .build_report import build_report
from .classify_jd import classify_jd
from .consistency_check import consistency_check
from .extract_jd import extract_jd
from .query_company import query_company
from .query_evidence import query_evidence
from .scan_phrases import scan_phrases
from .score_company import score_company

TOOLS = {
    "extract_jd": extract_jd,
    "scan_phrases": scan_phrases,
    "classify_jd": classify_jd,
    "query_company": query_company,
    "query_evidence": query_evidence,
    "score_company": score_company,
    "consistency_check": consistency_check,
    "build_report": build_report,
}

# 哪些工具会调用 LLM（用于文档与论文说明）
LLM_TOOLS = {"extract_jd"}


def list_tools() -> list[dict]:
    return [
        {
            "name": name,
            "uses_llm": name in LLM_TOOLS,
            "description": (func.__doc__ or "").strip().splitlines()[0],
        }
        for name, func in TOOLS.items()
    ]
