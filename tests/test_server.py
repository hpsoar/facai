"""Test MCP server functionality."""

from __future__ import annotations

import json

import pytest

from portfolio_mcp.app import PortfolioApp
from portfolio_mcp.server import build_server


class TestMCPServer:
    """Test MCP server tools and resources."""

    @pytest.mark.asyncio
    async def test_server_construction(self, app: PortfolioApp) -> None:
        """Test building the MCP server."""
        server = build_server(app, name="Test Server", version="0.1.0")
        assert server is not None
        assert server.name == "Test Server"

    @pytest.mark.asyncio
    async def test_list_tools(self, app: PortfolioApp) -> None:
        """Test listing available tools."""
        server = build_server(app, name="Test Server", version="0.1.0")
        tools = await server.list_tools()

        expected_tools = [
            "refresh_prices",
            "get_positions",
            "reload_portfolio",
            "get_summary",
            "list_portfolios",
            "create_portfolio",
            "update_portfolio",
            "delete_portfolio",
            "add_holding",
            "remove_holding",
            "update_holding",
            "search_symbols",
        ]

        tool_names = [t.name for t in tools]
        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    @pytest.mark.asyncio
    async def test_list_resources(self, app: PortfolioApp) -> None:
        """Test listing available resources."""
        server = build_server(app, name="Test Server", version="0.1.0")
        resources = await server.list_resources()

        expected_resources = [
            "portfolio://portfolios",
            "portfolio://summary",
            "portfolio://positions",
        ]

        resource_uris = [str(r.uri) for r in resources]
        for expected in expected_resources:
            assert expected in resource_uris, f"Missing resource: {expected}"

    @pytest.mark.asyncio
    async def test_read_portfolios_resource(self, app: PortfolioApp) -> None:
        """Test reading the portfolios resource."""
        server = build_server(app, name="Test Server", version="0.1.0")
        content = await server.read_resource("portfolio://portfolios")

        assert len(content) > 0
        data = json.loads(content[0].content)
        assert "portfolios" in data
        assert len(data["portfolios"]) == 3

    @pytest.mark.asyncio
    async def test_read_summary_resource(self, app: PortfolioApp) -> None:
        """Test reading the summary resource."""
        server = build_server(app, name="Test Server", version="0.1.0")
        content = await server.read_resource("portfolio://summary")

        assert len(content) > 0
        data = json.loads(content[0].content)
        assert data["portfolio_id"] == "all"
        assert "total_market" in data
        assert "total_gain" in data

    @pytest.mark.asyncio
    async def test_read_positions_resource(self, app: PortfolioApp) -> None:
        """Test reading the positions resource."""
        server = build_server(app, name="Test Server", version="0.1.0")
        content = await server.read_resource("portfolio://positions")

        assert len(content) > 0
        data = json.loads(content[0].content)
        assert "positions" in data
        assert len(data["positions"]) == 2

    @pytest.mark.asyncio
    async def test_call_list_portfolios_tool(self, app: PortfolioApp) -> None:
        """Test calling the list_portfolios tool."""
        server = build_server(app, name="Test Server", version="0.1.0")
        result = await server.call_tool("list_portfolios", {})

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_get_summary_tool(self, app: PortfolioApp) -> None:
        """Test calling the get_summary tool."""
        server = build_server(app, name="Test Server", version="0.1.0")
        result = await server.call_tool("get_summary", {})

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_get_positions_tool(self, app: PortfolioApp) -> None:
        """Test calling the get_positions tool."""
        server = build_server(app, name="Test Server", version="0.1.0")
        result = await server.call_tool("get_positions", {})

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_search_symbols_tool(self, app: PortfolioApp) -> None:
        """Test calling the search_symbols tool."""
        server = build_server(app, name="Test Server", version="0.1.0")
        result = await server.call_tool("search_symbols", {"query": "AAPL", "limit": 5})

        assert result is not None
        assert len(result) > 0
