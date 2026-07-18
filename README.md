# Trading Arena

Trading Arena is an autonomous trading simulation where four AI traders manage
separate accounts, research the market, buy and sell shares, and compete on a
shared leaderboard. Account state, holdings, transactions, portfolio value, P&L,
and activity logs are stored locally in `accounts.db`.

## Quick Start

Install dependencies and create the local environment:

```powershell
uv sync
```

Create a `.env` file from `.env.example`, then add the API keys you need. For a
normal OpenAI run, set at least:

```powershell
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
```

Reset all trader accounts to their starting balance and configured strategies:

```powershell
uv run -m backend.reset
```

Run the Gradio dashboard:

```powershell
uv run python app.py
```

Or start the local stack with the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1
```

Run the autonomous trading scheduler in a separate terminal:

```powershell
uv run -m backend.trading_arena
```

Optional read-only API:

```powershell
uv run uvicorn backend.api:app --port 8000
```

## What The Project Does

The project combines a trading account backend, AI trader agents, MCP tool
servers, a Gradio dashboard, and a FastAPI read-only API.

Each trader starts with `INITIAL_BALANCE = 50000.0`, a strategy from
`backend/roster.py`, empty holdings, and no transactions. On each scheduler
cycle, traders can inspect their account, research market context, and place
orders through account tools. The scheduler alternates each trader between new
opportunity trades and rebalance checks.

The Gradio dashboard shows:

- a leaderboard ranked by portfolio value
- portfolio value and P&L for each trader
- holdings
- recent transactions
- recent activity logs

## Main Commands

Run backend smoke check:

```powershell
uv run python backend_smoke_check.py
```

Run the accounts MCP server:

```powershell
uv run -m backend.accounts_server
```

Run the market MCP server:

```powershell
uv run -m backend.market_server
```

Reset all roster accounts:

```powershell
uv run -m backend.reset
```

Start the long-running arena scheduler:

```powershell
uv run -m backend.trading_arena
```

Start the dashboard:

```powershell
uv run python app.py
```

## Start And Stop Scripts

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1
powershell -ExecutionPolicy Bypass -File script\stop.ps1
```

macOS/Linux:

```bash
./script/start.sh
./script/stop.sh
```

By default, the scripts start or stop the dashboard, API, and scheduler. Runtime
PID files and logs are written to `.run/`.

Useful Windows options:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1 -NoApi -NoScheduler
powershell -ExecutionPolicy Bypass -File script\stop.ps1 -DashboardOnly
```

Useful macOS/Linux options:

```bash
./script/start.sh --no-api --no-scheduler
./script/stop.sh --dashboard-only
```

## Project Structure

```text
.
|-- app.py                         # Gradio dashboard launcher
|-- backend/
|   |-- accounts.py                # Account model, trades, holdings, P&L
|   |-- accounts_client.py         # MCP client helpers for account resources
|   |-- accounts_server.py         # Accounts MCP server
|   |-- api.py                     # Read-only FastAPI API
|   |-- database.py                # SQLite account/log persistence
|   |-- market.py                  # Yahoo Finance price helper
|   |-- market_server.py           # Market MCP server
|   |-- mcp_servers.py             # MCP server bundles for traders/researchers
|   |-- reset.py                   # Reset roster accounts
|   |-- roster.py                  # Trader profiles, strategies, model mapping
|   |-- templates.py               # Trader/researcher prompt templates
|   |-- tracers.py                 # Agents SDK trace logging
|   |-- traders.py                 # Default autonomous trader implementation
|   `-- trading_arena.py           # Scheduler and trader factory
|-- dashboard/
|   |-- ui.py                      # Gradio UI and leaderboard
|   `-- util.py                    # Dashboard CSS
|-- script/
|   |-- start.ps1                  # Windows start helper
|   |-- stop.ps1                   # Windows stop helper
|   |-- start.sh                   # macOS/Linux start helper
|   `-- stop.sh                    # macOS/Linux stop helper
|-- docs/
|   |-- developer_notes.md         # Runtime and MCP notes
|   |-- design.md                  # Architecture sequence diagram
|   |-- how_to_participate.md      # Add/customize a trader
|   `-- requirements.md            # Account-system requirements
`-- accounts.db                    # Local SQLite state, created at runtime
```

