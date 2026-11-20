"""classify_jd：TF-IDF + LogisticRegression 岗位风险概率（不使用 LLM）。

模型由 scripts/train_model.py 用 backend/data/dataset_full.csv 训练生成
app/data/model.pkl + vectorizer.pkl。模型不存在时返回 available=False，
由融合逻辑降级为「规则 + 低置信度」，不编造概率。
"""

from __future__ import annotations

from functools import lru_cache

from ..config import settings

_loaded = False
_pipeline = None


def _load() -> None:
    global _loaded, _pipeline
    if _loaded:
        return
    _loaded = True
    if not (settings.model_path.exists() and settings.vectorizer_path.exists()):
        return
    try:
        import joblib

        vectorizer = joblib.load(settings.vectorizer_path)
        model = joblib.load(settings.model_path)
        _pipeline = (vectorizer, model)
    except Exception:
        _pipeline = None


@lru_cache(maxsize=2048)
def _predict(text: str) -> float:
    vectorizer, model = _pipeline  # type: ignore[misc]
    features = vectorizer.transform([text])
    prob = model.predict_proba(features)[0][1]
    return float(prob)


def classify_jd(text: str) -> dict:
    """返回 {prob, available, note}。"""
    _load()
    if _pipeline is None:
        return {
            "prob": None,
            "available": False,
            "note": "未找到训练模型（运行 scripts/train_model.py 生成 app/data/model.pkl）",
        }
    try:
        return {"prob": round(_predict(text), 4), "available": True, "note": None}
    except Exception as exc:  # 模型或向量化不兼容时降级
        return {"prob": None, "available": False, "note": f"模型推理失败：{exc}"}
