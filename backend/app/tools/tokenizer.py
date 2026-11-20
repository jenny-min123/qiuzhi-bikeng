"""jieba 分词器。

必须放在可导入模块的顶层：TF-IDF 向量化器会把这个函数一起 pickle，
若定义在 scripts/train_model.py 的 __main__ 里，线上加载模型时会报
"Can't get attribute 'cut'"。
"""

from __future__ import annotations


def cut(text: str) -> list[str]:
    import jieba

    return jieba.lcut(text)
