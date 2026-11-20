"""证据源统一接口（V3 6.1：统一证据提供者接口）。

换数据源 = 增删一个 Provider 文件，评分逻辑不动（全栈方案 5.3）。
任何 Provider 失败都必须返回 retrieved=False，而不是抛给上层。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EvidenceResult:
    source: str
    retrieved: bool
    weight: float
    penalty: float = 0.0
    evidence_id: str = ""
    detail: dict = field(default_factory=dict)
    note: str | None = None


class EvidenceProvider(ABC):
    name: str
    weight: float

    @abstractmethod
    async def fetch(self, company: str) -> EvidenceResult:
        """查询证据。拿不到时返回 retrieved=False 并说明原因。"""

    def unavailable(self, note: str) -> EvidenceResult:
        return EvidenceResult(
            source=self.name,
            retrieved=False,
            weight=self.weight,
            note=note,
        )
