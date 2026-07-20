"""Manish Kumar's custom Trader using a multi-specialist research team."""

from __future__ import annotations

import json
from contextlib import AsyncExitStack

from agents import Agent, Runner

from backend.researchers.manish_research_team import get_research_coordinator_tool
from backend.mcp_servers import (
    focused_market_mcp_servers,
    manish_trader_mcp_servers,
    researcher_mcp_servers,
)
from backend.templates import rebalance_message, trade_message, trader_instructions
from backend.traders import MAX_TURNS, Trader, get_model


class ManishTrader(Trader):
    """Trader that consults Manish's research team before making a decision.

    The inherited ``Trader`` lifecycle still opens Arena MCP servers, reads the
    account and strategy, selects the trade or rebalance prompt, records a
    trace, and toggles the next cycle. This class changes only the research tool
    attached to the decision-making agent.
    """

    async def create_agent(
        self,
        trader_servers,
        researcher_servers,
        technical_servers,
    ) -> Agent:
        """Create Manish's Trader with the multi-specialist research team tool."""

        research_team_tool = await get_research_coordinator_tool(
            researcher_servers,
            technical_servers,
            self.model_name,
        )
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions(self.name),
            model=get_model(self.model_name),
            tools=[research_team_tool],
            mcp_servers=trader_servers,
        )
        return self.agent

    async def run_agent(
        self,
        trader_servers,
        researcher_servers,
        technical_servers,
    ) -> str:
        """Run a trade or rebalance turn with separated specialist tool bundles."""

        agent = await self.create_agent(
            trader_servers,
            researcher_servers,
            technical_servers,
        )
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
        """Read Manish's strategy through the central account resource."""

        from backend.accounts_client import read_strategy_resource

        return await read_strategy_resource(self.name)

    async def run_with_mcp_servers(self) -> str:
        """Open isolated tool bundles for Manish's Trader and specialists."""

        async with AsyncExitStack() as stack:
            trader_servers = [
                await stack.enter_async_context(server)
                for server in manish_trader_mcp_servers()
            ]
            researcher_servers = [
                await stack.enter_async_context(server)
                for server in researcher_mcp_servers(self.name, self.lastname)
            ]
            technical_servers = [
                await stack.enter_async_context(server)
                for server in focused_market_mcp_servers()
            ]
            return await self.run_agent(
                trader_servers,
                researcher_servers,
                technical_servers,
            )
