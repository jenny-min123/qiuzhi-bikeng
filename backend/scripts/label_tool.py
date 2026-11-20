"""标注集检查工具（V3 6.6：标注 ≠ 爬虫，span 千万别省）。

功能：
- stats   统计标签 / 来源分布
- check   校验每条样本的 evidence span 是否与原文对齐
- show N  查看前 N 条样本

运行：cd backend && python scripts/label_tool.py stats
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent / "data" / "dataset_full.csv"


def load_rows() -> list[dict]:
    with DATASET.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("jd_text") or "").strip()]


def stats(rows: list[dict]) -> None:
    print(f"总样本：{len(rows)}")
    print("标签分布：", dict(Counter(r["label"] for r in rows)))
    print("来源分布：")
    for source, count in Counter(r["source"] for r in rows).most_common():
        print(f"  {count:>4}  {source}")
    print("类别分布：", dict(Counter(r["category"] for r in rows)))


def check(rows: list[dict]) -> int:
    problems = 0
    missing_span = 0
    for row in rows:
        raw = (row.get("spans") or "").strip()
        if not raw:
            missing_span += 1
            continue
        try:
            spans = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[解析失败] {row['id']}: spans 不是合法 JSON")
            problems += 1
            continue
        text = row["jd_text"]
        for span in spans:
            phrase = span.get("phrase", "")
            start, end = span.get("start"), span.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                print(f"[类型错误] {row['id']}: span 非整数 {span}")
                problems += 1
                continue
            actual = text[start:end]
            if actual != phrase:
                print(
                    f"[偏移不一致] {row['id']}: 期望「{phrase}」，实际「{actual}」"
                    f" ({start},{end})"
                )
                problems += 1
    print(f"\n检查完成：{len(rows)} 条，span 问题 {problems} 个，无 span 样本 {missing_span} 条")
    return 0 if problems == 0 else 2


def show(rows: list[dict], limit: int) -> None:
    for row in rows[:limit]:
        print("-" * 60)
        print(f"id={row['id']} label={row['label']} source={row['source']}")
        print(row["jd_text"])
        print(f"spans={row.get('spans')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["stats", "check", "show"])
    parser.add_argument("n", nargs="?", type=int, default=5)
    args = parser.parse_args()

    if not DATASET.exists():
        print(f"找不到数据集：{DATASET}")
        return 1

    rows = load_rows()
    if args.command == "stats":
        stats(rows)
        return 0
    if args.command == "check":
        return check(rows)
    show(rows, args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
