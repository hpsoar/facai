"""Symbol search helpers backed by the yfinance SDK and Chinese stock APIs."""

from __future__ import annotations

from typing import Optional

import logging

import yfinance as yf

from .chinese_search import ChineseStockSearch
from .yfinance_utils import configure_network

logger = logging.getLogger(__name__)

# Global Chinese search instance with caching
_chinese_search: Optional[ChineseStockSearch] = None


def search_symbols(
    query: str,
    *,
    region: Optional[str] = None,
    quotes_count: int = 5,
    proxy: Optional[str] = None,
    timeout: int = 10,
) -> list[dict]:
    """Search for stock symbols, with automatic Chinese stock support.

    If the query contains Chinese characters, uses Chinese stock search APIs
    (AKShare + East Money) to find matching stocks. Otherwise, falls back to
    yfinance search.

    Args:
        query: Search query (Chinese name, English name, or stock code)
        region: Ignored (kept for API compatibility)
        quotes_count: Maximum number of results
        proxy: Proxy URL for network requests
        timeout: Request timeout in seconds

    Returns:
        List of dicts with symbol info in yfinance format:
        [
            {
                "symbol": "600519.SS",
                "shortName": "贵州茅台",
                "longName": "贵州茅台酒股份有限公司",
                "exchange": "SSE",
                "quoteType": "EQUITY"
            }
        ]
    """
    global _chinese_search

    # Detect Chinese characters and use Chinese search APIs
    if _contains_chinese(query):
        if _chinese_search is None:
            _chinese_search = ChineseStockSearch()

        try:
            results = _chinese_search.search(query, limit=quotes_count)
            if results:
                logger.info("Chinese search query=%s results=%d", query, len(results))
                return results
        except Exception as exc:
            logger.warning("Chinese search failed for query=%s: %s", query, exc)
            # Fall through to yfinance search

    # Fallback to yfinance search for non-Chinese or failed Chinese searches
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


def _contains_chinese(query: str) -> bool:
    """Check if query contains Chinese characters.

    Args:
        query: Search query string

    Returns:
        True if query contains Chinese characters, False otherwise
    """
    return any("\u4e00" <= char <= "\u9fff" for char in query)
