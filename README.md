# Trading Arena

Trading Arena is an autonomous trading simulation where multiple AI traders
manage separate accounts, research the market, buy and sell shares, and compete
on a shared leaderboard.

The project combines:

- AI trader agents
- a nested researcher agent
- local and external MCP tool servers
- a trading account backend
- SQLite persistence
- a Gradio dashboard
- a read-only FastAPI API

Account state, holdings, transactions, portfolio value, P&L, and activity logs
are stored locally in `accounts.db`.

## Quick Start

Install dependencies:

```powershell
uv sync
```

Create `.env` from `.env.example`, then add the keys and scheduler settings you
need. For a normal OpenAI run with researcher search:

```text
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
RUN_EVERY_N_MINUTES=15
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
SCHEDULER_TIME_WINDOW=us_or_india_office
```

Reset all trader accounts:

```powershell
uv run -m backend.reset
```

Start the full local stack:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1
```

Open:

```text
Dashboard: http://127.0.0.1:7860
API:       http://127.0.0.1:8000
API docs:  http://127.0.0.1:8000/docs
```

Stop the stack:

```powershell
powershell -ExecutionPolicy Bypass -File script\stop.ps1
```

For more run modes, see [docs/running.md](docs/running.md).

## What Happens On Each Cycle

Each trader starts with `INITIAL_BALANCE = 50000.0`, a strategy from
`backend/roster.py`, empty holdings, and no transactions.

On each scheduler cycle:

```text
Scheduler checks configured time window
  -> Trader opens account and market MCP tools
  -> Trader opens researcher MCP tools
  -> Trader reads account state and strategy
  -> Trader may ask Researcher for market ideas/news
  -> Trader may use Yahoo Finance MCP tools
  -> LLM chooses a ticker and action
  -> Account tool tries to buy/sell
  -> Account backend enforces guardrails and persists state
  -> Traces and activity logs appear in dashboard/API
```

The scheduler alternates each trader between new-opportunity trading cycles and
existing-holding rebalance cycles.

## Main Components

- `backend/trading_arena.py`: scheduler and trader factory
- `backend/roster.py`: trader profiles, strategies, and model mapping
- `backend/traders.py`: default trader and researcher agent construction
- `backend/mcp_servers.py`: MCP server bundles for traders and researchers
- `backend/accounts.py`: account model, trades, holdings, P&L
- `backend/accounts_server.py`: accounts MCP server
- `backend/market.py`: Yahoo Finance price helper
- `backend/market_server.py`: local market MCP server
- `backend/database.py`: SQLite persistence helpers
- `dashboard/ui.py`: Gradio dashboard UI
- `backend/api.py`: read-only FastAPI API

See [docs/architecture.md](docs/architecture.md) for component details and
Mermaid diagrams.

## MCP Server Summary

Trader MCP servers:

- accounts server: executes account reads/actions through
  `backend.accounts_server`
- Yahoo Finance MCP server: helps traders inspect market data before deciding

Researcher MCP servers:

- fetch: reads specific web pages
- Tavily search: discovers recent market news and context
- memory: stores per-trader research notes

Market tools support trader decisions. Account tools execute buys/sells and
enforce account guardrails.

See [docs/mcp_servers.md](docs/mcp_servers.md) for exact wiring and code
locations.

## Configuration Summary

Environment variables are loaded from `.env`.

Common settings:

- `OPENAI_API_KEY`: required for standard OpenAI model runs
- `TAVILY_API_KEY`: required for default researcher web search
- `RUN_EVERY_N_MINUTES`: scheduler interval, default `15`
- `SCHEDULER_TIME_WINDOW`: `us_market`, `us_office`, `india_office`,
  `us_or_india_office`, or `always`
- `RUN_EVEN_WHEN_MARKET_IS_CLOSED`: legacy override to run every tick
- `USE_MANY_MODELS`: map traders positionally onto `MANY_MODELS`

For all settings and examples, see
[docs/configuration.md](docs/configuration.md).

## Scheduler Time Windows

The scheduler only runs traders inside the configured time window unless
`RUN_EVEN_WHEN_MARKET_IS_CLOSED=true` or `SCHEDULER_TIME_WINDOW=always`.

Useful values:

- `us_market`: Monday-Friday, 9:30 AM-4:00 PM New York time
- `us_office`: Monday-Friday, 9:00 AM-5:00 PM New York time
- `india_office`: Monday-Friday, 9:00 AM-5:00 PM India time
- `us_or_india_office`: runs when either office-hours window is open
- `always`: runs on every scheduler tick

For immediate local testing, set:

```text
SCHEDULER_TIME_WINDOW=always
```

## Ticker Selection

The project does not define a hardcoded tradable stock list such as `AAPL`,
`MSFT`, `NVDA`, `TSLA`, `GOOGL`, `META`, or `AMD`. Traders choose symbols at run
time:

```text
Trader prompt says: look for opportunities
  -> Trader may ask Researcher for market ideas/news
  -> Trader may use Yahoo Finance MCP tools
  -> LLM chooses a ticker
  -> Account tool tries to buy/sell that ticker
```

The account backend accepts the chosen symbol, normalizes it, and asks Yahoo
Finance for a current price through `backend.market.get_share_price(symbol)`.
If Yahoo Finance can return a usable positive price and account guardrails pass,
the trade can execute.

## Running Components

Run components independently:

```powershell
uv run python app.py
uv run uvicorn backend.api:app --port 8000
uv run -m backend.trading_arena
uv run -m backend.accounts_server
uv run -m backend.market_server
```

Start everything together:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1
```

Runtime PID files and logs are written to `.run/`.

See [docs/running.md](docs/running.md) for all run and stop commands.

## Dashboard And API

The dashboard shows:

- leaderboard ranked by portfolio value
- cash, portfolio value, P&L, and P&L percentage
- holdings
- recent transactions
- recent activity logs

The read-only API exposes:

- `GET /api/traders`
- `GET /api/market`
- `GET /api/traders/{name}`
- `GET /api/traders/{name}/logs`

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
|   |-- market_server.py           # Local market MCP server
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
|   |-- architecture.md            # Components, diagrams, and flow
|   |-- configuration.md           # Environment variables and scheduler windows
|   |-- developer_notes.md         # Developer appendix
|   |-- how_to_participate.md      # Add/customize a trader
|   |-- mcp_servers.md             # MCP server wiring
|   |-- requirements.md            # Account-system requirements
|   `-- running.md                 # Running components and scripts
`-- accounts.db                    # Local SQLite state, created at runtime
```

## Documentation Map

- [docs/architecture.md](docs/architecture.md): project purpose, components,
  diagrams, cycle flow, and trace/log flow
- [docs/mcp_servers.md](docs/mcp_servers.md): MCP servers, responsibilities,
  and registration code paths
- [docs/configuration.md](docs/configuration.md): `.env` settings, model
  routing, scheduler windows, and runtime files
- [docs/running.md](docs/running.md): independent component commands, start
  scripts, stop scripts, and troubleshooting checks
- [docs/how_to_participate.md](docs/how_to_participate.md): add a learner,
  customize a trader, or customize a researcher
- [docs/requirements.md](docs/requirements.md): account-system requirements and
  current implementation notes
- [docs/developer_notes.md](docs/developer_notes.md): lower-level runtime notes
- [PLAN.md](PLAN.md): original project build plan
- [AGENTS.md](AGENTS.md): role constraints and project working agreement
