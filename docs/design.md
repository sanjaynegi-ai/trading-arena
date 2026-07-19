# Design Diagrams

This page keeps the compact design sequence diagram. For the fuller component
overview, architecture diagram, one-cycle flow, ticker selection flow, and
trace/log flow, see [architecture.md](architecture.md).

## Trader Cycle Sequence

```mermaid
sequenceDiagram
    participant Scheduler as backend/trading_arena.py
    participant Trader as Trader
    participant AccountsClient as accounts_client.py
    participant AccountsMCP as accounts_server.py
    participant TraderTools as Trader MCP servers
    participant Researcher as Researcher tool
    participant ResearchTools as Researcher MCP servers
    participant Yahoo as Yahoo Finance
    participant Runner as Agents SDK Runner
    participant Account as accounts.py
    participant DB as accounts.db
    participant Logs as LogTracer

    Scheduler->>Logs: register trace processor
    Scheduler->>Trader: run()
    Trader->>TraderTools: open accounts and market MCP servers
    Trader->>ResearchTools: open fetch/search/memory MCP servers
    Trader->>AccountsClient: read account and strategy resources
    AccountsClient->>AccountsMCP: accounts://... resources
    AccountsMCP->>Account: report() and get_strategy()
    Account->>DB: read/write account and log rows
    AccountsMCP-->>AccountsClient: JSON account and strategy text

    Trader->>Researcher: expose researcher as nested tool
    Trader->>Runner: run agent with prompt and tools
    Runner->>Researcher: request market ideas or context
    Researcher->>ResearchTools: use fetch/search/memory
    Runner->>Yahoo: inspect market data
    Runner->>TraderTools: buy, sell, change strategy, or hold
    TraderTools->>Account: mutate account when account tools are called
    Account->>Yahoo: price selected symbol
    Account->>DB: persist account and logs

    Runner-->>Logs: trace and span events
    Logs->>DB: write log rows
    Trader-->>Scheduler: complete cycle, toggle trade/rebalance mode
```
