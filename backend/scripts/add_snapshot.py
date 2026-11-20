"""录入一条企业工商信息人工核验快照。

示例（PowerShell 用反引号换行）：
  python scripts/add_snapshot.py `
    --company "某某网络科技有限公司" `
    --founded-at 2024-07-01 `
    --address "某市某区某路 1 号" `
    --insured-count 3 `
    --scope "教育咨询服务；企业管理咨询" `
    --status 存续 `
    --source-url "https://www.gsxt.gov.cn/" `
    --fetched-at 2026-11-20

可选：
  --credit-code, --employee-count, --official-domain, --note
  --dry-run   只校验与预览，不写入
  --list      列出现有快照
  --remove "公司全称"
  --force     允许新增与现有主体名称相近的记录
  --file PATH 操作其他快照文件（默认 backend/data/company_snapshots.json）

只录入公开信息，必须带来源与查询日期；不采集身份证号、手机号等个人信息。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from snapshot_utils import (
    BASE_DIR,
    SNAPSHOT,
    load_snapshot_file,
    parse_date,
    save_snapshot_file,
    unlocked_rules,
    validate_record,
)

sys.path.insert(0, str(BASE_DIR))

from app.tools.company_names import same_subject  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="录入 / 查看 / 删除企业工商信息人工核验快照",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--company", help="公司工商全称")
    parser.add_argument("--founded-at", help="成立日期 YYYY-MM-DD")
    parser.add_argument("--address", dest="registered_address", help="注册地址")
    parser.add_argument("--insured-count", type=int, help="参保人数")
    parser.add_argument("--scope", dest="business_scope", help="经营范围原文")
    parser.add_argument("--status", dest="registration_status", help="登记状态，如 存续")
    parser.add_argument("--source-url", help="查询页面 URL")
    parser.add_argument("--fetched-at", help="人工查询日期 YYYY-MM-DD")
    parser.add_argument("--credit-code", help="统一社会信用代码（可选）")
    parser.add_argument("--employee-count", type=int, help="员工人数（可选）")
    parser.add_argument("--official-domain", help="官网域名（可选）")
    parser.add_argument("--note", help="备注（可选）")
    parser.add_argument("--file", type=Path, default=SNAPSHOT, help="快照文件路径")
    parser.add_argument("--list", action="store_true", help="列出现有快照")
    parser.add_argument("--remove", metavar="COMPANY", help="删除指定公司快照")
    parser.add_argument("--dry-run", action="store_true", help="只校验和预览，不写入")
    parser.add_argument("--force", action="store_true", help="允许新增名称相近的主体")
    return parser


def list_snapshots(path: Path) -> int:
    try:
        data = load_snapshot_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取失败：{exc}")
        return 1
    companies = data.get("companies") or {}
    if not companies:
        print("快照为空。")
        return 0
    for name, record in companies.items():
        print(
            f"{name}\n"
            f"  状态：{record.get('registration_status', '—')}  "
            f"查询日期：{record.get('fetched_at', '—')}\n"
            f"  来源：{record.get('source_url', '—')}"
        )
    return 0


def remove_snapshot(path: Path, company: str, dry_run: bool) -> int:
    try:
        data = load_snapshot_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取失败：{exc}")
        return 1
    companies = data.get("companies") or {}
    if company not in companies:
        similar = [name for name in companies if same_subject(company, name)]
        if similar:
            print("未找到完全同名记录，相近主体：")
            for name in similar:
                print(f"  - {name}")
        else:
            print(f"未找到：{company}")
        return 2

    if not dry_run:
        del companies[company]
        save_snapshot_file(data, path)
    print(f"{'预览删除' if dry_run else '已删除'}：{company}")
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if args.list:
        return list_snapshots(args.file)
    if args.remove:
        return remove_snapshot(args.file, args.remove, args.dry_run)

    missing = [
        flag
        for flag, value in (
            ("--company", args.company),
            ("--founded-at", args.founded_at),
            ("--address", args.registered_address),
            ("--insured-count", args.insured_count),
            ("--scope", args.business_scope),
            ("--status", args.registration_status),
            ("--source-url", args.source_url),
            ("--fetched-at", args.fetched_at),
        )
        if value in (None, "")
    ]
    if missing:
        print(f"缺少参数：{', '.join(missing)}")
        print("运行 python scripts/add_snapshot.py --help 查看示例。")
        return 2

    company = args.company.strip()
    founded = parse_date(args.founded_at)
    fetched = parse_date(args.fetched_at)
    record = {
        "founded_at": founded.isoformat() if founded else args.founded_at.strip(),
        "registered_address": args.registered_address.strip(),
        "insured_count": args.insured_count,
        "business_scope": args.business_scope.strip(),
        "registration_status": args.registration_status.strip(),
        "source_url": args.source_url.strip(),
        "fetched_at": fetched.isoformat() if fetched else args.fetched_at.strip(),
    }
    for key, value in (
        ("credit_code", args.credit_code),
        ("employee_count", args.employee_count),
        ("official_domain", args.official_domain),
        ("note", args.note),
    ):
        if value not in (None, ""):
            record[key] = value.strip() if isinstance(value, str) else value

    errors = validate_record(record)
    if errors:
        print("校验失败：")
        for message in errors:
            print(f"  - {message}")
        return 2

    try:
        data = load_snapshot_file(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取快照失败：{exc}")
        return 1
    companies = data.setdefault("companies", {})

    if company in companies:
        action = "更新"
    else:
        similar = [name for name in companies if same_subject(company, name)]
        if similar and not args.force:
            print("发现名称相近的主体：")
            for name in similar:
                print(f"  - {name}")
            print("如果确认是不同主体，加 --force 新增；否则请使用已有的公司全称。")
            return 2
        action = "新增"

    if args.dry_run:
        print(f"校验通过（预览，不写入）。将要{action}：")
        print(json.dumps({company: record}, ensure_ascii=False, indent=2))
        print(f"可解锁一致性规则：{'、'.join(unlocked_rules(record)) or '无'}")
        return 0

    companies[company] = record
    save_snapshot_file(data, args.file)

    print(f"{action}成功：{company}")
    print(f"快照文件：{args.file}")
    print(f"可解锁一致性规则：{'、'.join(unlocked_rules(record)) or '无'}")
    print("下一步：")
    print("  python scripts/validate_snapshots.py")
    print("  然后在前端填写公司名称重新分析。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
