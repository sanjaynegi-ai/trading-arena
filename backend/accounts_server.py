from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.accounts import Account


mcp = FastMCP("accounts_server")


@mcp.tool()
async def get_balance(name: str) -> float:
    """Get the cash balance for an account."""

    return Account.get(name).balance


@mcp.tool()
async def get_holdings(name: str) -> dict[str, float]:
    """Get current share holdings for an account."""

    return Account.get(name).get_holdings()


@mcp.tool()
async def buy_shares(
    name: str,
    symbol: str,
    quantity: float,
    rationale: str,
) -> str:
    """Buy shares for an account and return the updated account report."""

    return Account.get(name).buy_shares(symbol, quantity, rationale)


@mcp.tool()
async def sell_shares(
    name: str,
    symbol: str,
    quantity: float,
    rationale: str,
) -> str:
    """Sell shares for an account and return the updated account report."""

    return Account.get(name).sell_shares(symbol, quantity, rationale)


@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    """Change the strategy text for an account."""

    account = Account.get(name)
    account.change_strategy(strategy)
    return f"Updated strategy for {account.name}."


@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    """Read the full account report resource for an account."""

    return Account.get(name).report()


@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    """Read the current strategy text resource for an account."""

    return Account.get(name).get_strategy()


if __name__ == "__main__":
    mcp.run(transport="stdio")
