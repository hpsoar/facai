"""MCP client for testing facai MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class FacaiMCPClient:
    """Simple client for testing facai MCP server."""

    def __init__(self, server_path: Optional[str] = None):
        """Initialize client.

        Args:
            server_path: Path to server executable/script. If None, uses the installed package.
        """
        if server_path:
            self._params = StdioServerParameters(
                command="python3",
                args=["-m", "app.__main__"],
            )
        else:
            self._params = StdioServerParameters(
                command="facai-mcp",
                args=[],
            )
        self._session: Optional[ClientSession] = None

    async def connect(self) -> None:
        """Connect to the MCP server."""
        stdio_transport = stdio_client(self._params)
        read, write = stdio_transport
        self._session = ClientSession(read, write)
        await self._session.initialize()
        logger.info("Connected to MCP server")

    async def close(self) -> None:
        """Close the connection."""
        if self._session:
            await self._session.close()
            logger.info("Closed MCP connection")

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources."""
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.list_resources()
        return result.resources if hasattr(result, "resources") else []

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI."""
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.read_resource(uri)
        return result.contents[0].text if result.contents else ""

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.list_tools()
        return result.tools if hasattr(result, "tools") else []

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool by name."""
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.call_tool(name, arguments or {})
        return result.content[0].text if result.content else None

    async def list_portfolios(self) -> Dict[str, Any]:
        """List all portfolios."""
        data = await self.read_resource("portfolio://portfolios")
        return json.loads(data)

    async def get_summary(self, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
        """Get portfolio summary."""
        uri = f"portfolio://summary/{portfolio_id}" if portfolio_id else "portfolio://summary"
        data = await self.read_resource(uri)
        return json.loads(data)

    async def get_positions(self, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
        """Get portfolio positions."""
        uri = f"portfolio://positions/{portfolio_id}" if portfolio_id else "portfolio://positions"
        data = await self.read_resource(uri)
        return json.loads(data)

    async def refresh_prices(self) -> Dict[str, Any]:
        """Refresh prices for all holdings."""
        return await self.call_tool("refresh_prices")

    async def add_holding(self, portfolio_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Add a holding to a portfolio."""
        args = {"portfolio_id": portfolio_id, **kwargs}
        return await self.call_tool("add_holding", args)

    async def search_symbols(
        self, query: str, region: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        """Search for stock symbols."""
        args = {"query": query}
        if region:
            args["region"] = region
        args["limit"] = limit
        return await self.call_tool("search_symbols", args)


async def test_mcp_server():
    """Test the MCP server with common operations."""
    client = FacaiMCPClient()

    try:
        await client.connect()

        print("=" * 60)
        print("Testing Portfolio MCP Server")
        print("=" * 60)
        print()

        print("1. List Resources")
        resources = await client.list_resources()
        for r in resources:
            print(f"   - {r.uri}: {r.name}")
        print()

        print("2. List Tools")
        tools = await client.list_tools()
        for t in tools:
            print(f"   - {t.name}: {t.description}")
        print()

        print("3. List Portfolios")
        portfolios = await client.list_portfolios()
        print(f"   {json.dumps(portfolios, indent=2, ensure_ascii=False)}")
        print()

        print("4. Get Summary")
        summary = await client.get_summary()
        print(f"   {json.dumps(summary, indent=2, ensure_ascii=False)}")
        print()

        print("5. Get Positions")
        positions = await client.get_positions()
        print(f"   Found {len(positions.get('positions', []))} holdings")
        print()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)

    finally:
        await client.close()


def main():
    """Run the test client."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_mcp_server())


if __name__ == "__main__":
    main()
