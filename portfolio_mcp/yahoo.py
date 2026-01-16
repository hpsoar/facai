"""Symbol search helpers backed by the yfinance SDK."""

from __future__ import annotations

from typing import Optional

import logging

import yfinance as yf

from .yfinance_utils import configure_network

logger = logging.getLogger(__name__)


def search_symbols(
    query: str,
    *,
    region: Optional[str] = None,
    quotes_count: int = 5,
    proxy: Optional[str] = None,
    timeout: int = 10,
) -> list[dict]:
    limit = max(1, quotes_count)
    configure_network(proxy, None)
    try:
        search = yf.Search(
            query,
            max_results=limit,
            news_count=0,
            lists_count=0,
            include_cb=False,
            include_nav_links=False,
            include_research=False,
            include_cultural_assets=False,
            enable_fuzzy_query=True,
            timeout=timeout,
        )
        quotes = search.quotes or []
        logger.debug(
            "yfinance search query=%s limit=%s region=%s quote_types=%s",
            query,
            limit,
            region,
            [type(q).__name__ for q in (quotes if isinstance(quotes, list) else [quotes])],
        )
    except Exception as exc:  # pragma: no cover - network failures
        logger.exception("yfinance search failed for query=%s region=%s", query, region)
        raise RuntimeError(f"yfinance search failed: {exc}") from exc

    results: list[dict] = []
    for quote in quotes:
        if not isinstance(quote, dict):
            logger.debug(
                "yfinance search skipping non-dict entry type=%s value=%r", type(quote), quote
            )
            continue
        results.append(
            {
                "symbol": quote.get("symbol"),
                "shortName": quote.get("shortname") or quote.get("shortName"),
                "longName": quote.get("longname") or quote.get("longName"),
                "exchange": quote.get("exchange") or quote.get("exchDisp"),
                "quoteType": quote.get("quoteType"),
            }
        )
    return results
