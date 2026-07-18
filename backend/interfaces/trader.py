from __future__ import annotations

from abc import ABC, abstractmethod


class Trader(ABC):
    @abstractmethod
    async def run(self) -> str:
        pass
