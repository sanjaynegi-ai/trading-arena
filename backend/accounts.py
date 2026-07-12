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
    """A single executed trade stored inside an account.

    Transactions capture the immutable details of an action that changed
    holdings: the ticker symbol, number of shares, execution price after spread,
    trade type, human/agent rationale, and UTC timestamp. Account methods append
    these records when shares are bought or sold so later reports can explain how
    the account reached its current state.
    """

    symbol: str
    quantity: float
    price: float
    type: str
    rationale: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Account(BaseModel):
    """Persistent trading account state for one arena participant.

    The account model owns cash balance, strategy text, current share holdings,
    executed transactions, and a time series of portfolio values. It is a
    Pydantic model so it can be validated from dictionaries read from SQLite and
    serialized back to JSON-compatible data when saved.

    Methods on this class intentionally combine domain state changes with
    persistence: when an operation mutates the account, it saves the updated
    model through `backend.database.write_account`. Trading methods also write
    account logs so the dashboard or API can show recent activity.
    """

    name: str
    balance: float = INITIAL_BALANCE
    strategy: str = ""
    holdings: dict[str, float] = Field(default_factory=dict)
    transactions: list[Transaction] = Field(default_factory=list)
    portfolio_values: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def get(cls, name: str) -> "Account":
        """Load an account by name, creating a clean account if needed.

        Names are normalized to lowercase before storage lookup. If the account
        already exists in SQLite, its JSON payload is validated into an
        `Account`. If no row exists, a new account starts with
        `INITIAL_BALANCE`, empty strategy, empty holdings, no transactions, and
        no portfolio value history, then is immediately saved.
        """

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
        """Persist the current account snapshot to SQLite.

        This writes the full JSON-compatible account model under the lowercase
        account name. Call this after any direct field mutation that is not
        already handled by a convenience method such as `deposit`, `withdraw`,
        `buy_shares`, or `reset`.
        """

        self.name = _normalize_name(self.name)
        write_account(self.name, self.model_dump(mode="json"))

    def reset(self, strategy: str = "") -> None:
        """Return the account to a clean starting state and save it.

        The reset keeps the same normalized account name, restores cash to
        `INITIAL_BALANCE`, replaces the strategy with the provided string, and
        clears holdings, transactions, and portfolio value history. This is
        useful before starting a new simulation run for the same participant.
        """

        self.name = _normalize_name(self.name)
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_values = []
        self.save()

    def deposit(self, amount: float) -> None:
        """Add positive cash to the account and persist the new balance.

        Raises `ValueError` when the amount is zero or negative. Deposits do not
        create transaction records because they are cash management operations,
        not market trades.
        """

        if amount <= 0:
            raise ValueError("deposit amount must be positive")

        self.balance += amount
        self.save()

    def withdraw(self, amount: float) -> None:
        """Remove cash from the account and persist the new balance.

        The amount must be positive and cannot exceed the current cash balance.
        A failed withdrawal raises `ValueError` and leaves the account unchanged.
        """

        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("withdrawal would make cash balance negative")

        self.balance -= amount
        self.save()

    def buy_shares(self, symbol: str, quantity: float, rationale: str) -> str:
        """Buy shares at the latest market price plus spread.

        The symbol is normalized to uppercase, the quantity must be positive,
        and the account must have enough cash for `price * (1 + SPREAD) *
        quantity`. On success this method subtracts cash, increases holdings,
        records a timestamped buy transaction with the rationale, appends a
        portfolio value point, saves the account, writes a buy log, and returns a
        human-readable prefix followed by the latest JSON report.
        """

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
        """Sell shares at the latest market price minus spread.

        The symbol is normalized to uppercase, the quantity must be positive,
        and the account must hold enough shares. On success this method adds
        cash, decreases or removes the holding, records a timestamped sell
        transaction with the rationale, appends a portfolio value point, saves
        the account, writes a sell log, and returns a human-readable prefix
        followed by the latest JSON report.
        """

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
        """Calculate current total account value using live market prices.

        The returned value is cash balance plus the market value of every current
        holding. Each holding is priced through `backend.market.get_share_price`,
        so this call can raise if a ticker cannot be priced.
        """

        holdings_value = 0.0
        for symbol, quantity in self.holdings.items():
            holdings_value += get_share_price(symbol) * quantity
        return self.balance + holdings_value

    def calculate_profit_loss(self, portfolio_value: float) -> float:
        """Calculate profit or loss relative to the initial starting balance.

        Pass a portfolio value from `calculate_portfolio_value` or another
        trusted valuation source. Positive numbers indicate gains above
        `INITIAL_BALANCE`; negative numbers indicate losses.
        """

        return portfolio_value - INITIAL_BALANCE

    def get_holdings(self) -> dict[str, float]:
        """Return a copy of the current holdings by ticker symbol.

        The copy prevents callers from accidentally mutating account state
        without going through the account methods and persistence flow.
        """

        return dict(self.holdings)

    def list_transactions(self) -> list[dict[str, Any]]:
        """Return all recorded trade transactions as JSON-compatible dicts.

        The list is ordered from oldest to newest because transactions are
        appended as trades occur. Each item includes symbol, quantity, execution
        price, type, rationale, and timestamp.
        """

        return [
            transaction.model_dump(mode="json")
            for transaction in self.transactions
        ]

    def report(self) -> str:
        """Generate, persist, log, and return a JSON account report.

        This method calculates current portfolio value from live prices,
        calculates total profit/loss versus `INITIAL_BALANCE`, appends the value
        to the portfolio time series, saves the account, writes a read/report log
        entry, and returns a JSON string containing balance, holdings,
        transactions, portfolio values, total portfolio value, and total
        profit/loss.
        """

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
        """Return the current strategy text for this account."""

        return self.strategy

    def change_strategy(self, strategy: str) -> None:
        """Replace the account strategy text and persist the change."""

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
