"""Market data helpers backed by Yahoo Finance."""

from __future__ import annotations

from typing import Any

import yfinance as yf


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must not be empty")
    return normalized


def _as_positive_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        price = float(value)
    except (TypeError, ValueError):
        return None

    if price <= 0:
        return None
    return price


def _price_from_fast_info(ticker: yf.Ticker) -> float | None:
    fast_info = ticker.fast_info
    for key in ("last_price", "regular_market_price", "previous_close"):
        try:
            price = _as_positive_float(fast_info.get(key))
        except Exception:
            price = None
        if price is not None:
            return price
    return None


def _price_from_recent_history(ticker: yf.Ticker) -> float | None:
    history = ticker.history(period="5d", interval="1d", auto_adjust=False)
    if history.empty or "Close" not in history:
        return None

    close_prices = history["Close"].dropna()
    if close_prices.empty:
        return None

    return _as_positive_float(close_prices.iloc[-1])


def get_share_price(symbol: str) -> float:
    """Return the latest available share price for a ticker symbol."""

    normalized_symbol = _normalize_symbol(symbol)
    ticker = yf.Ticker(normalized_symbol)

    price = _price_from_fast_info(ticker)
    if price is not None:
        return price

    price = _price_from_recent_history(ticker)
    if price is not None:
        return price

    raise ValueError(f"No market price available for symbol: {normalized_symbol}")
