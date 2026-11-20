"""社交口碑证据源（V3 6.3 / 6.4）。

V3 明确：口碑信号误伤风险最高，权重最低，只出「提示」不出「判定」。
因此本 Provider 即使接入搜索通道，也只返回 penalty=0 的提示证据。
框架阶段未接入搜索 API，返回未获取。
"""

from __future__ import annotations

from .base import EvidenceProvider, EvidenceResult


class SocialSentimentProvider(EvidenceProvider):
    name = "社交口碑"
    weight = 5.0

    async def fetch(self, company: str) -> EvidenceResult:
        return self.unavailable(
            "搜索引擎口碑计数通道未接入（V3 要求只存命中数、不存言论原文），本次跳过"
        )
