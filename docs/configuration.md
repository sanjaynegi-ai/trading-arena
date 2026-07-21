# Configuration

Environment variables are loaded from `.env` at startup. Start from
`.env.example`, then add real API keys and scheduler settings.

## Local Prerequisites

- Python 3.12+ and `uv` are required for the project runtime.
- Node.js LTS is required for `npx`, which starts the Tavily web-search and
  researcher-memory MCP servers. Confirm it is available with `npx --version`.

## Minimal Local Setup

For a normal OpenAI run with researcher web search:

```text
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
RUN_EVERY_N_MINUTES=15
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
SCHEDULER_TIME_WINDOW=us_or_india_office
```

For immediate testing outside office hours or on weekends:

```text
SCHEDULER_TIME_WINDOW=always
```

## API Keys

- `OPENAI_API_KEY`: required for standard OpenAI model runs.
- `TAVILY_API_KEY`: used by the Tavily MCP search server for researcher web
  search.
- `OPENROUTER_API_KEY`: required when a selected model name contains `/`.
- `DEEPSEEK_API_KEY`: required when a selected model name contains `deepseek`.
- `GROK_API_KEY`: required when a selected model name contains `grok`.
- `GOOGLE_API_KEY`: required when a selected model name contains `gemini`.

## Model Routing

Model routing lives in `backend/traders.py`.

- Plain model names such as `gpt-5.4-mini` are treated as OpenAI model names.
- Names containing `/` use OpenRouter.
- Names containing `deepseek` use DeepSeek.
- Names containing `grok` use xAI Grok.
- Names containing `gemini` use Gemini through its OpenAI-compatible endpoint.

Roster defaults live in `backend/roster.py`.

`USE_MANY_MODELS=false` means each `TraderProfile` uses its own `model_name`.

`USE_MANY_MODELS=true` maps traders positionally onto `MANY_MODELS`; profiles
past the end of that list fall back to `DEFAULT_MODEL`.

## Scheduler Settings

- `RUN_EVERY_N_MINUTES`: scheduler interval in minutes. Defaults to `15`.
- `RUN_EVEN_WHEN_MARKET_IS_CLOSED`: legacy override. When `true`, traders run on
  every scheduler tick regardless of the configured time window.
- `SCHEDULER_TIME_WINDOW`: controls when the scheduler may run. Defaults to
  `us_market`.

Supported `SCHEDULER_TIME_WINDOW` values:

- `us_market`: Monday-Friday, 9:30 AM-4:00 PM New York time.
- `us_office`: Monday-Friday, 9:00 AM-5:00 PM New York time.
- `india_office`: Monday-Friday, 9:00 AM-5:00 PM India time.
- `us_or_india_office`: runs when either US office hours or India office hours
  are open.
- `always`: runs on every scheduler tick.

The time-window checks live in `backend/trading_arena.py`. They use:

- `ZoneInfo("America/New_York")` for US windows.
- `ZoneInfo("Asia/Kolkata")` for India windows.

These checks do not currently account for market holidays or special half-days.

## Example Scheduler Modes

Run during US market hours only:

```text
RUN_EVERY_N_MINUTES=15
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
SCHEDULER_TIME_WINDOW=us_market
```

Run during either US or India office hours:

```text
RUN_EVERY_N_MINUTES=15
RUN_EVEN_WHEN_MARKET_IS_CLOSED=false
SCHEDULER_TIME_WINDOW=us_or_india_office
```

Run continuously for demos or debugging:

```text
RUN_EVERY_N_MINUTES=15
SCHEDULER_TIME_WINDOW=always
```

## Runtime Files

- `accounts.db`: local SQLite account snapshots and activity logs.
- `.run/*.pid`: process IDs written by start scripts.
- `.run/*.out.log`: process stdout logs written by start scripts.
- `.run/*.err.log`: process stderr logs written by start scripts.
- `memory/`: researcher memory databases created by the memory MCP server, one
  per trader as `{firstname}_{lastname}.db`.
