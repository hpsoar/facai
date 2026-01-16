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

    def test_search_chinese_stocks_by_code(self) -> None:
        """Test searching Chinese A-shares and HK stocks by ticker code.

        IMPORTANT: yfinance search does NOT support Chinese characters.
        Users must use ticker codes (e.g., 600519.SS, 0700.HK) or English names.

        Working search terms:
        - 600519.SS (Kweichow Moutai)
        - 000963.SZ (Huadong Medicine)
        - 0700.HK (Tencent)
        - 3690.HK (Meituan)
        """
        # A-share: 贵州茅台
        results = search_symbols("600519.SS", quotes_count=5)
        assert len(results) > 0
        assert any(r["symbol"] == "600519.SS" for r in results)

        # A-share: 华东医药
        results = search_symbols("000963.SZ", quotes_count=5)
        assert len(results) > 0
        assert any(r["symbol"] == "000963.SZ" for r in results)

        # HK stock: 腾讯控股
        results = search_symbols("0700.HK", quotes_count=5)
        assert len(results) > 0
        assert any(r["symbol"] == "0700.HK" for r in results)

        # HK stock: 美团点评-W
        results = search_symbols("3690.HK", quotes_count=5)
        assert len(results) > 0
        assert any(r["symbol"] == "3690.HK" for r in results)

    def test_search_chinese_stocks_by_english(self) -> None:
        """Test searching Chinese stocks by English company names.

        yfinance supports English company names but NOT Chinese characters.
        Working English search terms:
        - moutai, kweichow (for 贵州茅台)
        - huadong (for 华东医药)
        - tencent (for 腾讯控股)
        - meituan (for 美团点评-W)
        """
        # 贵州茅台 - English name works
        results = search_symbols("moutai", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "600519.SS" for r in results)

        # 贵州茅台 - Alternative English name
        results = search_symbols("kweichow", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "600519.SS" for r in results)

        # 华东医药 - Pinyin works
        results = search_symbols("huadong", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "000963.SZ" for r in results)

        # 腾讯控股 - English name works
        results = search_symbols("tencent", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "0700.HK" for r in results)

        # 美团点评-W - English name works
        results = search_symbols("meituan", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "3690.HK" for r in results)

    def test_search_chinese_characters_not_supported(self) -> None:
        """Test that Chinese character searches return no results.

        IMPORTANT: yfinance search API does NOT support Chinese characters.
        Users must use ticker codes or English names instead.
        """
        # Chinese characters don't work
        results = search_symbols("茅台", quotes_count=10)
        assert len(results) == 0

        results = search_symbols("贵州茅台", quotes_count=10)
        assert len(results) == 0

        results = search_symbols("腾讯", quotes_count=10)
        assert len(results) == 0

        results = search_symbols("阿里巴巴", quotes_count=10)
        assert len(results) == 0

        # Even pinyin without spaces doesn't always work
        results = search_symbols("guizhoumaotai", quotes_count=10)
        assert len(results) == 0

    def test_search_chinese_stocks_numeric_codes(self) -> None:
        """Test searching Chinese stocks by numeric codes without suffix.

        yfinance can find stocks with numeric codes, but results may include
        other matching tickers. Using full codes with suffix (.SS, .SZ, .HK)
        is more precise.
        """
        # 600519 returns Kweichow Moutai among results
        results = search_symbols("600519", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "600519.SS" for r in results)

        # 0700 returns Tencent among results
        results = search_symbols("0700", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "0700.HK" for r in results)

        # 3690 returns Meituan among results
        results = search_symbols("3690", quotes_count=10)
        assert len(results) > 0
        assert any(r["symbol"] == "3690.HK" for r in results)
