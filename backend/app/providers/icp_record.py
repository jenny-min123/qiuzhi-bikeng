"""ICP 备案证据源（V3 6.4）。

工信部备案系统没有稳定的公开查询 API，本框架保留 Provider 接口；
未接入查询通道时返回 retrieved=False，由 score_company 做权重归一化。
"""

from __future__ import annotations

from .base import EvidenceProvider, EvidenceResult


class ICPRecordProvider(EvidenceProvider):
    name = "ICP备案"
    weight = 15.0

    async def fetch(self, company: str) -> EvidenceResult:
        return self.unavailable(
            "ICP 备案查询通道未接入（需按域名查询工信部备案系统），本次跳过"
        )
