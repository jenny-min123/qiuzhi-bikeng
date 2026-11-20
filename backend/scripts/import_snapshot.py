"""从工商截图直接生成人工核验快照（个人录入工具）。

流程：本地 OCR 识别截图 -> 抽取候选字段 -> 逐项人工核对 -> 校验 -> 写入 JSON。
图片只在本机处理，不上传第三方。

用法：
  cd backend
  python scripts/import_snapshot.py C:\\截图\\示例公司.png

  # 多张截图依次录入
  python scripts/import_snapshot.py shot1.png shot2.png

  # 只看结果不写入
  python scripts/import_snapshot.py shot.png --dry-run

  # 预填来源 URL，省得每次手打
  python scripts/import_snapshot.py shot.png --source-url https://www.gsxt.gov.cn/

核对时：
  直接回车   = 接受候选值（没有候选值时，可选字段回车跳过）
  输入新内容 = 用你输入的值替换
  输入 -     = 清空可选字段
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import ocr  # noqa: E402
from app.config import settings  # noqa: E402
from app.tools.snapshot_extract import extract_snapshot_fields  # noqa: E402
from app.tools.snapshot_store import (  # noqa: E402
    parse_date,
    unlocked_rules,
    upsert_record,
    validate_record,
)

# 与企查查「工商信息」页蓝框字段一一对应
FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("company", "企业名称", True),
    ("credit_code", "统一社会信用代码", False),
    ("legal_representative", "法定代表人", False),
    ("registration_status", "登记状态", True),
    ("founded_at", "成立日期（YYYY-MM-DD）", True),
    ("registered_capital", "注册资本", False),
    ("paid_in_capital", "实缴资本", False),
    ("organization_code", "组织机构代码", False),
    ("business_registration_no", "工商注册号", False),
    ("taxpayer_id", "纳税人识别号", False),
    ("company_type", "企业类型", False),
    ("business_term", "营业期限", False),
    ("taxpayer_qualification", "纳税人资质", False),
    ("insured_count", "参保人数", True),
    ("approval_date", "核准日期（YYYY-MM-DD）", False),
    ("region", "所属地区", False),
    ("registration_authority", "登记机关", False),
    ("industry", "国标行业", False),
    ("english_name", "英文名", False),
    ("registered_address", "注册地址", True),
    ("mailing_address", "通信地址", False),
    ("business_scope", "经营范围", True),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="工商截图 -> OCR -> 人工核对 -> 写入 company_snapshots.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("images", nargs="+", type=Path, help="工商页面截图路径")
    parser.add_argument(
        "--file", type=Path, default=settings.snapshot_path, help="快照 JSON 路径"
    )
    parser.add_argument("--source-url", help="来源 URL，给出后不再逐张询问")
    parser.add_argument("--fetched-at", help="查询日期，默认今天")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    parser.add_argument("--force", action="store_true", help="允许新增名称相近的主体")
    parser.add_argument("--yes", action="store_true", help="跳过最后一步写入确认")
    return parser


def ask_text(label: str, current: str | None, required: bool) -> str:
    current = (current or "").strip()
    hint = current if current else ("必填" if required else "可选，回车跳过")
    while True:
        answer = input(f"{label} [{hint}]: ").strip()
        if answer == "":
            if current:
                return current
            if not required:
                return ""
            print("  这项必填，请填写。")
            continue
        if answer == "-":
            if required:
                print("  必填字段不能用 - 清空。")
                continue
            return ""
        return answer


def ask_int(label: str, current: int | None, required: bool) -> int | None:
    current_text = "" if current is None else str(current)
    while True:
        answer = ask_text(label, current_text or None, required)
        if answer == "":
            return None
        try:
            value = int(answer)
        except ValueError:
            print("  请输入整数。")
            continue
        if value < 0:
            print("  不能是负数。")
            continue
        return value


def ask_date(label: str, current: str | None, required: bool = True) -> str:
    while True:
        answer = ask_text(label, current, required)
        if answer == "":
            return ""
        parsed = parse_date(answer)
        if parsed:
            return parsed.isoformat()
        print("  日期格式无法识别，请用 YYYY-MM-DD。")


def ask_url(label: str, current: str | None) -> str:
    while True:
        answer = ask_text(label, current, required=True)
        if answer.startswith(("http://", "https://")):
            return answer
        print("  URL 必须以 http:// 或 https:// 开头。")


def collect_record(candidates: dict, args: argparse.Namespace) -> dict:
    record: dict = {}
    for key, label, required in FIELDS:
        current = candidates.get(key)
        if key == "insured_count":
            value = ask_int(label, current, required)
        elif key in ("founded_at", "approval_date"):
            value = ask_date(label, current, required)
        else:
            value = ask_text(label, current, required)
        if value not in (None, ""):
            record[key] = value

    record["source_url"] = ask_url("来源 URL", args.source_url)
    record["fetched_at"] = ask_date(
        "查询日期（YYYY-MM-DD）",
        args.fetched_at or date.today().isoformat(),
    )
    note = ask_text("备注", None, required=False)
    if note:
        record["note"] = note
    return record


def preview(company: str, record: dict) -> None:
    print("\n将写入的记录：")
    print(json.dumps({company: record}, ensure_ascii=False, indent=2))
    rules = unlocked_rules(record)
    print(f"可解锁一致性规则：{'、'.join(rules) if rules else '无'}")


def process_image(image: Path, args: argparse.Namespace) -> int:
    if not image.exists():
        print(f"找不到文件：{image}")
        return 2
    content = image.read_bytes()
    if len(content) > 10 * 1024 * 1024:
        print(f"图片超过 10MB，请压缩后再试：{image}")
        return 2

    print(f"\n=== 识别 {image.name} ===")
    result = asyncio.run(ocr.recognize(content, image.name))
    if not result.configured:
        print(f"OCR 不可用：{result.note}")
        return 1
    if not result.text.strip():
        print(f"未识别到文字：{result.note}")
        return 2

    print("\n--- OCR 原文 ---")
    print(result.text)
    print("--- 原文结束 ---\n")

    extracted = extract_snapshot_fields(result.text, blocks=result.blocks)
    if extracted["missing_fields"]:
        print(f"截图中未识别到：{'、'.join(extracted['missing_fields'])}，请手工补充。")
    for warning in extracted["warnings"]:
        print(f"提示：{warning}")
    print()

    record = collect_record(extracted["fields"], args)

    errors = validate_record(record)
    if errors:
        print("校验失败，未写入：")
        for message in errors:
            print(f"  - {message}")
        return 2

    company = record.pop("company")
    preview(company, record)

    if args.dry_run:
        print("（--dry-run，未写入）")
        return 0

    if not args.yes:
        answer = input("确认写入？[Y/n]: ").strip().lower()
        if answer not in ("", "y", "yes", "是"):
            print("已取消。")
            return 1

    action, similar = upsert_record(
        company, record, path=args.file, force=args.force
    )
    if action == "conflict":
        print("发现名称相近的已有主体，未写入：")
        for name in similar:
            print(f"  - {name}")
        print("确认是不同主体时加 --force 重跑。")
        return 2

    print(f"{action}成功：{company}")
    print(f"快照文件：{args.file}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    exit_code = 0
    for image in args.images:
        exit_code = max(exit_code, process_image(image, args))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
