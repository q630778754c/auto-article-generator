"""五环节Step基类与结果（design 2.1.5）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StepResult:
    success: bool
    next_status: str = ""
    detail: dict = field(default_factory=dict)
    error: str = ""
    degraded: bool = False
    pending: bool = False


class BaseStep(ABC):
    """环节基类：前置校验 → 调用领域服务 → 原子写状态。"""

    step_name: str = ""

    @abstractmethod
    async def execute(self, article_id: int, **kwargs) -> StepResult:
        ...

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")