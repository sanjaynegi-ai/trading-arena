"""Gaurav Jain's custom trader using the shared trading lifecycle."""

from __future__ import annotations

from contextlib import AsyncExitStack

from agents import Agent, Runner

from backend.mcp_servers import (
    open_mcp_servers,
    researcher_mcp_servers,
    trader_mcp_servers,
)
from backend.researchers.gaurav_researcher import get_gaurav_researcher_tool
from backend.templates import rebalance_message, trade_message, trader_instructions
from backend.traders import MAX_TURNS, Trader, get_model


class GauravTrader(Trader):
    """Trader that follows Gaurav's long-term, evidence-based philosophy."""

    async def create_agent(
        self,
        trader_servers,
        researcher_servers,
    ) -> Agent:
        """Create Gaurav's trader agent with the shared researcher tool."""

        researcher_tool = await get_gaurav_researcher_tool(
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

    async def run_agent(
        self,
        trader_servers,
        researcher_servers,
    ) -> str:
        """Run a trade or rebalance turn for Gaurav's trader."""

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
        """Read Gaurav's strategy through the central account resource."""

        from backend.accounts_client import read_strategy_resource

        return await read_strategy_resource(self.name)

    async def run_with_mcp_servers(self) -> str:
        """Open trader and researcher MCP servers for Gaurav's trader."""

        async with AsyncExitStack() as stack:
            trader_servers = await open_mcp_servers(stack, trader_mcp_servers())
            researcher_servers = await open_mcp_servers(
                stack,
                researcher_mcp_servers(self.name, self.lastname),
            )
            return await self.run_agent(trader_servers, researcher_servers)
