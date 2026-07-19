# How To Participate

This arena is built so each learner can join by adding a trader profile, then
optionally customizing the trader workflow, researcher, prompts, model, and MCP
tools.

Related docs:

- [architecture.md](architecture.md): components, diagrams, and runtime flow
- [mcp_servers.md](mcp_servers.md): account, market, researcher, fetch, search,
  and memory MCP wiring
- [configuration.md](configuration.md): `.env` options, model routing, and
  scheduler time windows
- [running.md](running.md): commands for running components independently or
  through the start scripts

## Arena Design

The arena starts from the roster in `backend/roster.py`. Each learner is
registered as a `TraderProfile` with a `name`, `lastname`, `strategy`, and
`model_name`. When the scheduler in `backend/trading_arena.py` starts,
`create_traders()` reads `TRADER_PROFILES`, resolves the model names, and builds
one trader runtime for each profile.

The roster only defines who participates; it does not define a per-trader stock
universe. Traders can attempt to trade any ticker symbol that Yahoo Finance can
price. The account code normalizes symbols and calls
`backend.market.get_share_price(symbol)` from `Account.buy_shares(...)` and
`Account.sell_shares(...)` in `backend/accounts.py`. The price lookup itself is
defined in `backend/market.py`. If Yahoo Finance cannot return a usable positive
price for a symbol, the trade fails with a `ValueError`.

Each trader is an autonomous competitor. On every cycle, the trader can use MCP
tools to inspect the account, research the market, and place trades:

- Accounts MCP server: lets the trader read balance, holdings, full account
  reports, strategy text, transaction history, and execute account actions such
  as buy, sell, and change strategy.
- Market tools: let the trader fetch live share-price and market data before
  making a buy, sell, hold, or rebalance decision.
- Researcher tool: the researcher is connected to the trader as a nested tool.
  The trader asks the researcher for evidence, news, context, risks, or ideas
  before deciding what to do.

The default researcher has its own MCP tools:

- Fetch: retrieves and reads a specific web page when the researcher already has
  a URL or needs to inspect a source directly.
- Web search: discovers recent news, market commentary, company information, and
  possible opportunities. In this project Tavily is filtered to the
  `tavily_search` tool so the researcher stays focused on search.
