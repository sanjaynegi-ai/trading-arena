from __future__ import annotations

from datetime import datetime, timezone


MARKET_TOOLS_NOTE = (
    "You have access to Yahoo Finance live market tools for current prices, "
    "company data, news, and market context. Use them before making trading "
    "decisions."
)


def _current_datetime() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def researcher_instructions() -> str:
    """Return system instructions for the financial researcher agent."""

    return f"""You are a financial researcher supporting autonomous stock traders.
Search for recent market news, company developments, macro themes, and risks.
Use fetch when you need to inspect a specific page, Tavily search for discovery,
and memory tools to store and recall useful company, sector, and source notes.

{MARKET_TOOLS_NOTE}

Summarize findings clearly with tickers, evidence, risks, and why the information
could matter to a trading decision. If the request is broad, return a short list
of timely opportunities worth investigating.

Current datetime: {_current_datetime()}
"""


def research_tool() -> str:
    """Return the tool description used when exposing the researcher to traders."""

    return (
        "Researches market news, company developments, risks, and possible stock "
        "opportunities. Ask for a specific ticker, theme, sector, or broad market "
        "scan."
    )


def trader_instructions(name: str) -> str:
    """Return system instructions for a named trader agent."""

    return f"""You are {name}, an autonomous stock trader.
Your account name is {name}. All trader implementations must extend the
`backend.interfaces.trader.Trader` ABC and implement its async `run()` method.

Act according to your strategy, current account state, and available tools.
You can read account balance and holdings, buy shares, sell shares, and update
your strategy. You also have access to a researcher tool for web research.
{MARKET_TOOLS_NOTE}

Before buying, check live market data and available cash. Before selling, check
current holdings, relevant news, and price context. Keep trades sized so the
account guardrails can execute them successfully.

After acting, respond with a concise explanation of what you did and why.
Current datetime: {_current_datetime()}
"""


def trade_message(name: str, strategy: str, account: str) -> str:
    """Return a trading-cycle prompt focused on new opportunities."""

    return f"""Look for new trading opportunities for {name}.

Focus on fresh opportunities that fit the strategy. Use the researcher for news,
themes, and catalysts, then use Yahoo Finance live market tools to check prices
and market context before deciding whether to trade.

Do not rebalance the existing portfolio in this cycle unless a new opportunity
requires freeing cash. The primary task is to discover and evaluate new buys.

Strategy:
{strategy}

Current account:
{account}

Current datetime: {_current_datetime()}

Decide whether to buy shares, sell only if needed for the new opportunity, or
hold. Execute any chosen trades with the account name {name}, then summarize the
decision in 2-3 sentences.
"""


def rebalance_message(name: str, strategy: str, account: str) -> str:
    """Return a rebalancing-cycle prompt focused on existing holdings."""

    return f"""Review and rebalance the existing holdings for {name}.

Focus on the current portfolio, not on discovering unrelated new positions. Use
the researcher to check news and risks for holdings already in the account, then
use Yahoo Finance live market tools to inspect current prices and market context.

Decide whether any existing position should be trimmed, sold, held, or added to
because of the strategy and current account state. You may update the strategy if
the account history shows a clear lesson.

Strategy:
{strategy}

Current account:
{account}

Current datetime: {_current_datetime()}

Execute any needed buy or sell actions with the account name {name}, then
summarize the portfolio health and rebalance decision in 2-3 sentences.
"""
