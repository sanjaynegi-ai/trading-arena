"""MCP stdio server for market-data lookup tools.

This module is designed to run as its own subprocess, typically with
`uv run -m backend.market_server`. It exposes a small FastMCP surface that lets
LLM agents request a current share price without importing the market provider
directly. Pricing behavior, ticker normalization, and provider errors are owned
by `backend.market.get_share_price`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.market import get_share_price

mcp = FastMCP("market_server")


@mcp.tool()
async def lookup_share_price(symbol: str) -> float:
    """Return the latest available share price for a ticker symbol.

    Args:
        symbol: Stock ticker symbol to price, such as "AAPL" or "TSLA".

    Returns:
        A positive float price from the configured market data provider.

    Raises:
        ValueError: If the symbol is empty or no usable market price is found.
    """

    return get_share_price(symbol)


if __name__ == "__main__":
    mcp.run(transport="stdio")
