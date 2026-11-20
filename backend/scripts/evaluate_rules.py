"""规则引擎基线评估（对应论文实验一中的「A 纯规则」方案）。

在 backend/data/dataset_full.csv 上逐条运行 scan_phrases，用不同风险分阈值
计算 Precision / Recall / F1，并列出误报、漏报样本，便于迭代词表与边界规则。

注意：当前词表 v0.2 是依据本数据集校准的，因此这里的结果属于「样本内评估」，
不能当作泛化性能。论文中必须如实说明，并按 V3 第八章的建议留出独立真实分布
校验集复测（正样本来源 ③④ 不参与校准）。

运行：cd backend && python scripts/evaluate_rules.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.tools.scan_phrases import scan_phrases  # noqa: E402

DATASET = BASE_DIR / "data" / "dataset_full.csv"


def load_rows() -> list[dict]:
    with DATASET.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("jd_text") or "").strip()]


def metrics(preds: list[int], labels: list[int]) -> dict:
    tp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(preds, labels) if p == 1 and y == 0)
    tn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 0)
    fn = sum(1 for p, y in zip(preds, labels) if p == 0 and y == 1)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> int:
    rows = load_rows()
    labels = [int(r["label"]) for r in rows]
    results = [scan_phrases(r["jd_text"]) for r in rows]

    print(f"样本数：{len(rows)}，正样本 {sum(labels)}，负样本 {len(labels) - sum(labels)}")
    print("\n=== 阈值扫描（score >= 阈值判为风险） ===")
    print(f"{'策略':<14}{'TP':>4}{'FP':>4}{'TN':>4}{'FN':>4}{'P':>9}{'R':>9}{'F1':>9}")
    for name, preds in [("任一命中", [1 if r["hits"] else 0 for r in results])] + [
        (
            f"score>={t}",
            [1 if r["score"] >= t else 0 for r in results],
        )
        for t in (20, 30, 40, 50, 60)
    ]:
        m = metrics(preds, labels)
        print(
            f"{name:<14}{m['tp']:>4}{m['fp']:>4}{m['tn']:>4}{m['fn']:>4}"
            f"{m['precision']:>9.3f}{m['recall']:>9.3f}{m['f1']:>9.3f}"
        )

    print(
        "\n注意：词表依据同一数据集校准，以上为样本内评估，不能作为泛化性能；"
        "论文需用独立真实分布校验集复测。"
    )

    threshold = 40
    print(f"\n=== score>={threshold} 误报（负样本被判风险，最多 10 条） ===")
    shown = 0
    for row, result in zip(rows, results):
        if int(row["label"]) == 0 and result["score"] >= threshold:
            print(
                f"{row['id']} score={result['score']} "
                f"hits={[(h['type'], h['fragment']) for h in result['hits']]}"
            )
            print("  ", row["jd_text"][:100].replace("\n", " "))
            shown += 1
            if shown >= 10:
                break
    if not shown:
        print("无")

    print(f"\n=== score<{threshold} 漏报（正样本被判正常，最多 10 条） ===")
    shown = 0
    for row, result in zip(rows, results):
        if int(row["label"]) == 1 and result["score"] < threshold:
            print(
                f"{row['id']} score={result['score']} "
                f"hits={[(h['type'], h['fragment']) for h in result['hits']]}"
            )
            print("  ", row["jd_text"][:100].replace("\n", " "))
            shown += 1
            if shown >= 10:
                break
    if not shown:
        print("无")

    print("\n=== 负样本中「岗前培训」类话术的放行检查 ===")
    checked = 0
    for row, result in zip(rows, results):
        if int(row["label"]) == 0 and any(
            w in row["jd_text"] for w in ("岗前培训", "免费入职培训", "公司提供岗前培训")
        ):
            flagged = [h for h in result["hits"] if "培训" in h["fragment"]]
            print(
                f"{row['id']} score={result['score']} 培训类命中={flagged or '已放行'}"
            )
            checked += 1
            if checked >= 10:
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
