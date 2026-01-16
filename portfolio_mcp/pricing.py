"""Price fetching utilities with caching."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

import httpx

from .models import PriceQuote
from .proxy import resolve_proxy

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
    "Connection": "keep-alive",
}

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    quote: PriceQuote
    expires_at: datetime


class PriceService:
    """Fetches quotes via Yahoo Finance public quote API with a TTL cache."""

    def __init__(
        self,
        ttl_seconds: int = 300,
        timeout: float = 10.0,
        proxy: Optional[str] = None,
        max_retries: Optional[int] = None,
    ):
        self.ttl = timedelta(seconds=max(ttl_seconds, 0))
        self.timeout = timeout
        self.proxy = resolve_proxy(proxy)
        self.max_retries = (
            int(max_retries)
            if max_retries is not None
            else int(os.environ.get("YF_MAX_RETRIES", "2") or 0)
        )
        self.max_retries = max(self.max_retries, 0)
        self._cache: Dict[str, CacheEntry] = {}
        client_kwargs = {"timeout": self.timeout, "headers": REQUEST_HEADERS}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
        self._client = httpx.Client(**client_kwargs)

    async def aclose(self) -> None:
        await asyncio.to_thread(self._client.close)

    async def get_quotes(self, symbols: Iterable[str]) -> Dict[str, PriceQuote]:
        tasks = [self._get_symbol(symbol) for symbol in symbols]
        quotes = await asyncio.gather(*tasks)
        return {quote.symbol.upper(): quote for quote in quotes}

    async def refresh_all(self, symbols: Iterable[str]) -> Dict[str, PriceQuote]:
        return await self.get_quotes(symbols)

    async def get_quote(self, symbol: str) -> PriceQuote:
        return await self._get_symbol(symbol)

    async def _get_symbol(self, symbol: str) -> PriceQuote:
        normalized = symbol.upper()
        cached = self._cache.get(normalized)
        now = datetime.now(timezone.utc)
        if cached and cached.expires_at > now:
            return cached.quote
        quote = await asyncio.to_thread(self._fetch_quote_sync, normalized)
        self._cache[normalized] = CacheEntry(
            quote=quote,
            expires_at=now + self.ttl if self.ttl.total_seconds() else now,
        )
        return quote

    def _fetch_quote_sync(self, symbol: str) -> PriceQuote:
        now = datetime.now(timezone.utc)
        params = {"symbols": symbol}
        price: Optional[float] = None
        currency: Optional[str] = None
        provider = "yahoo_quote_api"
        attempts = self.max_retries + 1
        try:
            response = self._client.get(YAHOO_QUOTE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            result = (payload.get("quoteResponse") or {}).get("result") or []
            if result:
                info = result[0]
                price = info.get("regularMarketPrice") or info.get("postMarketPrice")
                currency = info.get("currency")
        except Exception:
            # Network errors return an empty quote; caller will see price None.
            pass
        return PriceQuote(
            symbol=symbol,
            price=float(price) if price is not None else None,
            currency=currency,
            fetched_at=now,
            provider=provider,
        )
