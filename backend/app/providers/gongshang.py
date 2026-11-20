"""工商信息证据源（可选，V3 3.1「可插拔」原则的权重最高一路）。

框架阶段没有配置工商数据通道，返回 retrieved=False；
后续接入企查查 / 天眼查等开放 API 时，只需实现本文件的 fetch。
"""

from __future__ import annotations

from .base import EvidenceProvider, EvidenceResult


class GongshangProvider(EvidenceProvider):
    name = "工商信息"
    weight = 25.0

    async def fetch(self, company: str) -> EvidenceResult:
        return self.unavailable(
            "工商数据通道未配置（可选证据源），本次分析不包含工商字段"
        )
