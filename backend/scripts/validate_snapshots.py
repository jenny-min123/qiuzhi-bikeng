"""校验人工核验快照（company_snapshots.json）。

运行：cd backend && python scripts/validate_snapshots.py
可选：--file path/to/other.json 校验其他快照文件
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from snapshot_utils import (
    SNAPSHOT,
    load_snapshot_file,
    unlocked_rules,
    validate_record,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验人工核验快照")
    parser.add_argument(
        "--file",
        type=Path,
        default=SNAPSHOT,
        help="快照文件路径，默认 backend/data/company_snapshots.json",
    )
    args = parser.parse_args()

    try:
        data = load_snapshot_file(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取失败：{exc}")
        return 1

    companies = data.get("companies") or {}
    if not companies:
        print("快照为空。请用 scripts/add_snapshot.py 录入真实公司信息。")
        print("说明：docs/manual_snapshot.md")
        return 0

    errors = 0
    for name, record in companies.items():
        print(f"\n== {name}")
        if not isinstance(record, dict):
            print("  [错误] 记录必须是对象")
            errors += 1
            continue
        record_errors = validate_record(record)
        for message in record_errors:
            print(f"  [错误] {message}")
        errors += len(record_errors)
        print(f"  可解锁一致性规则：{'、'.join(unlocked_rules(record)) or '无'}")

    print(f"\n检查完成：{len(companies)} 条记录，错误 {errors} 个。")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
