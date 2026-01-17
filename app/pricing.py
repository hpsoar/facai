"""Price fetching utilities with caching."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

import yfinance as yf

from .models import PriceQuote
from .proxy import resolve_proxy
from .yfinance_utils import configure_network

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
        configure_network(self.proxy, self.max_retries)

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
        import traceback
        normalized = symbol.upper()
        
        if normalized.endswith('.HK'):
            normalized = normalized.lstrip('0') if len(normalized) > 5 else normalized
        
        cached = self._cache.get(normalized)
        now = datetime.now(timezone.utc)
        if cached and cached.expires_at > now:
            logger.debug("Cache hit for %s", normalized)
            return cached.quote
        logger.debug("Fetching price for %s\nCaller:\n%s", normalized, "".join(traceback.format_stack()[-50:-1]))
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
                ticker = yf.Ticker(symbol)
                price, currency = self._extract_price_and_currency(ticker)
                if price is not None:
                    break
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "yfinance fetch failed for %s (attempt %s/%s)",
                    symbol,
                    attempt + 1,
                    attempts,
                )
            if attempt < attempts - 1:
                backoff = min(2**attempt, 5)
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

    def _extract_price_and_currency(
        self, ticker: yf.Ticker
    ) -> tuple[Optional[float], Optional[str]]:
        price = None
        currency = None
        history = None
        try:
            history = ticker.history(period="5d", interval="1d", auto_adjust=False, actions=False)
        except Exception as exc:
            logger.debug("yfinance history lookup failed for %s: %s", ticker.ticker, exc)
        price = self._price_from_history(history)
        try:
            metadata = ticker.get_history_metadata()
            if isinstance(metadata, dict):
                currency = metadata.get("currency") or currency
        except Exception as exc:
            logger.debug("yfinance metadata lookup failed for %s: %s", ticker.ticker, exc)
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
