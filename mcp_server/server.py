"""FastMCP server wiring for the portfolio app."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app import PortfolioApp

logger = logging.getLogger(__name__)


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _serialize_summary(summary) -> Dict[str, Any]:
    return summary.model_dump(mode="json")


def _serialize_snapshot(snapshot) -> Dict[str, Any]:
    return snapshot.model_dump(mode="json")


def build_server(app: PortfolioApp, *, name: str, version: str) -> FastMCP:
    """Create a FastMCP server exposing the portfolio resources and tools."""

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        await app.start()
        try:
            yield None
        finally:
            await app.stop()

    mcp = FastMCP(name=name, lifespan=lifespan)

    @mcp.resource("portfolio://portfolios")
    async def list_portfolios_resource() -> str:
        """List available portfolios and holding counts."""
        data = app.list_portfolios()
        return _dump_json({"portfolios": data})

    @mcp.resource("portfolio://summary")
    async def summary_resource() -> str:
        """Overall portfolio metrics including market value and PnL."""
        summary = await app.summary()
        payload = _serialize_summary(summary)
        logger.info(
            "Resource summary portfolio=%s holdings=%s",
            payload["portfolio_id"],
            payload["holding_count"],
        )
        return _dump_json(payload)

    @mcp.resource("portfolio://summary/{portfolio_id}")
    async def summary_by_portfolio_resource(portfolio_id: str) -> str:
        """Portfolio-specific summary."""
        summary = await app.summary(portfolio_id=portfolio_id)
        payload = _serialize_summary(summary)
        logger.info(
            "Resource summary portfolio=%s holdings=%s",
            payload["portfolio_id"],
            payload["holding_count"],
        )
        return _dump_json(payload)

    @mcp.resource("portfolio://positions")
    async def positions_resource() -> str:
        """Full list of holdings with latest quotes and gains."""
        snapshots = await app.snapshots()
        data = [_serialize_snapshot(s) for s in snapshots]
        logger.info("Resource positions all count=%s", len(data))
        return _dump_json({"positions": data})

    @mcp.resource("portfolio://positions/{portfolio_id}")
    async def positions_by_portfolio_resource(portfolio_id: str) -> str:
        """Holdings for a specific portfolio."""
        snapshots = await app.snapshots(portfolio_id=portfolio_id)
        data = [_serialize_snapshot(s) for s in snapshots]
        logger.info("Resource positions portfolio=%s count=%s", portfolio_id, len(data))
        return _dump_json({"positions": data})

    @mcp.tool()
    async def refresh_prices() -> Dict[str, Any]:
        """Force an immediate price pull for every tracked ticker."""
        quotes = await app.refresh_prices()
        payload = {
            "symbols": sorted(quotes.keys()),
            "count": len(quotes),
        }
        logger.info("Tool refresh_prices count=%s", payload["count"])
        return payload

    @mcp.tool()
    async def get_positions(
        symbol: Optional[str] = None, portfolio_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return holdings, optionally filtered by ticker symbol or portfolio."""
        snapshots = await app.snapshots(portfolio_id=portfolio_id, symbol=symbol)
        items = [_serialize_snapshot(s) for s in snapshots]
        if symbol:
            target = symbol.upper()
            items = [item for item in items if item["holding"]["symbol"].upper() == target]
        logger.info(
            "Tool get_positions portfolio=%s symbol=%s result_count=%s",
            portfolio_id or "all",
            symbol or "*",
            len(items),
        )
        return items

    @mcp.tool()
    async def reload_portfolio() -> Dict[str, Any]:
        """Reload YAML holdings file from disk."""
        data = await app.reload_portfolio()
        result = {
            "base_currency": data.base_currency,
            "portfolio_count": len(app.store.portfolio_ids()),
            "portfolios": app.list_portfolios(),
        }
        logger.info("Tool reload_portfolio portfolio_count=%s", result["portfolio_count"])
        return result

    @mcp.tool()
    async def get_summary(portfolio_id: Optional[str] = None) -> Dict[str, Any]:
        """Return the current portfolio summary as structured data."""
        summary = await app.summary(portfolio_id=portfolio_id)
        payload = _serialize_summary(summary)
        logger.info(
            "Tool get_summary portfolio=%s total_market=%s",
            payload["portfolio_id"],
            payload["total_market"],
        )
        return payload

    @mcp.tool()
    async def list_portfolios() -> Dict[str, Any]:
        """List available portfolios with ids and holding counts."""
        result = {"portfolios": app.list_portfolios()}
        logger.info("Tool list_portfolios count=%s", len(result["portfolios"]))
        return result

    @mcp.tool()
    async def create_portfolio(
        portfolio_id: str, name: Optional[str] = None, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new empty portfolio."""
        definition = await app.create_portfolio(portfolio_id, name, notes)
        payload = definition.model_dump(mode="json")
        logger.info("Tool create_portfolio id=%s name=%s", portfolio_id, payload.get("name"))
        return payload

    @mcp.tool()
    async def update_portfolio(
        portfolio_id: str, name: Optional[str] = None, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update portfolio metadata such as name or notes."""
        definition = await app.update_portfolio(portfolio_id, name, notes)
        payload = definition.model_dump(mode="json")
        logger.info("Tool update_portfolio id=%s", portfolio_id)
        return payload

    @mcp.tool()
    async def delete_portfolio(portfolio_id: str, force: bool = False) -> Dict[str, Any]:
        """Delete a portfolio (set force=true to remove non-empty portfolios)."""
        definition = await app.delete_portfolio(portfolio_id, force)
        payload = definition.model_dump(mode="json")
        logger.info("Tool delete_portfolio id=%s force=%s", portfolio_id, force)
        return payload

    @mcp.tool()
    async def add_holding(
        portfolio_id: str,
        quantity: float,
        cost_basis: float,
        symbol: Optional[str] = None,
        search_query: Optional[str] = None,
        currency: Optional[str] = None,
        name: Optional[str] = None,
        broker: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
        holding_id: Optional[str] = None,
        search_region: Optional[str] = None,
        search_limit: int = 5,
    ) -> Dict[str, Any]:
        """Add a holding to a portfolio; use search_query for fuzzy ticker lookup."""
        result = await app.add_holding(
            portfolio_id,
            symbol=symbol,
            search_query=search_query,
            quantity=quantity,
            cost_basis=cost_basis,
            currency=currency,
            name=name,
            broker=broker,
            category=category,
            notes=notes,
            holding_id=holding_id,
            search_region=search_region,
            search_limit=search_limit,
        )
        logger.info(
            "Tool add_holding portfolio=%s symbol=%s quantity=%s cost=%s",
            portfolio_id,
            result.get("holding", {}).get("symbol"),
            quantity,
            cost_basis,
        )
        return result

    @mcp.tool()
    async def remove_holding(portfolio_id: str, holding_key: str) -> Dict[str, Any]:
        """Remove a holding by id or symbol from a portfolio."""
        result = await app.remove_holding(portfolio_id, holding_key)
        logger.info("Tool remove_holding portfolio=%s holding=%s", portfolio_id, holding_key)
        return result

    @mcp.tool()
    async def update_holding(
        portfolio_id: str,
        holding_id: str,
        quantity: Optional[float] = None,
        cost_basis: Optional[float] = None,
        notes: Optional[str] = None,
        broker: Optional[str] = None,
        category: Optional[str] = None,
        name: Optional[str] = None,
        currency: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update holding properties such as quantity, cost basis, symbol, or notes."""
        result = await app.update_holding(
            portfolio_id,
            holding_id,
            quantity=quantity,
            cost_basis=cost_basis,
            notes=notes,
            broker=broker,
            category=category,
            name=name,
            currency=currency,
            symbol=symbol,
        )
        logger.info("Tool update_holding portfolio=%s holding=%s", portfolio_id, holding_id)
        return result

    @mcp.tool()
    async def search_symbols(
        query: str, region: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        """Fuzzy search for symbols via yfinance SDK."""
        result = await app.search_symbols(query, region, limit)
        logger.info(
            "Tool search_symbols query=%s results=%s error=%s",
            query,
            len(result.get("results", [])),
            result.get("error"),
        )
        return result

    return mcp
