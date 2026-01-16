"""Test symbol search functionality."""

from __future__ import annotations


from portfolio_mcp.yahoo import search_symbols


class TestSymbolSearch:
    """Test yfinance-backed symbol search."""

    def test_search_basic(self) -> None:
        """Test basic symbol search."""
        results = search_symbols("AAPL", quotes_count=5)
        assert isinstance(results, list)
        assert len(results) > 0
        assert "symbol" in results[0]

    def test_search_multiple_results(self) -> None:
        """Test search returns multiple results."""
        results = search_symbols("Apple", quotes_count=10)
        assert isinstance(results, list)
        assert len(results) > 1

    def test_search_no_results(self) -> None:
        """Test search with no results."""
        results = search_symbols("INVALIDTICKERXYZ123", quotes_count=5)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_fields(self) -> None:
        """Test search result has expected fields."""
        results = search_symbols("AAPL", quotes_count=1)
        assert len(results) > 0
        result = results[0]
        assert "symbol" in result
        assert "shortName" in result
        assert "longName" in result
        assert "exchange" in result
        assert "quoteType" in result

    def test_search_limit(self) -> None:
        """Test search respects limit parameter."""
        results = search_symbols("AAPL", quotes_count=3)
        assert len(results) <= 3
