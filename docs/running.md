# Running The Project

All commands should be run from the project root.

## Install

Install dependencies and create the local environment:

```powershell
uv sync
```

Create `.env` from `.env.example`, then add the keys and scheduler settings you
need. See [configuration.md](configuration.md).

## Reset Accounts

Reset all roster accounts to their configured starting strategies:

```powershell
uv run -m backend.reset
```

This creates or updates local account rows in `accounts.db`.

## Run Components Independently

### Dashboard

```powershell
uv run python app.py
```

Default URL:

```text
http://127.0.0.1:7860
```

### API

```powershell
uv run uvicorn backend.api:app --port 8000
```

Default URL:

```text
http://127.0.0.1:8000
```

Interactive FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

- `GET /api/traders`
- `GET /api/market`
- `GET /api/traders/{name}`
- `GET /api/traders/{name}/logs`

### Scheduler

```powershell
uv run -m backend.trading_arena
```

The scheduler is long-running. It creates all rostered traders and runs them on
the configured interval when the configured time window is open.

### Accounts MCP Server

```powershell
uv run -m backend.accounts_server
```

This is normally started automatically as a stdio subprocess when traders run.
Run it directly only when testing the MCP server itself.

### Local Market MCP Server

```powershell
uv run -m backend.market_server
```

This local server exposes `lookup_share_price(symbol)`. The default trader MCP
bundle currently uses `uvx mcp-yahoo-finance` directly instead.

### Smoke Check

```powershell
uv run python backend_smoke_check.py
```

Use this to verify imports, core runtime wiring, and API construction.

## Start Everything Together

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1
```

macOS/Linux:

```bash
./script/start.sh
```

By default, the start scripts launch:

- dashboard on `http://127.0.0.1:7860`
- read-only API on `http://127.0.0.1:8000`
- scheduler in the background

The scripts write PID files and logs to `.run/`.

## Stop Everything

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File script\stop.ps1
```

macOS/Linux:

```bash
./script/stop.sh
```

## Start Script Options

Windows examples:

```powershell
powershell -ExecutionPolicy Bypass -File script\start.ps1 -NoApi -NoScheduler
powershell -ExecutionPolicy Bypass -File script\start.ps1 -NoDashboard
powershell -ExecutionPolicy Bypass -File script\start.ps1 -DashboardPort 7861
powershell -ExecutionPolicy Bypass -File script\start.ps1 -ApiPort 8001
```

macOS/Linux examples:

```bash
./script/start.sh --no-api --no-scheduler
./script/start.sh --no-dashboard
./script/start.sh --dashboard-port 7861
./script/start.sh --api-port 8001
```

## Stop Script Options

Windows examples:

```powershell
powershell -ExecutionPolicy Bypass -File script\stop.ps1 -DashboardOnly
powershell -ExecutionPolicy Bypass -File script\stop.ps1 -ApiOnly
powershell -ExecutionPolicy Bypass -File script\stop.ps1 -SchedulerOnly
```

macOS/Linux examples:

```bash
./script/stop.sh --dashboard-only
./script/stop.sh --api-only
./script/stop.sh --scheduler-only
```

## Check Whether Traders Are Running

Start scripts write scheduler logs here:

```text
.run/scheduler.out.log
.run/scheduler.err.log
```

The scheduler also writes activity into each trader's Recent Logs panel on the
dashboard.

If traders are not running, check:

- `.env` contains a valid model API key such as `OPENAI_API_KEY`.
- `SCHEDULER_TIME_WINDOW` is currently open, or set to `always` for testing.
- `RUN_EVERY_N_MINUTES` is set to the interval you expect.
- `.run/scheduler.err.log` has no startup errors.

For immediate local verification:

```text
SCHEDULER_TIME_WINDOW=always
```

Then restart only the scheduler:

```powershell
powershell -ExecutionPolicy Bypass -File script\stop.ps1 -SchedulerOnly
powershell -ExecutionPolicy Bypass -File script\start.ps1 -NoDashboard -NoApi
```
