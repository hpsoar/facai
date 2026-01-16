"""Yahoo Finance helper utilities."""

from __future__ import annotations

from typing import Optional

import httpx

SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
    "Connection": "keep-alive",
}


def search_symbols(
    query: str,
    *,
    region: Optional[str] = None,
    quotes_count: int = 5,
    proxy: Optional[str] = None,
    timeout: float = 10.0,
) -> list[dict]:
    params = {
        "q": query,
        "quotesCount": max(1, quotes_count),
        "newsCount": 0,
        "enableNavLinks": False,
        "enableEnhancedTrivialQuery": True,
    }
    if region:
        params["region"] = region
    client_kwargs = {"timeout": timeout, "headers": DEFAULT_HEADERS}
    if proxy:
        client_kwargs["proxy"] = proxy
    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - network failures
        raise RuntimeError(f"Yahoo search failed: {exc}") from exc
    quotes = payload.get("quotes") or []
    results: list[dict] = []
    for quote in quotes:
        results.append(
            {
                "symbol": quote.get("symbol"),
                "shortName": quote.get("shortname") or quote.get("shortName"),
                "longName": quote.get("longname") or quote.get("longName"),
                "exchange": quote.get("exchange"),
                "quoteType": quote.get("quoteType"),
            }
        )
    return results
