# MCP Servers

Trading Arena uses MCP servers to give agents controlled access to account
actions, market data, web research, and memory.

MCP server bundles are defined in `backend/mcp_servers.py`.

## Trader MCP Servers

Trader-facing MCP servers are created by:

```python
trader_mcp_servers()
```

in `backend/mcp_servers.py`.

The default trader bundle contains:

- accounts server: `uv run -m backend.accounts_server`
- Yahoo Finance market server: `uvx mcp-yahoo-finance`

These server objects are opened in `Trader.run_with_mcp_servers()` in
`backend/traders.py`, then passed into the trader agent with:

```python
Agent(..., mcp_servers=trader_servers)
```

## Accounts MCP Server

`backend/accounts_server.py` exposes account tools and resources.

Tools:

- `get_balance(name)`
- `get_holdings(name)`
- `buy_shares(name, symbol, quantity, rationale)`
- `sell_shares(name, symbol, quantity, rationale)`
- `change_strategy(name, strategy)`

Resources:

- `accounts://accounts_server/{name}`
- `accounts://strategy/{name}`

The accounts server is the execution path for account changes. Buys and sells
are still validated by `backend/accounts.py`, including cash and holdings
guardrails.

## Market MCP Server

The default trader bundle uses the external Yahoo Finance MCP package:

```text
uvx mcp-yahoo-finance
```

For traders, the market MCP server is a decision-support tool. It helps the LLM
inspect market data, current prices, and related stock information before
deciding whether to buy, sell, or hold.

It does not execute trades. Actual account actions go through the accounts MCP
server, and account methods independently call
`backend.market.get_share_price(symbol)` before changing account state.

```text
Market MCP tools  -> help the trader inspect market data and choose
Account MCP tools -> execute buys/sells and enforce account guardrails
```

## Local Market Server

`backend/market_server.py` defines a local MCP server with:

```python
lookup_share_price(symbol)
```

This local server calls `backend.market.get_share_price(symbol)`, but the
default trader bundle currently uses `uvx mcp-yahoo-finance` directly instead
of `backend.market_server`.

You can run the local market server independently with:

```powershell
uv run -m backend.market_server
```

## Researcher MCP Servers

Researcher-facing MCP servers are created by:

```python
researcher_mcp_servers(name, lastname)
```

in `backend/mcp_servers.py`.

The default researcher bundle contains:

- fetch: `uvx mcp-server-fetch`
- Tavily search: `npx -y tavily-mcp@latest`, filtered to `tavily_search`
- memory: `npx -y mcp-memory-libsql`

Each trader gets isolated researcher memory through:

```text
file:./memory/{firstname}_{lastname}.db
```

## Researcher Research Flow

The Researcher does not follow a hardcoded Python workflow such as "always
search first, then fetch three pages." The current implementation is
agent-directed: the code gives the researcher instructions and tool access, then
the LLM decides which tools to call for the trader's request.

The Researcher is created in `backend/traders.py`:

```python
async def get_researcher(mcp_servers, model_name: str) -> Agent:
    return Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )
```

The Researcher instructions live in `backend/templates.py` and tell it to:

```text
Search for recent market news, company developments, macro themes, and risks.
Use fetch when you need to inspect a specific page, Tavily search for discovery,
and memory tools to store and recall useful company, sector, and source notes.
```

The intended research flow is:

```text
Trader asks Researcher for ideas/news/context
  -> Researcher uses Tavily search for discovery
  -> Researcher uses Fetch when it has a specific URL to inspect
  -> Researcher may use Memory to recall or store useful notes
  -> Researcher returns tickers, evidence, risks, and relevance
  -> Trader decides whether to use market/account tools
```

Tool purposes:

- Tavily search: discovery. Use it to find recent news, broad market context,
  company developments, themes, catalysts, and risks.
- Fetch: source inspection. Use it after a URL is known and the researcher needs
  to read a specific page directly.
- Memory: continuity. Use it to recall or store useful company, sector, source,
  and prior-research notes for future cycles.

The Trader sees the Researcher as a nested tool through
`get_researcher_tool(...)` in `backend/traders.py`. The tool description from
`backend/templates.py` says the trader can ask for:

```text
a specific ticker, theme, sector, or broad market scan
```

Trading prompts trigger this path by telling the Trader to use the researcher
for news, themes, and catalysts. Rebalance prompts tell the Trader to use the
researcher to check news and risks for current holdings.

## Researcher Memory

The Memory MCP server gives each researcher a long-term note store that can
survive across trader cycles. It is intended for research context, not account
state. Account state belongs in `accounts.db`; researcher memory belongs under
`memory/`.

The default researcher is instructed to use memory in
`backend/templates.py`:

```text
Use fetch when you need to inspect a specific page, Tavily search for discovery,
and memory tools to store and recall useful company, sector, and source notes.
```

Useful memory examples include:

- company notes
- sector notes
- source notes
- prior research findings
- recurring risks or catalysts
- facts that may help future trade/rebalance cycles

The application code does not explicitly call a `read_memory` or `write_memory`
function. Instead, the researcher LLM receives the memory MCP tools and decides
when to use them based on its instructions and the trader's request.

The memory server is registered in `researcher_mcp_servers(name, lastname)` in
`backend/mcp_servers.py`:

```python
memory = MCPServerStdio(
    params={
        "command": "npx",
        "args": ["-y", "mcp-memory-libsql"],
        "cwd": str(PROJECT_ROOT),
        "env": _env_with(
            LIBSQL_URL=f"file:./memory/{_memory_db_name(name, lastname)}"
        ),
    },
)
```

That means memory is isolated by first and last name, so two learners with the
same first name can both participate safely. Example files:

```text
memory/sanjay_negi.db
memory/neil_sharma.db
```

If those files do not exist yet, the researcher has not successfully used memory
for that trader.

To inspect memory files once they exist:

```powershell
Get-ChildItem memory
sqlite3 memory\sanjay_negi.db ".tables"
sqlite3 memory\sanjay_negi.db "SELECT * FROM memories LIMIT 20;"
```

The exact table names depend on the `mcp-memory-libsql` server version. Use
`.tables` first before querying a table directly.

Trace logs may show that a memory MCP tool was called:

- dashboard: Recent Logs
- API: `GET /api/traders/{name}/logs`
- database: `accounts.db`, table `logs`

Those traces show tool activity, but they should not be treated as the source of
truth for memory content. The source of truth is the per-trader database under
`memory/`.

## Researcher Registration

The researcher is built in `backend/traders.py`:

```python
get_researcher(mcp_servers, model_name)
get_researcher_tool(mcp_servers, model_name)
```

`get_researcher(...)` creates the researcher agent with:

```python
Agent(..., mcp_servers=mcp_servers)
```

`get_researcher_tool(...)` exposes that researcher as a nested tool. The trader
then receives it in `Trader.create_agent(...)` with:

```python
tools=[researcher_tool]
```

## Wiring Summary

```text
Trader.run_with_mcp_servers()
  -> trader_mcp_servers()
    -> accounts_server
    -> mcp-yahoo-finance
  -> researcher_mcp_servers(trader.name, trader.lastname)
    -> fetch
    -> Tavily search
    -> memory
  -> Trader.create_agent(...)
    -> tools=[researcher_tool]
    -> mcp_servers=trader_servers
```
