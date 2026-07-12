"""Account models and persistence helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.database import read_account, write_account, write_log
from backend.market import get_share_price


INITIAL_BALANCE = 50000.0
SPREAD = 0.002


class Transaction(BaseModel):
    symbol: str
    quantity: float
    price: float
    type: str
    rationale: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Account(BaseModel):
    name: str
    balance: float = INITIAL_BALANCE
    strategy: str = ""
    holdings: dict[str, float] = Field(default_factory=dict)
    transactions: list[Transaction] = Field(default_factory=list)
    portfolio_values: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def get(cls, name: str) -> "Account":
        normalized_name = _normalize_name(name)
        account_data = read_account(normalized_name)

        if account_data is not None:
            return cls.model_validate(account_data)

        account = cls(
            name=normalized_name,
            balance=INITIAL_BALANCE,
            strategy="",
            holdings={},
            transactions=[],
            portfolio_values=[],
        )
        account.save()
        return account

    def save(self) -> None:
        self.name = _normalize_name(self.name)
        write_account(self.name, self.model_dump(mode="json"))

    def reset(self, strategy: str = "") -> None:
        self.name = _normalize_name(self.name)
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_values = []
        self.save()

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("deposit amount must be positive")

        self.balance += amount
        self.save()

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("withdrawal would make cash balance negative")

        self.balance -= amount
        self.save()

    def buy_shares(self, symbol: str, quantity: float, rationale: str) -> str:
        normalized_symbol = _normalize_symbol(symbol)
        _validate_quantity(quantity)

        market_price = get_share_price(normalized_symbol)
        execution_price = market_price * (1 + SPREAD)
        total_cost = execution_price * quantity
        if total_cost > self.balance:
            raise ValueError("insufficient cash to buy shares")

        self.balance -= total_cost
        self.holdings[normalized_symbol] = (
            self.holdings.get(normalized_symbol, 0.0) + quantity
        )
        self.transactions.append(
            Transaction(
                symbol=normalized_symbol,
                quantity=quantity,
                price=execution_price,
                type="buy",
                rationale=rationale,
            )
        )

        report = self._record_portfolio_value({normalized_symbol: market_price})
        self.save()
        message = (
            f"Bought {quantity:g} shares of {normalized_symbol} at "
            f"{execution_price:.2f}. Rationale: {rationale}"
        )
        write_log(self.name, "buy", message)
        return _format_trade_response(message, report)

    def sell_shares(self, symbol: str, quantity: float, rationale: str) -> str:
        normalized_symbol = _normalize_symbol(symbol)
        _validate_quantity(quantity)

        shares_owned = self.holdings.get(normalized_symbol, 0.0)
        if quantity > shares_owned:
            raise ValueError("insufficient holdings to sell shares")

        market_price = get_share_price(normalized_symbol)
        execution_price = market_price * (1 - SPREAD)
        proceeds = execution_price * quantity

        self.balance += proceeds
        remaining_shares = shares_owned - quantity
        if remaining_shares <= 0:
            self.holdings.pop(normalized_symbol, None)
        else:
            self.holdings[normalized_symbol] = remaining_shares

        self.transactions.append(
            Transaction(
                symbol=normalized_symbol,
                quantity=quantity,
                price=execution_price,
                type="sell",
                rationale=rationale,
            )
        )

        report = self._record_portfolio_value({normalized_symbol: market_price})
        self.save()
        message = (
            f"Sold {quantity:g} shares of {normalized_symbol} at "
            f"{execution_price:.2f}. Rationale: {rationale}"
        )
        write_log(self.name, "sell", message)
        return _format_trade_response(message, report)

    def calculate_portfolio_value(self) -> float:
        holdings_value = 0.0
        for symbol, quantity in self.holdings.items():
            holdings_value += get_share_price(symbol) * quantity
        return self.balance + holdings_value

    def calculate_profit_loss(self, portfolio_value: float) -> float:
        return portfolio_value - INITIAL_BALANCE

    def get_holdings(self) -> dict[str, float]:
        return dict(self.holdings)

    def list_transactions(self) -> list[dict[str, Any]]:
        return [
            transaction.model_dump(mode="json")
            for transaction in self.transactions
        ]

    def report(self) -> str:
        portfolio_value = self.calculate_portfolio_value()
        profit_loss = self.calculate_profit_loss(portfolio_value)
        timestamp = datetime.now(timezone.utc).isoformat()

        self.portfolio_values.append(
            {
                "timestamp": timestamp,
                "value": portfolio_value,
            }
        )
        self.save()
        write_log(self.name, "report", "Read account report")

        return json.dumps(
            {
                "timestamp": timestamp,
                "name": self.name,
                "balance": self.balance,
                "holdings": self.get_holdings(),
                "transactions": self.list_transactions(),
                "portfolio_values": self.portfolio_values,
                "total_portfolio_value": portfolio_value,
                "total_profit_loss": profit_loss,
            },
            sort_keys=True,
        )

    def get_strategy(self) -> str:
        return self.strategy

    def change_strategy(self, strategy: str) -> None:
        self.strategy = strategy
        self.save()

    def _record_portfolio_value(
        self, price_overrides: dict[str, float] | None = None
    ) -> dict[str, Any]:
        report = self._build_report(price_overrides)
        self.portfolio_values.append(
            {
                "timestamp": report["timestamp"],
                "value": report["portfolio_value"],
            }
        )
        return report

    def _build_report(
        self, price_overrides: dict[str, float] | None = None
    ) -> dict[str, Any]:
        prices = price_overrides or {}
        holdings_value = 0.0

        for symbol, quantity in self.holdings.items():
            price = prices.get(symbol)
            if price is None:
                price = get_share_price(symbol)
            holdings_value += price * quantity

        portfolio_value = self.balance + holdings_value
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "name": self.name,
            "balance": self.balance,
            "holdings": self.holdings,
            "transactions": [
                transaction.model_dump(mode="json")
                for transaction in self.transactions
            ],
            "portfolio_value": portfolio_value,
        }


def _normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("name must not be empty")
    return normalized


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    return normalized


def _validate_quantity(quantity: float) -> None:
    if quantity <= 0:
        raise ValueError("quantity must be positive")


def _format_trade_response(prefix: str, report: dict[str, Any]) -> str:
    return f"{prefix}\n{json.dumps(report, sort_keys=True)}"
