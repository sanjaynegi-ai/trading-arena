# Developer Notes

Run local MCP servers from the project root so package imports and relative
paths resolve correctly.

## Local MCP Servers

Accounts MCP server:

```powershell
uv run -m backend.accounts_server
```

Market MCP server:

```powershell
uv run -m backend.market_server
```

Push MCP server:

```powershell
uv run -m backend.push_server
```

Note: `backend.push_server` is listed for the planned local push server, but
`backend/push_server.py` does not currently exist in this checkout.

## Account Client

`backend/accounts_client.py` starts the accounts server over stdio with:

```powershell
uv run -m backend.accounts_server
```

Keep that command working from the project root. The account client depends on
it for reading `accounts://accounts_server/{name}` and
`accounts://strategy/{name}` resources without callers managing the MCP session
directly.

## Runtime Notes

The full trading scheduler runs from the project root with:

```powershell
uv run -m backend.trading_arena
```

This is a long-running process. It loops forever, runs the rostered traders when
the market is open or when the override is enabled, and writes account snapshots
and activity logs to `accounts.db`.

Environment variables:

- `OPENAI_API_KEY`: Required for normal OpenAI model runs.
- `TAVILY_API_KEY`: Used by the Tavily MCP search server for researcher web
  search.
- `RUN_EVERY_N_MINUTES`: Scheduler interval in minutes. Defaults to `60`.
- `RUN_EVEN_WHEN_MARKET_IS_CLOSED`: Set to `true` to run traders even outside
  regular market hours. Defaults to `false`.
- `USE_MANY_MODELS`: Set to `true` to map traders onto `MANY_MODELS` from
  `backend/roster.py`. Defaults to `false`, which uses each profile's
  `model_name`.
- `OPENROUTER_API_KEY`: Required only when a selected model name contains `/`,
  which routes through OpenRouter.
- `DEEPSEEK_API_KEY`: Required only when a selected model name contains
  `deepseek`.
- `GROK_API_KEY`: Required only when a selected model name contains `grok`.
- `GOOGLE_API_KEY`: Required only when a selected model name contains `gemini`.

Market pricing note: the broader capstone pattern can use simulator prices when
Massive market data is unavailable. This checkout currently uses Yahoo Finance
through `backend.market.get_share_price()` and the Yahoo Finance MCP server; it
does not currently define `MASSIVE_API_KEY` or a local simulator fallback.
