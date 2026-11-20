"""校验人工核验快照（company_snapshots.json）。

检查：
- 必填字段、日期格式、参保人数类型
- 是否带 source_url 与 fetched_at（缺失会被分析流程按未核验处理）
- 该条快照能解锁哪些一致性校验规则

运行：cd backend && python scripts/validate_snapshots.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT = BASE_DIR / "data" / "company_snapshots.json"

REQUIRED = (
    "founded_at",
    "registered_address",
    "insured_count",
    "business_scope",
    "registration_status",
    "source_url",
    "fetched_at",
)
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y年%m月")


def parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def unlocked_rules(facts: dict) -> list[str]:
    unlocked = []
    if facts.get("insured_count") is not None or facts.get("employee_count") is not None:
        unlocked.append("规模")
    if facts.get("registered_address"):
        unlocked.append("地址")
    if facts.get("founded_at"):
        unlocked.append("时间")
    if facts.get("business_scope"):
        unlocked.append("行业")
    if facts.get("official_domain"):
        unlocked.append("联系")
    return unlocked


def main() -> int:
    if not SNAPSHOT.exists():
        print(f"未找到快照文件：{SNAPSHOT}")
        return 1

    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"JSON 解析失败：{exc}")
        return 1

    companies = data.get("companies") or {}
    if not companies:
        print("快照为空。请按 docs/manual_snapshot.md 填写真实公司信息后再运行分析。")
        return 0

    errors = 0
    for name, facts in companies.items():
        print(f"\n== {name}")
        if not isinstance(facts, dict):
            print("  [错误] 记录必须是对象")
            errors += 1
            continue

        missing = [field for field in REQUIRED if facts.get(field) in (None, "")]
        if missing:
            print(f"  [警告] 缺少必填字段：{'、'.join(missing)}，该记录会被按未核验处理")
            errors += 1 if any(f in missing for f in ("source_url", "fetched_at")) else 0

        for field in ("founded_at", "fetched_at"):
            if facts.get(field) and parse_date(facts[field]) is None:
                print(f"  [错误] {field} 不是可识别日期：{facts[field]}")
                errors += 1

        insured = facts.get("insured_count")
        if insured is not None and (isinstance(insured, bool) or not isinstance(insured, int)):
            print(f"  [错误] insured_count 必须是整数：{insured!r}")
            errors += 1

        source_url = str(facts.get("source_url") or "")
        if source_url and not source_url.startswith(("http://", "https://")):
            print(f"  [错误] source_url 必须以 http(s):// 开头：{source_url}")
            errors += 1

        print(f"  可解锁一致性规则：{'、'.join(unlocked_rules(facts)) or '无'}")

    print(f"\n检查完成：{len(companies)} 条记录，错误 {errors} 个。")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
