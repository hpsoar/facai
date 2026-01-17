"""Background refresh loop for quotes."""

from __future__ import annotations

import asyncio
from typing import Dict

from .portfolio import PortfolioStore
from .pricing import PriceService
from .models import PriceQuote


class PricePoller:
    def __init__(self, store: PortfolioStore, service: PriceService, interval_seconds: int):
        self.store = store
        self.service = service
        self.interval = max(interval_seconds, 0)
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._quotes: Dict[str, PriceQuote] = {}

    async def start(self) -> None:
        if self._task or self.interval == 0:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

async def refresh_now(self) -> Dict[str, PriceQuote]:
        symbols = self.store.symbols()
        quotes = await self.service.refresh_all(symbols)
        return quotes

    async def cached_quotes(self) -> Dict[str, PriceQuote]:
        async with self._lock:
            return dict(self._quotes)

    async def ensure_warm(self) -> Dict[str, PriceQuote]:
        quotes = await self.cached_quotes()
        if quotes:
            return quotes
        return await self.refresh_now()

    async def _loop(self) -> None:
        while True:
            try:
                await self.refresh_now()
            except Exception:
                # Avoid crashing the poller for transient errors.
                await asyncio.sleep(5)
                continue
            await asyncio.sleep(self.interval)