- Memory: stores and recalls useful notes about companies, sectors, sources, and
  previous research. Each trader gets an isolated memory database so learners do
  not overwrite each other's research context. The researcher LLM decides when
  to use memory tools; the application code only registers the memory MCP
  server. See [mcp_servers.md](mcp_servers.md#researcher-memory) for inspection
  commands and storage details.

The research workflow is agent-directed rather than hardcoded. The trader asks
the Researcher for a specific ticker, theme, sector, or broad market scan; the
Researcher may use Tavily search for discovery, Fetch to read a known URL, and
Memory to recall or store durable notes. See
[mcp_servers.md](mcp_servers.md#researcher-research-flow) for the complete
flow.

The normal flow is:

1. Register a trader in `TRADER_PROFILES`.
2. Reset accounts so the trader gets its starting strategy.
3. Start the scheduler.
4. The scheduler creates traders from the roster.
5. Each trader opens account, market, and researcher MCP tools.
6. The trader alternates between new-opportunity trading cycles and existing
   holding rebalance cycles.
7. Account state and activity logs are written to `accounts.db`.

## What A Trader Gets

Every trader starts with a persistent account in `accounts.db`. The account can:

- read balance and holdings
- buy and sell shares
- change its strategy
- read account reports and strategy text through the accounts MCP server
- use Yahoo Finance market tools for live price and market context
- use a nested researcher tool for web research and memory

All trader implementations should extend `backend.interfaces.trader.Trader` and
implement:

```python
async def run(self) -> str:
    ...
```

The default implementation is `backend.traders.Trader`.

The account and market MCP servers are registered with the trader at runtime, not
inside `backend/roster.py`. `Trader.run_with_mcp_servers()` in
`backend/traders.py` opens the server bundle returned by
`backend.mcp_servers.trader_mcp_servers()`. That bundle currently contains the
local accounts server command `uv run -m backend.accounts_server` and the Yahoo
Finance market server command `uvx mcp-yahoo-finance`. The opened server objects
are then passed into `Agent(..., mcp_servers=trader_servers)` in
`Trader.create_agent(...)`.

## Fast Path: Add A New Competitor

Most learners only need to edit `backend/roster.py`.

1. Add a strategy string:

```python
nina_strategy = (
    "Look for high-quality companies with improving earnings momentum, "
    "reasonable valuation, and clear catalysts over the next quarter."
)
```

2. Add a `TraderProfile`:

```python
TRADER_PROFILES: list[TraderProfile] = [
    TraderProfile(name="Sanjay", lastname="Negi", strategy=sanjay_strategy),
    TraderProfile(name="Neil", lastname="Sharma", strategy=neil_strategy),
    TraderProfile(name="Nina", lastname="Momentum", strategy=nina_strategy),
]
```

3. Optionally choose a model:

```python
TraderProfile(
    name="Nina",
    lastname="Momentum",
    strategy=nina_strategy,
    model_name="gpt-5.4-mini",
)
```

If `USE_MANY_MODELS=false`, each profile uses its own `model_name`. If
`USE_MANY_MODELS=true`, the scheduler maps traders positionally to
`MANY_MODELS`; profiles past the end of that list fall back to `DEFAULT_MODEL`.

## Model Choices

Model routing lives in `backend/traders.py`.

- Plain model names such as `gpt-5.4-mini` are treated as OpenAI model names.
- Names containing `/` use OpenRouter and require `OPENROUTER_API_KEY`.
- Names containing `deepseek` require `DEEPSEEK_API_KEY`.
- Names containing `grok` require `GROK_API_KEY`.
- Names containing `gemini` require `GOOGLE_API_KEY`.

Normal OpenAI runs require `OPENAI_API_KEY`.

## Prompts And Strategy

Shared prompt templates live in `backend/templates.py`.

Use these when you want every trader to follow the same arena rules:

- `researcher_instructions()`
- `research_tool()`
- `trader_instructions(name)`
- `trade_message(name, strategy, account)`
- `rebalance_message(name, strategy, account)`

Trade prompts are intentionally focused on finding new opportunities. Rebalance
prompts are intentionally focused on existing holdings. Keep that separation so
traders alternate between exploration and portfolio maintenance.

For a learner-specific personality or style, prefer putting the durable
investment philosophy in that learner's `strategy` string in `backend/roster.py`.
Change global templates only when the whole arena should behave differently.

## Custom Trader Workflow

Advanced learners can create their own trader class while still extending the
ABC:

```python
from backend.interfaces.trader import Trader


class NinaTrader(Trader):
    async def run(self) -> str:
        # Open MCP servers, inspect account state, run agents, or implement
        # another workflow here.
        return "Nina completed one trading cycle."
```

The default `backend.traders.Trader` already demonstrates the expected runtime
pattern:

- open trader MCP servers and researcher MCP servers with `AsyncExitStack`
- create a trader `Agent`
- expose a nested researcher agent with `get_researcher_tool(...)`
- read account and strategy through `backend.accounts_client`
- remove long portfolio time series before prompt injection
- choose `trade_message(...)` or `rebalance_message(...)`
- run `Runner.run(..., max_turns=10)`
- wrap each run in an Agents SDK trace
- catch exceptions per trader
- toggle between trade and rebalance mode

The default researcher is attached to the trader in
`Trader.create_agent(...)` in `backend/traders.py`. That method calls
`get_researcher_tool(researcher_servers, self.model_name)`, stores the returned
tool in `tools=[researcher_tool]`, and passes the account and market MCP bundle
through `mcp_servers=trader_servers`.

If you add a custom trader class, also update the scheduler factory in
`backend/trading_arena.py` so your profile uses that class.

## Custom Researcher

The default researcher is built by:

```python
get_researcher(mcp_servers, model_name)
get_researcher_tool(mcp_servers, model_name)
```

It uses `researcher_instructions()` and the researcher MCP server bundle from
`backend/mcp_servers.py`.

The fetch, web search, and memory MCP servers are registered with the researcher
through `researcher_mcp_servers(name, lastname)` in `backend/mcp_servers.py`.
`Trader.run_with_mcp_servers()` opens that bundle with the current trader's
first and last name, then passes the opened `researcher_servers` into
`get_researcher_tool(...)`.
`get_researcher(...)` finally creates the researcher with
`Agent(..., mcp_servers=mcp_servers)`.

Use this default researcher when you only need general web research, fetch, and
memory. If the learner only wants a different tone or research checklist, edit
`researcher_instructions()` and `research_tool()` in `backend/templates.py`.

Create a custom researcher when you want a different research workflow, for
example:

- stricter evidence requirements
- sector-specific analysis
- memory-first research
- a multi-agent research team
- different tools for news, filings, or quantitative signals

### Add A Custom Researcher

A custom researcher can live in a new module such as
`backend/researchers/nina_researcher.py`. Keep the public factory small: it
should accept opened MCP servers and a model name, then return an Agents SDK
`Agent`.

```python
from agents import Agent, Tool

from backend.templates import research_tool
from backend.traders import get_model


def nina_researcher_instructions() -> str:
    return """You are Nina's market researcher.
Focus on earnings momentum, analyst revisions, recent news, and valuation risk.
Return concise evidence with tickers and links when available."""


async def get_nina_researcher(mcp_servers, model_name: str) -> Agent:
    return Agent(
        name="NinaResearcher",
        instructions=nina_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_nina_researcher_tool(mcp_servers, model_name: str) -> Tool:
    researcher = await get_nina_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="NinaResearcher",
        tool_description=(
            "Researches earnings momentum, analyst revisions, catalysts, "
            "valuation risk, and relevant market news for Nina's strategy."
        ),
    )
```

If the researcher needs different tools, update or add a server factory in
`backend/mcp_servers.py`. For example, a filings researcher might add an SEC MCP
server, while a macro researcher might add a data source for rates, inflation,
or commodities. Keep each learner's memory isolated by using a per-trader path
based on first and last name, such as `file:./memory/nina_momentum.db`.

### Connect A Custom Researcher To A Trader

The default trader uses `get_researcher_tool(...)`. A custom trader can swap in
its own researcher tool while keeping the rest of the arena behavior.

```python
from agents import Agent

from backend.traders import Trader, get_model
from backend.templates import trader_instructions
from backend.researchers.nina_researcher import get_nina_researcher_tool


class NinaTrader(Trader):
    async def create_agent(self, trader_servers, researcher_servers) -> Agent:
        researcher_tool = await get_nina_researcher_tool(
            researcher_servers,
            self.model_name,
        )
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions(self.name),
            model=get_model(self.model_name),
            tools=[researcher_tool],
            mcp_servers=trader_servers,
        )
        return self.agent
```

For a complete research workflow, the researcher tool does not have to be a
single simple agent. It can orchestrate several specialist agents internally, run
a staged process, use custom MCP servers, or produce a structured research
brief. The trader only needs a clear tool interface it can call during trade and
rebalance cycles.

Good researcher outputs include:

- ticker symbols considered
- sources or search terms used
- short thesis
- key risks
- price or valuation context
- what would change the recommendation
- a concise final recommendation for the trader

Keep the trader-facing tool description clear. The trader should know what kind
of research to request and what kind of answer to expect.

## MCP Tools

MCP server bundles live in `backend/mcp_servers.py`.

Trader servers include:

- accounts server: registered in `trader_mcp_servers()` with
  `uv run -m backend.accounts_server`; exposes account tools and account
  resources.
- Yahoo Finance market server: registered in `trader_mcp_servers()` with
  `uvx mcp-yahoo-finance`; exposes live market-data tools to traders.

There is also a local `backend/market_server.py` with a `lookup_share_price`
tool, but the default trader bundle currently uses the Yahoo Finance MCP package
directly instead of this local server.

Researcher servers include:

- fetch: registered in `researcher_mcp_servers(name, lastname)` with
  `uvx mcp-server-fetch`.
- Tavily search: registered in `researcher_mcp_servers(name, lastname)` with
  `npx -y tavily-mcp@latest` and filtered to `tavily_search`.
- memory: registered in `researcher_mcp_servers(name, lastname)` with
  `npx -y mcp-memory-libsql` and one database per trader:
  `file:./memory/{firstname}_{lastname}.db`.

The account client expects this command to work from the project root over
stdio:

```powershell
uv run -m backend.accounts_server
```

## Reset And Run

After adding or changing profiles, reset accounts so each trader starts with its
configured strategy:

```powershell
uv run -m backend.reset
```

Run the backend smoke check:

```powershell
uv run python backend_smoke_check.py
```

Start the read-only API:

```powershell
uv run uvicorn backend.api:app --port 8000
```

Run the long-running scheduler:

```powershell
uv run -m backend.trading_arena
```

The scheduler writes activity to `accounts.db` and alternates each trader
between trade and rebalance cycles.

## Before Submitting A Trader

Check these before competing:

- The trader has a unique `name` in `TRADER_PROFILES`.
- The strategy is specific enough to guide decisions.
- The selected model has the required API key in `.env`.
- `uv run -m backend.reset` succeeds.
- `uv run python backend_smoke_check.py` succeeds.
- The API returns the trader at `/api/traders`.
- The implementation does not write directly to `accounts.db`; use account tools
  and existing backend APIs.
