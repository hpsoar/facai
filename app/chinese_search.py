"""Chinese stock search using AKShare and East Money APIs."""

from __future__ import annotations

import logging
import time
from typing import Optional

import akshare as ak
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class ChineseStockSearch:
    """Search Chinese stocks by Chinese company names or codes."""

    def __init__(self, cache_ttl_seconds: int = 86400):
        """Initialize Chinese stock search with caching.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default 24 hours)
        """
        self._cache: Optional[pd.DataFrame] = None
        self._cache_age: float = 0
        self._cache_ttl: float = cache_ttl_seconds

    def search(
        self,
        query: str,
        limit: int = 5,
        use_api: bool = True,
    ) -> list[dict]:
        """Search for Chinese stocks by name or code.

        Args:
            query: Chinese company name or stock code (e.g., "茅台", "腾讯", "600519")
            limit: Maximum number of results
            use_api: If True, try East Money search API first; if False, use local cache only

        Returns:
            List of dicts matching yfinance search_symbols format:
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
        # Try East Money API first for faster results
        if use_api:
            api_results = self._search_eastmoney_api(query, limit)
            if api_results:
                return api_results

        # Fallback to local AKShare cache
        return self._search_local_cache(query, limit)

    def _search_eastmoney_api(self, query: str, limit: int) -> list[dict]:
        """Search using East Money's suggestion API.

        This is faster than local search but may have rate limits.
        """
        try:
            url = "https://searchapi.eastmoney.com/api/suggest/get"
            params = {
                "input": query,
                "type": "14",
                "token": "D43BF722C8E33BDC906FB84D85E326E8",
                "count": str(limit),
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("QuotationCodeTable", {}).get("Data", [])
            if not items:
                return []

            results = []
            for item in items[:limit]:
                code = item.get("Code", "")
                name = item.get("Name", "")
                market_num = item.get("MktNum", "")

                # Map market numbers to yfinance format
                market_map = {
                    "0": "SZ",  # Shenzhen
                    "1": "SS",  # Shanghai
                    "116": "HK",  # Hong Kong
                }

                market = market_map.get(market_num, "")
                if not market:
                    continue

                # Pad code to 6 digits for A-shares
                if market in ("SZ", "SS") and len(code) < 6:
                    code = code.zfill(6)

                # Convert to yfinance format
                symbol = f"{code}.{market}"

                # Map market to exchange name
                exchange_map = {
                    "SZ": "SZSE",
                    "SS": "SSE",
                    "HK": "HKEX",
                }

                results.append(
                    {
                        "symbol": symbol,
                        "shortName": name,
                        "longName": name,
                        "exchange": exchange_map.get(market, "Unknown"),
                        "quoteType": "EQUITY",
                    }
                )

            logger.debug("East Money API search query=%s results=%d", query, len(results))
            return results

        except Exception as exc:
            logger.debug("East Money API search failed: %s", exc)
            return []

    def _search_local_cache(self, query: str, limit: int) -> list[dict]:
        """Search using locally cached AKShare stock list.

        This is slower but more reliable and doesn't depend on external API.
        """
        stocks = self._get_stock_list()

        # Fuzzy search by name or code
        matches = stocks[
            stocks["name"].str.contains(query, na=False)
            | stocks["code"].str.contains(query, na=False)
        ].head(limit)

        results = []
        for _, row in matches.iterrows():
            code = row["code"]
            name = row["name"]

            # Map to yfinance format
            if code.startswith("6"):  # Shanghai
                symbol = f"{code}.SS"
                exchange = "SSE"
            elif code.startswith(("0", "3")):  # Shenzhen
                symbol = f"{code}.SZ"
                exchange = "SZSE"
            elif code.startswith("8"):  # Beijing
                symbol = f"{code}.BJ"
                exchange = "BSE"
            else:
                symbol = code
                exchange = "Unknown"

            results.append(
                {
                    "symbol": symbol,
                    "shortName": name,
                    "longName": name,
                    "exchange": exchange,
                    "quoteType": "EQUITY",
                }
            )

        logger.debug("Local cache search query=%s results=%d", query, len(results))
        return results

    def _get_stock_list(self) -> pd.DataFrame:
        """Get cached stock list from AKShare, refresh if expired."""
        now = time.time()

        if self._cache is None or (now - self._cache_age) > self._cache_ttl:
            logger.info("Fetching Chinese stock list from AKShare")
            try:
                self._cache = ak.stock_info_a_code_name()
                self._cache_age = now
            except Exception as exc:
                logger.warning("Failed to fetch stock list: %s", exc)
                # Return empty DataFrame on error
                if self._cache is None:
                    self._cache = pd.DataFrame(columns=["code", "name"])

        return self._cache

    def is_chinese_query(self, query: str) -> bool:
        """Check if query contains Chinese characters.

        Args:
            query: Search query string

        Returns:
            True if query contains Chinese characters, False otherwise
        """
        return any("\u4e00" <= char <= "\u9fff" for char in query)