## Configuration

Environment variables are loaded from `.env`.

- `OPENAI_API_KEY`: Required for standard OpenAI model runs.
- `TAVILY_API_KEY`: Used by the Tavily MCP search server for researcher web
  search.
- `RUN_EVERY_N_MINUTES`: Scheduler interval. Defaults to `60`.
- `RUN_EVEN_WHEN_MARKET_IS_CLOSED`: Set to `true` to run outside regular US
  market hours. Defaults to `false`.
- `USE_MANY_MODELS`: Set to `true` to map traders onto `MANY_MODELS` in
  `backend/roster.py`. Defaults to `false`.
- `OPENROUTER_API_KEY`: Required when a selected model name contains `/`.
- `DEEPSEEK_API_KEY`: Required when a selected model name contains `deepseek`.
- `GROK_API_KEY`: Required when a selected model name contains `grok`.
- `GOOGLE_API_KEY`: Required when a selected model name contains `gemini`.

See [docs/developer_notes.md](docs/developer_notes.md) for more runtime notes.

## Traders And Models

The roster lives in `backend/roster.py`. Each `TraderProfile` has:

- `name`
- `lastname`
- `strategy`
- `model_name`

By default, all traders use `DEFAULT_MODEL`. If `USE_MANY_MODELS=true`, the
scheduler maps traders positionally to `MANY_MODELS`.

For full participation instructions, including adding a new competitor, custom
trader workflows, custom researchers, and MCP tool changes, see
[docs/how_to_participate.md](docs/how_to_participate.md).

## Account Rules

The account system supports:

- deposits and withdrawals
- buying and selling shares
- portfolio valuation
- profit/loss reporting
- current holdings
- transaction history

It enforces:

- no withdrawing more cash than the account holds
- no buying more shares than the account can afford
- no selling shares the account does not hold

The original account requirements are in
[docs/requirements.md](docs/requirements.md).

## Market Data

`backend.market.get_share_price(symbol)` uses Yahoo Finance through `yfinance`.
The helper normalizes ticker symbols, tries fast price data first, then falls
back to recent historical close prices. It raises `ValueError` when a price is
not available.

The trader MCP tool bundle also includes Yahoo Finance through `uvx
mcp-yahoo-finance`.

## Dashboard

The dashboard is built with Gradio in `dashboard/ui.py` and launched from
`app.py`.

It creates one local dashboard `Trader` wrapper per roster profile, then renders:

- a summary leaderboard above the trader panels
- one detail column per trader
- 120-second refresh timers for account data and leaderboard data
- 0.5-second refresh timers for logs

The leaderboard uses each account's:

- `calculate_portfolio_value()`
- `calculate_profit_loss(portfolio_value)`

P&L percentage is calculated as:

```text
pnl / INITIAL_BALANCE
```

## API

The FastAPI app in `backend/api.py` exposes read-only dashboard-friendly
endpoints:

- `GET /api/traders`
- `GET /api/market`
- `GET /api/traders/{name}`
- `GET /api/traders/{name}/logs`

Run it with:

```powershell
uv run uvicorn backend.api:app --port 8000
```

## Persistence

Account snapshots and logs are stored in local SQLite at `accounts.db`.

`backend/database.py` owns the storage helpers:

- `write_account(...)`
- `read_account(...)`
- `write_log(...)`
- `read_log(...)`

Researcher memory, when used, is stored separately under `memory/` through the
MCP memory server.

## Useful References

- [docs/requirements.md](docs/requirements.md): backend account requirements
- [docs/design.md](docs/design.md): sequence diagram and high-level flow
- [docs/developer_notes.md](docs/developer_notes.md): MCP and runtime notes
- [docs/how_to_participate.md](docs/how_to_participate.md): adding or
  customizing traders
- [PLAN.md](PLAN.md): original project build plan
- [AGENTS.md](AGENTS.md): role constraints and project working agreement
