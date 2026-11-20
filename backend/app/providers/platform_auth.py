"""招聘平台企业认证证据源（V3 6.4）。

平台企业主页认证标识与在招职位数需要平台侧页面解析；框架阶段不写
爬虫（V3 6.7 合规红线），保留 Provider 插件位，明确返回未获取。
"""

from __future__ import annotations

from .base import EvidenceProvider, EvidenceResult


class PlatformAuthProvider(EvidenceProvider):
    name = "平台企业认证"
    weight = 15.0

    async def fetch(self, company: str) -> EvidenceResult:
        return self.unavailable(
            "招聘平台企业认证数据未接入（需平台页面解析），本次跳过"
        )
