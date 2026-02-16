from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseNode(ABC):
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
