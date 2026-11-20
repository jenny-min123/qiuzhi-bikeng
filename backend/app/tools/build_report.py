"""build_report：模板渲染一页决策报告（不使用 LLM，V3 4.4）。

融合策略（V3 5.5 / 7.3）：
1. 一致性校验存在 critical 项 → 一票否决，建议放弃，不参与加权；
2. 岗位风险或公司可信度任一判高危 → 木桶原则，建议放弃；
3. 任一模块中等风险或有 high/medium 不一致项 → 谨慎投递；
4. 主体证据缺失 → 置信度降级，最多给「谨慎投递」；
5. 全部低风险且有可用主体证据 → 建议投递。
"""

from __future__ import annotations

from ..providers.base import EvidenceResult
from ..schemas import (
    AnalyzeReport,
    CompanyScore,
    ConsistencyResult,
    EvidenceItem,
    JDInfo,
    JDRisk,
    Verdict,
)

DISCLAIMER = "本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。"


def _decide(jd_risk: dict, company_score: dict, consistency: dict) -> Verdict:
    critical = consistency.get("critical") or []
    if critical:
        categories = "、".join(sorted({c["category"] for c in critical}))
        return Verdict(
            final_suggestion="建议放弃",
            one_vote_veto=True,
            veto_reason=f"一致性校验发现一票否决项：{categories}",
        )

    jd_level = jd_risk.get("level")
    company_available = bool(company_score.get("available"))
    company_level = company_score.get("level")
    severities = {m["severity"] for m in consistency.get("mismatches", [])}

    if jd_level == "high" or (company_available and company_level == "high_risk"):
        return Verdict(final_suggestion="建议放弃")

    # 木桶原则：一致性校验出现 high 级矛盾，视为核心模块高危
    if "high" in severities:
        return Verdict(final_suggestion="建议放弃")

    if (
        jd_level == "medium"
        or (company_available and company_level == "medium_risk")
        or "medium" in severities
    ):
        return Verdict(final_suggestion="谨慎投递")

    if not company_available:
        # 只有岗位侧证据，主体未核验：不给「建议投递」
        return Verdict(final_suggestion="谨慎投递")

    return Verdict(final_suggestion="建议投递")


def _evidence_chain(
    jd_risk: dict, evidence: list[EvidenceResult]
) -> list[EvidenceItem]:
    chain: list[EvidenceItem] = []
    seen: set[str] = set()

    for hit in jd_risk.get("hits", []):
        evidence_id = hit.get("evidence_id", "")
        if not evidence_id or evidence_id in seen:
            continue
        seen.add(evidence_id)
        chain.append(
            EvidenceItem(
                evidence_id=evidence_id,
                source="JD 原文",
                detail={
                    "fragment": hit.get("fragment"),
                    "type": hit.get("type"),
                    "span": list(hit.get("span", ())),
                },
            )
        )

    for item in evidence:
        if not item.retrieved or not item.evidence_id or item.evidence_id in seen:
            continue
        seen.add(item.evidence_id)
        chain.append(
            EvidenceItem(
                evidence_id=item.evidence_id,
                source=item.source,
                link=(item.detail or {}).get("link"),
                detail=item.detail or None,
            )
        )

    return chain


def build_report(
    *,
    report_id: str,
    jd: JDInfo,
    jd_risk: dict,
    classify: dict,
    company_score: dict,
    consistency: dict,
    evidence: list[EvidenceResult],
    need_clarify: bool = False,
    clarify_question: str | None = None,
) -> AnalyzeReport:
    jd_risk_model = JDRisk(
        score=jd_risk["score"],
        level=jd_risk["level"],
        hits=jd_risk.get("hits", []),
        classify_prob=classify.get("prob"),
        classify_available=bool(classify.get("available")),
        classify_note=classify.get("note"),
    )

    return AnalyzeReport(
        report_id=report_id,
        jd=jd,
        jd_risk=jd_risk_model,
        company_score=CompanyScore(**company_score),
        consistency=ConsistencyResult(**consistency),
        verdict=_decide(jd_risk, company_score, consistency),
        evidence_chain=_evidence_chain(jd_risk, evidence),
        disclaimer=DISCLAIMER,
        need_clarify=need_clarify,
        clarify_question=clarify_question,
    )
