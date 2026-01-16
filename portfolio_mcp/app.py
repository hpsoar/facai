"""High-level coordinator for portfolio data and pricing."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .config import Settings
from .models import (
    Holding,
    HoldingSnapshot,
    PortfolioDefinition,
    PortfolioFile,
    PortfolioSummary,
    PriceQuote,
)
from .portfolio import AGGREGATE_PORTFOLIO_ID, PortfolioStore
from .pricing import PriceService
from .proxy import resolve_proxy
from .scheduler import PricePoller
from .yahoo import search_symbols as yahoo_symbol_search


class PortfolioApp:
    """Glues together storage, pricing, and refresh logic."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = PortfolioStore(settings.portfolio_file)
        self.price_service = PriceService(settings.price_ttl_seconds)
        self.poller = PricePoller(self.store, self.price_service, settings.refresh_interval_seconds)
        self._startup_lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        async with self._startup_lock:
            if self._started:
                return
            await self.poller.ensure_warm()
            await self.poller.start()
            self._started = True

    async def stop(self) -> None:
        async with self._startup_lock:
            if not self._started:
                return
            await self.poller.stop()
            await self.price_service.aclose()
            self._started = False

    async def refresh_prices(self) -> Dict[str, PriceQuote]:
        return await self.poller.refresh_now()

    async def quotes(self) -> Dict[str, PriceQuote]:
        return await self.poller.ensure_warm()

    async def snapshots(self, portfolio_id: Optional[str] = None) -> List[HoldingSnapshot]:
        quotes = await self.quotes()
        return self.store.snapshots(quotes, portfolio_id)

    async def summary(self, portfolio_id: Optional[str] = None) -> PortfolioSummary:
        quotes = await self.quotes()
        return self.store.summary(quotes, portfolio_id)

    async def reload_portfolio(self) -> PortfolioFile:
        return await asyncio.to_thread(self.store.reload)

    def list_portfolios(self) -> List[Dict[str, Optional[str]]]:
        meta = self.store.portfolio_metadata()
        total_holdings = 0
        for item in meta:
            count = item.get("holding_count")
            if isinstance(count, int):
                total_holdings += count
        combined = {
            "id": AGGREGATE_PORTFOLIO_ID,
            "name": "All Portfolios",
            "holding_count": total_holdings,
        }
        return [combined, *meta]

    async def create_portfolio(
        self, portfolio_id: str, name: Optional[str], notes: Optional[str]
    ) -> PortfolioDefinition:
        definition = self.store.create_portfolio(portfolio_id, name, notes)
        self.store.reload()
        return definition

    async def update_portfolio(
        self, portfolio_id: str, name: Optional[str], notes: Optional[str]
    ) -> PortfolioDefinition:
        definition = self.store.update_portfolio(portfolio_id, name=name, notes=notes)
        self.store.reload()
        return definition

    async def delete_portfolio(self, portfolio_id: str, force: bool) -> PortfolioDefinition:
        definition = self.store.delete_portfolio(portfolio_id, force=force)
        self.store.reload()
        return definition

    async def add_holding(
        self,
        portfolio_id: str,
        *,
        symbol: Optional[str],
        search_query: Optional[str],
        quantity: float,
        cost_basis: float,
        currency: Optional[str],
        name: Optional[str],
        broker: Optional[str],
        category: Optional[str],
        notes: Optional[str],
        holding_id: Optional[str],
        search_region: Optional[str],
        search_limit: int,
    ) -> Dict[str, Any]:
        proxy = resolve_proxy()
        resolved_symbol = symbol
        matches: List[Dict[str, Optional[str]]] = []
        if not resolved_symbol and search_query:
            try:
                matches = await asyncio.to_thread(
                    yahoo_symbol_search,
                    search_query,
                    region=search_region,
                    quotes_count=search_limit,
                    proxy=proxy,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Symbol search failed for query '{search_query}': {exc}"
                ) from exc
            if not matches:
                raise ValueError(f"No symbols found for query '{search_query}'")
            resolved_symbol = matches[0].get("symbol")
        if not resolved_symbol:
            raise ValueError("symbol or search_query must be provided")
        holding = Holding(
            id=holding_id,
            symbol=resolved_symbol,
            quantity=quantity,
            cost_basis=cost_basis,
            currency=currency,
            name=name,
            broker=broker,
            category=category,
            notes=notes,
        )
        saved = self.store.add_holding(portfolio_id, holding)
        self.store.reload()
        await self.poller.refresh_now()
        return {"holding": saved.model_dump(mode="json"), "search_matches": matches}

    async def remove_holding(self, portfolio_id: str, holding_key: str) -> Dict[str, Any]:
        holding = self.store.remove_holding(portfolio_id, holding_key)
        self.store.reload()
        await self.poller.refresh_now()
        return {"holding": holding.model_dump(mode="json")}

    async def update_holding(
        self,
        portfolio_id: str,
        holding_id: str,
        *,
        quantity: Optional[float],
        cost_basis: Optional[float],
        notes: Optional[str],
        broker: Optional[str],
        category: Optional[str],
        name: Optional[str],
        currency: Optional[str],
    ) -> Dict[str, Any]:
        holding = self.store.update_holding(
            portfolio_id,
            holding_id,
            quantity=quantity,
            cost_basis=cost_basis,
            notes=notes,
            broker=broker,
            category=category,
            name=name,
            currency=currency,
        )
        self.store.reload()
        await self.poller.refresh_now()
        return {"holding": holding.model_dump(mode="json")}

    async def search_symbols(self, query: str, region: Optional[str], limit: int) -> Dict[str, Any]:
        proxy = resolve_proxy()
        try:
            results = await asyncio.to_thread(
                yahoo_symbol_search,
                query,
                region=region,
                quotes_count=limit,
                proxy=proxy,
            )
            return {"results": results}
        except Exception as exc:
            return {"results": [], "error": str(exc)}
