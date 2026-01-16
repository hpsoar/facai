"""Price fetching utilities with caching."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

import requests
import yfinance as yf

from .models import PriceQuote
from .proxy import resolve_proxy

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
    """Fetches quotes via yfinance with a TTL cache."""

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

    async def aclose(self) -> None:
        return None

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
        price: Optional[float] = None
        currency: Optional[str] = None
        provider = "yfinance_sdk"
        attempts = self.max_retries + 1
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                with self._create_session() as session:
                    ticker = yf.Ticker(symbol, session=session)
                    price, currency = self._extract_price_and_currency(ticker)
                if price is not None:
                    break
            except Exception as exc:
                last_error = exc
                logger.debug(
                    "yfinance fetch failed for %s (attempt %s/%s): %s",
                    symbol,
                    attempt + 1,
                    attempts,
                    exc,
                )
            if attempt < attempts - 1:
                backoff = min(2 ** attempt, 5)
                time.sleep(backoff)
        if price is None and last_error is not None:
            logger.warning("Failed to fetch price for %s via yfinance: %s", symbol, last_error)
        return PriceQuote(
            symbol=symbol,
            price=float(price) if price is not None else None,
            currency=currency,
            fetched_at=now,
            provider=provider,
        )

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
        if self.proxy:
            session.proxies.update({"http": self.proxy, "https": self.proxy})
        original_request = session.request

        def request_with_timeout(method, url, **kwargs):  # type: ignore[override]
            kwargs.setdefault("timeout", self.timeout)
            return original_request(method, url, **kwargs)

        session.request = request_with_timeout  # type: ignore[assignment]
        return session

    def _extract_price_and_currency(self, ticker: yf.Ticker) -> tuple[Optional[float], Optional[str]]:
        price = None
        currency = None
        fast_info = getattr(ticker, "fast_info", None)
        fast_info_dict = None
        if fast_info is not None:
            try:
                fast_info_dict = dict(fast_info)
            except Exception:
                fast_info_dict = fast_info
        if fast_info_dict:
            get = fast_info_dict.get  # type: ignore[attr-defined]
            price = self._safe_float(get("last_price")) or self._safe_float(
                get("regular_market_price")
            )
            currency = get("currency") or get("last_price_currency")
        if price is None:
            history = ticker.history(period="5d", interval="1d", auto_adjust=False, actions=False)
            price = self._price_from_history(history)
        if currency is None and fast_info_dict:
            currency = fast_info_dict.get("currency")  # type: ignore[attr-defined]
        return price, currency

    @staticmethod
    def _price_from_history(history) -> Optional[float]:
        if history is None:
            return None
        close = getattr(history, "Close", None)
        if close is None:
            return None
        try:
            close = close.dropna()
        except Exception:
            return None
        if len(close) == 0:
            return None
        try:
            return float(close.iloc[-1])
        except (ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _safe_float(value: Optional[float]) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
