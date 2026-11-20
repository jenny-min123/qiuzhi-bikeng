"""训练岗位风险分类模型（V3 6.6 / 全栈方案 6.2）。

数据：backend/data/dataset_full.csv（当前 168 条：正 60 / 负 108）
流程：jieba 分词 → TF-IDF → LogisticRegression，训练:测试 = 7:3
输出：app/data/vectorizer.pkl + app/data/model.pkl

运行：cd backend && python scripts/train_model.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET = BASE_DIR / "data" / "dataset_full.csv"
OUT_DIR = BASE_DIR / "app" / "data"

sys.path.insert(0, str(BASE_DIR))

# 必须从模块导入，不能在本文件里定义：向量化器会 pickle 这个函数
from app.tools.tokenizer import cut  # noqa: E402


def main() -> int:
    if not DATASET.exists():
        print(f"找不到数据集：{DATASET}")
        return 1

    try:
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        print(f"缺少训练依赖：{exc}；请先 pip install -r requirements.txt")
        return 1

    with DATASET.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("jd_text") or "").strip()]

    texts = [r["jd_text"].strip() for r in rows]
    labels = [int(r["label"]) for r in rows]
    counts = Counter(labels)
    print(f"样本数：{len(texts)}，标签分布：{dict(counts)}")

    if len(texts) < 20 or len(counts) < 2:
        print("样本过少，至少需要两个类别且不少于 20 条")
        return 1

    vectorizer = TfidfVectorizer(
        tokenizer=cut,
        token_pattern=None,
        ngram_range=(1, 2),
        min_df=1,
        max_features=20000,
    )
    features = vectorizer.fit_transform(texts)

    stratify = labels if min(counts.values()) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.3, random_state=42, stratify=stratify
    )

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(x_train, y_train)

    print("\n测试集评估（重点看招转培类别召回率）：")
    print(
        classification_report(
            y_test, model.predict(x_test), digits=4, zero_division=0
        )
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, OUT_DIR / "vectorizer.pkl")
    joblib.dump(model, OUT_DIR / "model.pkl")
    print(f"已保存：{OUT_DIR / 'vectorizer.pkl'}")
    print(f"已保存：{OUT_DIR / 'model.pkl'}")
    print(
        "\n注意：当前数据集模板高度相似，随机划分的测试集接近重复样本，"
        "以上指标仅作基线，不代表泛化性能（见 V3 第八章）。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
