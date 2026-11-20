"""请求 / 响应模型。

字段严格对齐《全栈开发方案》第四章「关键契约」。
额外字段（need_clarify / available / classify_available 等）只用于表达
「信息不足」，不改变原契约语义。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]
CompanyLevel = Literal["low_risk", "medium_risk", "high_risk", "unknown"]
Suggestion = Literal["建议投递", "谨慎投递", "建议放弃"]
Severity = Literal["low", "medium", "high", "critical"]
Confidence = Literal["高", "中", "低"]


# ---------- 输入 ----------


class AnalyzeRequest(BaseModel):
    jd_text: str = Field(min_length=1, max_length=20000)
    company_name: str | None = Field(default=None, max_length=200)
    images: list[str] = Field(default_factory=list)


class BatchRequest(BaseModel):
    jd_list: list[str] = Field(min_length=1, max_length=30)


class ExportRequest(BaseModel):
    report_id: str
    format: Literal["pdf", "png"] = "pdf"


class SubjectCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    recruiter_company: str | None = Field(default=None, max_length=200)


class SubjectEntity(BaseModel):
    name: str
    matches_recruiter: bool | None = None


class SnapshotFields(BaseModel):
    """企查查「工商信息」页字段，按页面顺序排列。"""

    company: str | None = None
    credit_code: str | None = None
    legal_representative: str | None = None
    registration_status: str | None = None
    founded_at: str | None = None
    registered_capital: str | None = None
    paid_in_capital: str | None = None
    organization_code: str | None = None
    business_registration_no: str | None = None
    taxpayer_id: str | None = None
    company_type: str | None = None
    business_term: str | None = None
    taxpayer_qualification: str | None = None
    insured_count: int | None = None
    employee_count: int | None = None
    approval_date: str | None = None
    region: str | None = None
    registration_authority: str | None = None
    industry: str | None = None
    english_name: str | None = None
    registered_address: str | None = None
    mailing_address: str | None = None
    business_scope: str | None = None
    official_domain: str | None = None


class SnapshotExtractResponse(BaseModel):
    text: str
    fields: SnapshotFields
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggested_fetched_at: str


class SnapshotUpsertRequest(BaseModel):
    company: str = Field(min_length=4, max_length=200)
    founded_at: str = Field(min_length=8, max_length=20)
    registered_address: str = Field(min_length=2, max_length=300)
    insured_count: int = Field(ge=0)
    business_scope: str = Field(min_length=1, max_length=2000)
    registration_status: str = Field(min_length=1, max_length=50)
    source_url: str = Field(pattern=r"^https?://", max_length=500)
    fetched_at: str = Field(min_length=8, max_length=20)
    credit_code: str | None = Field(default=None, max_length=50)
    legal_representative: str | None = Field(default=None, max_length=100)
    registered_capital: str | None = Field(default=None, max_length=100)
    paid_in_capital: str | None = Field(default=None, max_length=100)
    organization_code: str | None = Field(default=None, max_length=50)
    business_registration_no: str | None = Field(default=None, max_length=50)
    taxpayer_id: str | None = Field(default=None, max_length=50)
    company_type: str | None = Field(default=None, max_length=100)
    business_term: str | None = Field(default=None, max_length=100)
    taxpayer_qualification: str | None = Field(default=None, max_length=50)
    approval_date: str | None = Field(default=None, max_length=20)
    region: str | None = Field(default=None, max_length=100)
    registration_authority: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    english_name: str | None = Field(default=None, max_length=200)
    mailing_address: str | None = Field(default=None, max_length=300)
    employee_count: int | None = Field(default=None, ge=0)
    official_domain: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class SnapshotUpsertResponse(BaseModel):
    action: Literal["新增", "更新"]
    company: str
    unlocked_rules: list[str] = Field(default_factory=list)
    snapshot_path: str


class SubjectCheckResponse(BaseModel):
    recruiter_company: str | None = None
    entities: list[SubjectEntity] = Field(default_factory=list)
    matched: bool | None = None
    severity: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    alert: str
    advice: list[str] = Field(default_factory=list)


# ---------- JD 抽取 ----------


class JDInfo(BaseModel):
    text: str
    company: str | None = None
    position: str | None = None
    salary: str | None = None
    education: str | None = None
    claimed_headcount: str | None = None
    visit_address: str | None = None
    extracted_by: Literal["llm", "regex_fallback"] = "regex_fallback"


# ---------- 岗位风险 ----------


class PhraseHit(BaseModel):
    evidence_id: str
    type: str
    span: tuple[int, int] = Field(description="字符级偏移，前端据此高亮原文")
    fragment: str
    penalty: float
    explanation: str


class JDRisk(BaseModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    hits: list[PhraseHit] = Field(default_factory=list)
    classify_prob: float | None = None
    classify_available: bool = False
    classify_note: str | None = None


# ---------- 公司可信度 ----------


class CompanyDeduction(BaseModel):
    evidence_id: str
    source: str
    item: str
    fact: str
    penalty: float
    explanation: str


class CompanyScore(BaseModel):
    score: int | None = Field(default=None, ge=0, le=100)
    level: CompanyLevel = "unknown"
    confidence: Confidence = "低"
    available: bool = False
    coverage: float = Field(default=0.0, ge=0, le=1, description="可用证据权重占全部注册证据源的比例")
    missing_sources: list[str] = Field(default_factory=list)
    deductions: list[CompanyDeduction] = Field(default_factory=list)


# ---------- 一致性校验 ----------


class ConsistencyItem(BaseModel):
    evidence_id: str
    category: str
    jd_claim: str | None = None
    jd_span: tuple[int, int] | None = None
    subject_fact: str
    severity: Severity
    penalty: float
    explanation: str


class ConsistencyResult(BaseModel):
    mismatches: list[ConsistencyItem] = Field(default_factory=list)
    critical: list[ConsistencyItem] = Field(default_factory=list)
    rules_evaluated: list[str] = Field(default_factory=list)
    rules_not_evaluable: list[str] = Field(default_factory=list)


# ---------- 证据链与结论 ----------


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    link: str | None = None
    detail: dict | None = None


class Verdict(BaseModel):
    final_suggestion: Suggestion
    one_vote_veto: bool = False
    veto_reason: str | None = None


class AnalyzeReport(BaseModel):
    report_id: str
    jd: JDInfo
    jd_risk: JDRisk
    company_score: CompanyScore
    consistency: ConsistencyResult
    verdict: Verdict
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    disclaimer: str = "本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。"
    need_clarify: bool = False
    clarify_question: str | None = None


# ---------- 批量模式 ----------


class BatchItem(BaseModel):
    jd_index: int
    score: int
    level: RiskLevel
    suggestion: Suggestion


class BatchResponse(BaseModel):
    items: list[BatchItem]
    risk_distribution: dict[str, int]
    risk_categories: dict[str, int]


# ---------- OCR ----------


class OcrEntity(BaseModel):
    type: str
    name: str


class OcrResponse(BaseModel):
    text: str
    entities: list[OcrEntity] = Field(default_factory=list)
