"""F-06 主体分离检测（文本入口）。

投递那一刻，面试方 / 签约方 / 放款方不在任何可查数据里（V3 4.6），
因此不能靠查工商，而是比较「招聘方」与「协议/邀约/收款页面上的签约方」
是否为同一主体。这是同一性判断，不依赖外部数据。
"""

from __future__ import annotations

from .company_names import extract_company_names, same_subject


def subject_check(text: str, recruiter_company: str | None = None) -> dict:
    recruiter = (recruiter_company or "").strip() or None
    names = extract_company_names(text)
    matches = [
        same_subject(recruiter, name) if recruiter else None for name in names
    ]

    entities = [
        {"name": name, "matches_recruiter": match}
        for name, match in zip(names, matches)
    ]

    severity = "unknown"
    alert = ""
    advice: list[str] = []
    matched: bool | None = None

    if not recruiter:
        if len(names) >= 3:
            severity = "high"
            alert = f"文本中出现 {len(names)} 个不同公司主体，且尚未填写招聘方名称。"
        elif len(names) == 2:
            severity = "medium"
            alert = "文本中出现两个不同公司主体，请补充招聘方名称后再核对。"
        elif len(names) == 1:
            alert = "已识别到一个公司主体，请补充招聘方名称以判断是否一致。"
        else:
            alert = "未能识别到公司全称，请人工查看协议上的甲方与收款方。"
        advice = ["补充招聘方公司全称后重新核对。", "直接查看合同甲方、收款方、放款方。"]
        return _result(recruiter, entities, matched, severity, alert, advice)

    if not names:
        alert = "未能从文本中识别到公司全称，请人工核对合同甲方与收款方。"
        advice = [
            "直接查看协议 / 邀约上的公司全称，不要只看简称。",
            "核对收款账户名称与放款机构名称。",
        ]
        return _result(recruiter, entities, matched, severity, alert, advice)

    matched = any(matches)
    if matched:
        if len(names) == 1:
            severity = "low"
            alert = "文本中的主体与招聘方一致。"
        elif len(names) == 2:
            severity = "medium"
            alert = "文本中出现两个不同主体，请确认与你签约的是招聘方还是另一家公司。"
        else:
            severity = "high"
            alert = f"文本中出现 {len(names)} 个不同主体，风险较高，建议逐一核对。"
        advice = ["核对合同甲方、收款方、放款方是否为同一主体。"]
        if severity != "low":
            advice.append("要求对方书面说明各主体之间的关系。")
    else:
        severity = "critical"
        alert = "招聘方与签约方不是同一主体，这是招转培的典型特征。"
        advice = [
            "不要签字。",
            "不要下载任何对方指定的 App。",
            "不要转账或办理分期。",
            "保存协议、聊天记录与收款方信息，必要时向平台或 12333 反映。",
        ]

    return _result(recruiter, entities, matched, severity, alert, advice)


def _result(
    recruiter: str | None,
    entities: list[dict],
    matched: bool | None,
    severity: str,
    alert: str,
    advice: list[str],
) -> dict:
    return {
        "recruiter_company": recruiter,
        "entities": entities,
        "matched": matched,
        "severity": severity,
        "alert": alert,
        "advice": advice,
    }
