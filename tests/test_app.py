"""Test portfolio app functionality."""

from __future__ import annotations

import pytest

from app import PortfolioApp


class TestPortfolioApp:
    """Test PortfolioApp core functionality."""

    @pytest.mark.asyncio
    async def test_list_portfolios(self, app: PortfolioApp) -> None:
        """Test listing portfolios."""
        portfolios = app.list_portfolios()
        assert len(portfolios) == 3  # all + cn-growth + hk-tech
        assert portfolios[0]["id"] == "all"
        assert portfolios[0]["name"] == "All Portfolios"
        assert portfolios[1]["id"] == "cn-growth"
        assert portfolios[2]["id"] == "hk-tech"

    @pytest.mark.asyncio
    async def test_get_summary_all(self, app: PortfolioApp) -> None:
        """Test getting summary for all portfolios."""
        summary = await app.summary()
        assert summary.portfolio_id == "all"
        assert summary.portfolio_name == "All Portfolios"
        assert summary.holding_count == 2
        assert summary.total_book > 0
        assert summary.total_market >= 0
        assert len(summary.symbols) == 2

    @pytest.mark.asyncio
    async def test_get_summary_portfolio(self, app: PortfolioApp) -> None:
        """Test getting summary for a specific portfolio."""
        summary = await app.summary("cn-growth")
        assert summary.portfolio_id == "cn-growth"
        assert summary.portfolio_name == "A股成长"
        assert summary.holding_count == 1
        assert summary.total_book > 0

    @pytest.mark.asyncio
    async def test_get_snapshots_all(self, app: PortfolioApp) -> None:
        """Test getting snapshots for all portfolios."""
        snapshots = await app.snapshots()
        assert len(snapshots) == 2
        assert all(s.holding.symbol is not None for s in snapshots)

    @pytest.mark.asyncio
    async def test_get_snapshots_portfolio(self, app: PortfolioApp) -> None:
        """Test getting snapshots for a specific portfolio."""
        snapshots = await app.snapshots("cn-growth")
        assert len(snapshots) == 1
        assert snapshots[0].holding.symbol == "600519.SS"

    @pytest.mark.asyncio
    async def test_get_snapshots_with_symbol(self, app: PortfolioApp) -> None:
        """Test getting snapshots filtered by symbol."""
        snapshots = await app.snapshots(symbol="600519.SS")
        assert len(snapshots) == 1
        assert snapshots[0].holding.symbol == "600519.SS"

    @pytest.mark.asyncio
    async def test_get_summary_with_symbol(self, app: PortfolioApp) -> None:
        """Test getting summary filtered by symbol."""
        summary = await app.summary(symbol="600519.SS")
        assert summary.portfolio_id == "all"
        assert summary.holding_count == 1
        assert summary.symbols == ["600519.SS"]

    @pytest.mark.asyncio
    async def test_refresh_prices(self, app: PortfolioApp) -> None:
        """Test refreshing prices."""
        quotes = await app.refresh_prices()
        assert len(quotes) == 2
        assert "600519.SS" in quotes
        assert "0700.HK" in quotes
        assert all(q.price > 0 for q in quotes.values())

    @pytest.mark.asyncio
    async def test_reload_portfolio(self, app: PortfolioApp) -> None:
        """Test reloading portfolio file."""
        reloaded = await app.reload_portfolio()
        assert len(reloaded.portfolios) == 2
        assert reloaded.base_currency == "CNY"

    @pytest.mark.asyncio
    async def test_search_symbols(self, app: PortfolioApp) -> None:
        """Test symbol search."""
        result = await app.search_symbols("AAPL", None, 5)
        assert "results" in result
        assert isinstance(result["results"], list)
        if len(result["results"]) > 0:
            assert "symbol" in result["results"][0]

    @pytest.mark.asyncio
    async def test_create_portfolio(self, app: PortfolioApp) -> None:
        """Test creating a portfolio."""
        portfolio = await app.create_portfolio("test", "Test Portfolio", "Test notes")
        assert portfolio.id == "test"
        assert portfolio.name == "Test Portfolio"
        assert portfolio.notes == "Test notes"

        # Verify it appears in list
        portfolios = app.list_portfolios()
        portfolio_ids = [p["id"] for p in portfolios]
        assert "test" in portfolio_ids

    @pytest.mark.asyncio
    async def test_update_portfolio(self, app: PortfolioApp) -> None:
        """Test updating a portfolio."""
        # First create
        await app.create_portfolio("update-test", "Original Name", None)

        # Then update
        updated = await app.update_portfolio("update-test", "Updated Name", "Updated notes")
        assert updated.id == "update-test"
        assert updated.name == "Updated Name"
        assert updated.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_delete_portfolio(self, app: PortfolioApp) -> None:
        """Test deleting a portfolio."""
        # First create
        await app.create_portfolio("delete-test", "To Delete", None)

        # Then delete
        deleted = await app.delete_portfolio("delete-test", force=True)
        assert deleted.id == "delete-test"

        # Verify it's gone
        portfolios = app.list_portfolios()
        portfolio_ids = [p["id"] for p in portfolios]
        assert "delete-test" not in portfolio_ids

    @pytest.mark.asyncio
    async def test_add_holding_with_symbol(self, app: PortfolioApp) -> None:
        """Test adding a holding with explicit symbol."""
        # Create a test portfolio
        await app.create_portfolio("holding-test", "Holding Test", None)

        # Add holding
        result = await app.add_holding(
            "holding-test",
            symbol="AAPL",
            quantity=10,
            cost_basis=150.0,
            currency="USD",
            name="Apple Inc.",
            search_query=None,
            search_region=None,
            search_limit=5,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
        )

        assert "holding" in result
        assert result["holding"]["symbol"] == "AAPL"
        assert result["holding"]["quantity"] == 10.0
        assert result["holding"]["name"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_add_holding_requires_name(self, app: PortfolioApp) -> None:
        """Test that adding a holding requires a name."""
        # Create a test portfolio
        await app.create_portfolio("name-test", "Name Test", None)

        with pytest.raises(ValueError, match="name must be provided"):
            await app.add_holding(
                "name-test",
                symbol="AAPL",
                quantity=10,
                cost_basis=150.0,
                currency="USD",
                name=None,
                search_query=None,
                search_region=None,
                search_limit=5,
                broker=None,
                category=None,
                notes=None,
                holding_id=None,
            )

    @pytest.mark.asyncio
    async def test_add_holding_with_search(self, app: PortfolioApp) -> None:
        """Test adding a holding with search query."""
        # Create a test portfolio
        await app.create_portfolio("search-test", "Search Test", None)

        # Add holding via search
        result = await app.add_holding(
            "search-test",
            search_query="Apple",
            quantity=5,
            cost_basis=180.0,
            currency="USD",
            search_limit=5,
            symbol=None,
            name=None,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
            search_region=None,
        )

        assert "holding" in result
        assert result["holding"]["symbol"] is not None
        assert result["holding"]["name"] is not None
        assert "search_matches" in result

    @pytest.mark.asyncio
    async def test_update_holding(self, app: PortfolioApp) -> None:
        """Test updating a holding."""
        # Create portfolio and add holding
        await app.create_portfolio("update-holding-test", "Update Holding Test", None)
        add_result = await app.add_holding(
            "update-holding-test",
            symbol="AAPL",
            quantity=10,
            cost_basis=150.0,
            currency="USD",
            name="Apple Inc.",
            search_query=None,
            search_region=None,
            search_limit=5,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
        )

        # Update holding
        holding_id = add_result["holding"]["id"]
        updated = await app.update_holding(
            "update-holding-test",
            holding_id,
            quantity=20,
            cost_basis=160.0,
            notes=None,
            broker=None,
            category=None,
            name="Microsoft Corp.",
            currency=None,
            symbol="MSFT",
        )

        assert updated["holding"]["quantity"] == 20.0
        assert updated["holding"]["cost_basis"] == 160.0
        assert updated["holding"]["symbol"] == "MSFT"
        assert updated["holding"]["name"] == "Microsoft Corp."

    @pytest.mark.asyncio
    async def test_remove_holding(self, app: PortfolioApp) -> None:
        """Test removing a holding."""
        # Create portfolio and add holding
        await app.create_portfolio("remove-holding-test", "Remove Holding Test", None)
        add_result = await app.add_holding(
            "remove-holding-test",
            symbol="AAPL",
            quantity=10,
            cost_basis=150.0,
            currency="USD",
            name="Apple Inc.",
            search_query=None,
            search_region=None,
            search_limit=5,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
        )

        # Remove holding
        holding_id = add_result["holding"]["id"]
        removed = await app.remove_holding("remove-holding-test", holding_id)

        assert removed["holding"]["symbol"] == "AAPL"

        # Verify it's gone from snapshots
        snapshots = await app.snapshots("remove-holding-test")
        assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_price_cache(self, app: PortfolioApp) -> None:
        """Test that price caching works."""
        quotes1 = await app.price_service.get_quotes(["600519.SS"])
        assert "600519.SS" in quotes1

        quotes2 = await app.price_service.get_quotes(["600519.SS"])
        assert "600519.SS" in quotes2
        assert quotes1["600519.SS"].price == quotes2["600519.SS"].price

    @pytest.mark.asyncio
    async def test_hk_stock_code_normalization(self, app: PortfolioApp) -> None:
        """Test that HK stock codes with leading zeros are normalized."""
        quote1 = await app.price_service.get_quote("09988.HK")
        assert quote1 is not None

        quote2 = await app.price_service.get_quote("9988.HK")
        assert quote2 is not None

    @pytest.mark.asyncio
    async def test_no_auto_refresh_after_operations(self, app: PortfolioApp) -> None:
        """Test that holding operations don't trigger auto refresh."""
        await app.create_portfolio("no-refresh-test", "No Refresh Test", None)
        await app.add_holding(
            "no-refresh-test",
            symbol="AAPL",
            quantity=10,
            cost_basis=150.0,
            currency="USD",
            name="Apple Inc.",
            search_query=None,
            search_region=None,
            search_limit=5,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
        )

        add_result = await app.add_holding(
            "no-refresh-test",
            symbol="MSFT",
            quantity=5,
            cost_basis=200.0,
            currency="USD",
            name="Microsoft",
            search_query=None,
            search_region=None,
            search_limit=5,
            broker=None,
            category=None,
            notes=None,
            holding_id=None,
        )
        holding_id = add_result["holding"]["id"]
        await app.update_holding(
            "no-refresh-test",
            holding_id,
            quantity=15,
            cost_basis=210.0,
            notes=None,
            broker=None,
            category=None,
            name="Microsoft Corp.",
            currency=None,
            symbol=None,
        )

        await app.remove_holding("no-refresh-test", holding_id)
