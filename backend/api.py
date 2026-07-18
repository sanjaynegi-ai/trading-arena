from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from backend import market
from backend.accounts import Account, INITIAL_BALANCE
from backend.database import read_log
from backend.trading_arena import is_market_open, lastnames, model_names, names


LOG_COLORS = {
    "trace": "#87CEEB",
    "agent": "#00dddd",
    "function": "#00dd00",
    "mcp_tools": "#66bbff",
    "generation": "#dddd00",
    "response": "#aa00dd",
    "buy": "#00aa66",
    "sell": "#dd7700",
    "report": "#888888",
    "account": "#dd0000",
}
DEFAULT_LOG_COLOR = "#87CEEB"


app = FastAPI(title="Trading Arena")

roster = [
    {"name": name, "lastname": lastname, "model_name": model_name}
    for name, lastname, model_name in zip(names, lastnames, model_names)
]
roster_by_name = {trader["name"].lower(): trader for trader in roster}


def _require_trader(name: str) -> dict[str, str]:
    trader = roster_by_name.get(name.lower())
    if trader is None:
        raise HTTPException(status_code=404, detail=f"Unknown trader: {name}")
    return trader


def _average_cost_by_symbol(account: Account) -> dict[str, float]:
    lots: dict[str, dict[str, float]] = {}

    for transaction in account.transactions:
        symbol = transaction.symbol
        lot = lots.setdefault(symbol, {"quantity": 0.0, "cost": 0.0})

        if transaction.type == "buy":
            lot["quantity"] += transaction.quantity
            lot["cost"] += transaction.quantity * transaction.price
        elif transaction.type == "sell" and lot["quantity"] > 0:
            average_cost = lot["cost"] / lot["quantity"]
            sold_quantity = min(transaction.quantity, lot["quantity"])
            lot["quantity"] -= sold_quantity
            lot["cost"] -= sold_quantity * average_cost

    return {
        symbol: lot["cost"] / lot["quantity"]
        for symbol, lot in lots.items()
        if lot["quantity"] > 0
    }


def _holdings_detail(account: Account) -> list[dict[str, float | str]]:
    average_costs = _average_cost_by_symbol(account)
    holdings = []

    for symbol, quantity in account.get_holdings().items():
        current_price = market.get_share_price(symbol)
        average_cost = average_costs.get(symbol, 0.0)
        market_value = current_price * quantity
        unrealized_pnl = (current_price - average_cost) * quantity
        holdings.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "current_price": current_price,
                "average_cost": average_cost,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
            }
        )

    return holdings


@app.get("/api/traders")
def get_traders() -> list[dict[str, str]]:
    """Return read-only roster metadata for all traders."""

    return roster


@app.get("/api/market")
def get_market() -> dict[str, bool | str]:
    """Return read-only market metadata."""

    return {
        "source": "yahoo_finance",
        "is_market_open": is_market_open(),
    }


@app.get("/api/traders/{name}")
def get_trader(name: str) -> dict[str, Any]:
    """Return read-only account detail for one trader."""

    trader = _require_trader(name)
    account = Account.get(trader["name"])
    holdings = _holdings_detail(account)
    holdings_value = sum(float(holding["market_value"]) for holding in holdings)
    total_portfolio_value = account.balance + holdings_value
    total_pnl = total_portfolio_value - INITIAL_BALANCE

    return {
        "name": trader["name"],
        "lastname": trader["lastname"],
        "model_name": trader["model_name"],
        "balance": account.balance,
        "strategy": account.strategy,
        "holdings": holdings,
        "transactions": account.list_transactions(),
        "time_series": account.portfolio_values,
        "total_portfolio_value": total_portfolio_value,
        "total_pnl": total_pnl,
    }


@app.get("/api/traders/{name}/logs")
def get_trader_logs(name: str, last_n: int = 13) -> list[dict[str, Any]]:
    """Return recent read-only log rows for one trader."""

    trader = _require_trader(name)
    rows = read_log(trader["name"], last_n)
    return [
        {
            **row,
            "color": LOG_COLORS.get(row["type"], DEFAULT_LOG_COLOR),
        }
        for row in rows
    ]
