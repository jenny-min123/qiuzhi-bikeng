# 接口文档

> 对齐《大专生求职避坑平台_全栈开发方案》第四章「关键契约」。
> 启动后也可访问 FastAPI 自动文档：<http://127.0.0.1:8000/docs>

## 通用

- Base URL：`http://127.0.0.1:8000`
- 前端开发代理：`/api/*` → `http://127.0.0.1:8000/*`
- 所有评分均由后端确定性代码产出，前端不参与评分。
- 证据源缺失时不会编造数据，而是在 `missing_sources` / `rules_not_evaluable` 中明示。

## POST /analyze

同步返回完整决策报告。

请求：

```json
{
  "jd_text": "AI剪辑实训生，零基础可投……",
  "company_name": "深圳市某某网络科技有限公司",
  "images": []
}
```

响应（核心字段）：

```json
{
  "report_id": "rpt_20261120_ab12cd34",
  "jd": {
    "text": "……",
    "company": "深圳市某某网络科技有限公司",
    "position": "AI剪辑实训生",
    "salary": "8-15K",
    "education": null,
    "claimed_headcount": null,
    "visit_address": null,
    "extracted_by": "regex_fallback"
  },
  "jd_risk": {
    "score": 54,
    "level": "medium",
    "hits": [
      {
        "evidence_id": "ph_001",
        "type": "零门槛类",
        "span": [8, 13],
        "fragment": "零基础可投",
        "penalty": 8,
        "explanation": "「零基础可投」出现在原文第 1 段，……"
      }
    ],
    "classify_prob": null,
    "classify_available": false,
    "classify_note": "未找到训练模型……"
  },
  "company_score": {
    "score": null,
    "level": "unknown",
    "confidence": "低",
    "available": false,
    "missing_sources": ["地图POI", "ICP备案", "域名年龄", "平台企业认证", "社交口碑", "工商信息"],
    "deductions": []
  },
  "consistency": {
    "mismatches": [],
    "critical": [],
    "rules_evaluated": [],
    "rules_not_evaluable": ["规模", "地址", "行业", "主体", "时间", "薪资", "业务", "联系", "资质"]
  },
  "verdict": {
    "final_suggestion": "谨慎投递",
    "one_vote_veto": false,
    "veto_reason": null
  },
  "evidence_chain": [],
  "disclaimer": "本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。",
  "need_clarify": false,
  "clarify_question": null
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `jd_risk.score` | 规则引擎扣分求和（上限 100），当前基线实现 |
| `jd_risk.hits[].span` | **字符级**起止下标，前端据此高亮 |
| `jd_risk.classify_prob` | TF-IDF+LR 模型概率；模型未训练时为 `null` |
| `company_score.score` | 动态权重归一化后的可信分；无证据时为 `null` |
| `company_score.missing_sources` | 本次未获取的证据源 |
| `consistency.critical` | 一票否决项（如签约方 ≠ 招聘方） |
| `verdict.final_suggestion` | `建议投递` / `谨慎投递` / `建议放弃` |

## POST /analyze/stream

请求体同上，返回 `text/event-stream`：

```
event: progress
data: {"stage":"extract","message":"正在抽取 JD 关键信息…"}

event: progress
data: {"stage":"scan","message":"正在并行执行话术扫描、模型判定与证据查询…"}

event: report
data: { ...完整 AnalyzeReport... }
```

失败时推送 `event: error`。前端在 SSE 不可用时回退到 `POST /analyze`。

## POST /batch

请求：

```json
{ "jd_list": ["JD 一", "JD 二", "JD 三"] }
```

响应：

```json
{
  "items": [
    { "jd_index": 0, "score": 62, "level": "medium", "suggestion": "谨慎投递" }
  ],
  "risk_distribution": { "high": 1, "medium": 2, "low": 0 },
  "risk_categories": { "零门槛类": 2, "培训诱导类": 1 }
}
```

批量模式只做岗位侧规则扫描，不做主体核验。

## POST /ocr

`multipart/form-data`，字段 `file`。图片上限 10MB。

成功：

```json
{ "text": "……", "entities": [{ "type": "signing_party", "name": "XX教育科技有限公司" }] }
```

OCR 引擎未接入时返回 `503`，`detail` 说明原因；不返回空文本冒充识别成功。

## POST /export

请求：

```json
{ "report_id": "rpt_20261120_ab12cd34", "format": "pdf" }
```

当前报告已可通过 `GET /reports/{report_id}` 取回；PDF / 长图渲染器尚未接入，导出接口返回 `501` 并说明原因（开发序位第 8 周）。

## GET /reports/{report_id}

返回已保存的报告 JSON；不存在时 `404`。

## GET /health

```json
{
  "status": "ok",
  "version": "0.1.0",
  "llm_configured": false,
  "ocr_engine": "disabled",
  "amap_configured": false
}
```
