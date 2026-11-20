"""Agent 内核：固定 5 步编排（V3 5.4 / 全栈方案 3.3）。

Agent 不是独立服务，就是本文件的一段编排逻辑：
  1. extract_jd（唯一一次 LLM 抽取）
  2. 并行 scan_phrases / classify_jd / query_evidence
  3. score_company + consistency_check
  4. 融合 + 解释（当前框架使用规则模板解释，LLM 只做证据约束改写）
  5. build_report（模板渲染）

降级链：LLM 不可用 → regex 抽取 + 模板解释；
证据源不可用 → 权重归一化 + 报告标注缺失；
两者全挂 → 报告仍然生成，只是置信度降低。
"""

from __future__ import annotations

import asyncio
import inspect
import uuid
from datetime import datetime
from typing import Awaitable, Callable

from . import db
from .providers.base import EvidenceResult
from .schemas import AnalyzeReport
from .tools.build_report import build_report
from .tools.classify_jd import classify_jd
from .tools.consistency_check import consistency_check
from .tools.extract_jd import extract_jd
from .tools.query_evidence import query_evidence
from .tools.scan_phrases import scan_phrases
from .tools.score_company import score_company

ProgressCallback = Callable[[str, str], Awaitable[None] | None]


async def _emit(progress: ProgressCallback | None, stage: str, message: str) -> None:
    if progress is None:
        return
    result = progress(stage, message)
    if inspect.isawaitable(result):
        await result


def _new_report_id() -> str:
    return f"rpt_{datetime.now():%Y%m%d}_{uuid.uuid4().hex[:8]}"


async def _no_evidence() -> list[EvidenceResult]:
    return []


async def analyze(
    jd_text: str,
    company_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> AnalyzeReport:
    # 步骤 1：抽取
    await _emit(progress, "extract", "正在抽取 JD 关键信息…")
    jd = await extract_jd(jd_text)
    if company_name and company_name.strip():
        jd.company = company_name.strip()

    need_clarify = not jd.company
    clarify_question = (
        "未识别到公司名称。可补充公司名称以进行主体核验；不填则仅输出岗位侧风险结果。"
        if need_clarify
        else None
    )

    # 步骤 2：并行跑三条无依赖路径
    await _emit(progress, "scan", "正在并行执行话术扫描、模型判定与证据查询…")
    scan_result, classify_result, evidence = await asyncio.gather(
        asyncio.to_thread(scan_phrases, jd_text),
        asyncio.to_thread(classify_jd, jd_text),
        query_evidence(jd.company) if jd.company else _no_evidence(),
    )

    # 步骤 3：评分 + 一致性校验
    await _emit(progress, "check", "正在进行公司可信度评分与一致性校验…")
    company_score = score_company(evidence)
    consistency = consistency_check(jd, evidence)

    # 步骤 4 + 5：融合 + 模板渲染
    await _emit(progress, "report", "正在生成决策报告…")
    report = build_report(
        report_id=_new_report_id(),
        jd=jd,
        jd_risk=scan_result,
        classify=classify_result,
        company_score=company_score,
        consistency=consistency,
        evidence=evidence,
        need_clarify=need_clarify,
        clarify_question=clarify_question,
    )
    db.save_report(report.report_id, report.model_dump(mode="json"))
    await _emit(progress, "done", "分析完成")
    return report
