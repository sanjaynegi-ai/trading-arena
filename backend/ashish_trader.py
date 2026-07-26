from __future__ import annotations

import json
from contextlib import AsyncExitStack

from agents import Agent, Runner

from backend.mcp_servers import (
    trader_mcp_servers,
    researcher_mcp_servers,
)
from backend.templates import (
    trader_instructions_ashish,
    researcher_instructions_ashish,
    trade_message,
    rebalance_message,
)
from backend.traders import MAX_TURNS, Trader, get_model


class AshishTrader(Trader):
    """Ashish's custom catalyst-driven trader with specialized prompts."""

    async def create_agent(
        self,
        trader_servers,
        researcher_servers,
    ) -> Agent:
        """Create Ashish's trader agent with custom prompts."""

        # Build researcher agent using Ashish's researcher prompt
        researcher = Agent(
            name="Researcher",
            instructions=researcher_instructions_ashish(),
            model=get_model(self.model_name),
            mcp_servers=researcher_servers,
        )
        researcher_tool = researcher.as_tool(
            tool_name="Researcher",
            tool_description="Catalyst-driven research assistant",
        )

        # Build trader agent using Ashish's trader prompt
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions_ashish(self.name),
            model=get_model(self.model_name),
            tools=[researcher_tool],
            mcp_servers=trader_servers,
        )
        return self.agent

    async def run_agent(self, trader_servers, researcher_servers) -> str:
        """Run Ashish's trade or rebalance cycle."""

        agent = await self.create_agent(trader_servers, researcher_servers)
        account = await self.get_account_report()
        strategy = await self.get_strategy()

        message = (
            trade_message(self.name, strategy, account)
            if self.do_trade
            else rebalance_message(self.name, strategy, account)
        )

        result = await Runner.run(agent, message, max_turns=MAX_TURNS)
        return str(result.final_output)

    async def get_strategy(self) -> str:
        """Read strategy from central account resource."""

        from backend.accounts_client import read_strategy_resource
        return await read_strategy_resource(self.name)

    async def run_with_mcp_servers(self) -> str:
        """Open MCP servers for Ashish's trader."""

        async with AsyncExitStack() as stack:
            trader_servers = [
                await stack.enter_async_context(server)
                for server in trader_mcp_servers()
            ]
            researcher_servers = [
                await stack.enter_async_context(server)
                for server in researcher_mcp_servers(self.name, self.lastname)
            ]
            return await self.run_agent(trader_servers, researcher_servers)
