from __future__ import annotations

import json
import os
from contextlib import AsyncExitStack
from pathlib import Path

from agents import Agent, OpenAIChatCompletionsModel, Runner, Tool, trace
from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.accounts_client import read_accounts_resource, read_strategy_resource
from backend.database import write_log
from backend.interfaces.trader import Trader as TraderABC
from backend.mcp_servers import researcher_mcp_servers, trader_mcp_servers
from backend.templates import (
    rebalance_message,
    research_tool,
    researcher_instructions,
    trade_message,
    trader_instructions,
)
from backend.tracers import make_trace_id


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
grok_api_key = os.getenv("GROK_API_KEY")
gemini_api_key = os.getenv("GOOGLE_API_KEY")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
GROK_BASE_URL = "https://api.x.ai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MAX_TURNS = 10

_provider_clients: dict[str, AsyncOpenAI] = {}


def _provider_client(
    name: str,
    base_url: str,
    api_key: str | None,
) -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client for an optional model provider."""

    if not api_key:
        raise RuntimeError(
            f"{name} model selected, but its API key is not set. "
            "Add the key to .env or choose an OpenAI model."
        )

    if name not in _provider_clients:
        _provider_clients[name] = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    return _provider_clients[name]


def get_model(model_name: str) -> str | OpenAIChatCompletionsModel:
    """Return an Agents SDK model value for OpenAI or optional providers."""

    normalized_model_name = model_name.strip()
    provider_key = normalized_model_name.lower()

    if "/" in normalized_model_name:
        client = _provider_client(
            "openrouter",
            OPENROUTER_BASE_URL,
            openrouter_api_key,
        )
        return OpenAIChatCompletionsModel(
            model=normalized_model_name,
            openai_client=client,
        )

    if "deepseek" in provider_key:
        client = _provider_client(
            "deepseek",
            DEEPSEEK_BASE_URL,
            deepseek_api_key,
        )
        return OpenAIChatCompletionsModel(
            model=normalized_model_name,
            openai_client=client,
        )

    if "grok" in provider_key:
        client = _provider_client("grok", GROK_BASE_URL, grok_api_key)
        return OpenAIChatCompletionsModel(
            model=normalized_model_name,
            openai_client=client,
        )

    if "gemini" in provider_key:
        client = _provider_client("gemini", GEMINI_BASE_URL, gemini_api_key)
        return OpenAIChatCompletionsModel(
            model=normalized_model_name,
            openai_client=client,
        )

    return normalized_model_name


async def get_researcher(mcp_servers, model_name: str) -> Agent:
    """Build the researcher agent with its MCP servers and selected model."""

    return Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_researcher_tool(
    mcp_servers,
    model_name: str,
    account_name: str,
) -> Tool:
    """Expose the researcher agent as a nested tool for a trader."""

    researcher = await get_researcher(mcp_servers, model_name)

    async def log_research_output(result) -> str:
        output = str(result.final_output)
        write_log(account_name, "research", output)
        return output

    return researcher.as_tool(
        tool_name="Researcher",
        tool_description=research_tool(),
        custom_output_extractor=log_research_output,
    )


class Trader(TraderABC):
    def __init__(
        self,
        name: str,
        lastname: str = "Trader",
        model_name: str = "gpt-5.4-mini",
    ) -> None:
        self.name = name
        self.lastname = lastname
        self.model_name = model_name
        self.agent: Agent | None = None
        self.do_trade = True

    async def create_agent(
        self,
        trader_servers,
        researcher_servers,
    ) -> Agent:
        """Create the trading agent with a nested researcher tool."""

        researcher_tool = await get_researcher_tool(
            researcher_servers,
            self.model_name,
            self.name,
        )
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions(self.name),
            model=get_model(self.model_name),
            tools=[researcher_tool],
            mcp_servers=trader_servers,
        )
        return self.agent

    async def get_account_report(self) -> str:
        """Read and compact the account report before prompt injection."""

        account_report = await read_accounts_resource(self.name)
        account_json = json.loads(account_report)
        account_json.pop("portfolio_values", None)
        account_json.pop("portfolio_value_time_series", None)
        return json.dumps(account_json, sort_keys=True)

    async def run_agent(self, trader_servers, researcher_servers) -> str:
        """Run one trade or rebalance turn using already-open MCP servers."""

        agent = await self.create_agent(trader_servers, researcher_servers)
        account = await self.get_account_report()
        strategy = await read_strategy_resource(self.name)
        message = (
            trade_message(self.name, strategy, account)
            if self.do_trade
            else rebalance_message(self.name, strategy, account)
        )
        result = await Runner.run(agent, message, max_turns=MAX_TURNS)
        return str(result.final_output)

    async def run_with_mcp_servers(self) -> str:
        """Open trader and researcher MCP servers for one agent run."""

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

    async def run_with_trace(self) -> str:
        """Run the trader inside an Agents SDK trace."""

        trace_name = (
            f"{self.name}-trading"
            if self.do_trade
            else f"{self.name}-rebalancing"
        )
        trace_id = make_trace_id(self.name.lower())
        with trace(trace_name, trace_id=trace_id):
            return await self.run_with_mcp_servers()

    async def run(self) -> str:
        """Run one trader cycle and toggle between trade and rebalance modes."""

        try:
            return await self.run_with_trace()
        except Exception as exc:
            message = f"Error running trader {self.name}: {exc}"
            print(message)
            return message
        finally:
            self.do_trade = not self.do_trade
