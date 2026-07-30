from __future__ import annotations

import os
import re
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from agents.mcp import MCPServerStdio, create_static_tool_filter

from backend.runtime_commands import resolve_command, with_local_bin_path


load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 120
UV_COMMAND = resolve_command("uv")
UVX_COMMAND = resolve_command("uvx")
NPX_COMMAND = resolve_command("npx")
MUKESH_MARKET_TOOL_NAMES = [
    "get_current_stock_price",
    "get_historical_stock_prices",
    "get_news",
    "get_earning_dates",
    "get_income_statement",
]
MANISH_MARKET_TOOL_NAMES = MUKESH_MARKET_TOOL_NAMES


def _env_with(**updates: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(updates)
    return with_local_bin_path(env)


def _project_cwd_params(command: str, args: list[str]) -> dict[str, object]:
    return {
        "command": command,
        "args": args,
        "cwd": str(PROJECT_ROOT),
        "env": _env_with(),
    }


async def open_mcp_servers(
    stack: AsyncExitStack,
    servers: list[MCPServerStdio],
) -> list[MCPServerStdio]:
    """Open MCP servers while skipping those that fail to initialize."""

    opened_servers: list[MCPServerStdio] = []
    for server in servers:
        try:
            opened_servers.append(await stack.enter_async_context(server))
        except Exception as exc:  # pragma: no cover - defensive runtime handling
            print(
                f"Warning: failed to initialize MCP server {type(server).__name__}: {exc}",
                flush=True,
            )
    return opened_servers


def _memory_db_name(name: str, lastname: str) -> str:
    raw_name = f"{name}_{lastname}".strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")
    return f"{cleaned or 'trader'}.db"


def trader_mcp_servers() -> list[MCPServerStdio]:
    """Return stdio MCP servers available to trading agents."""

    return [_accounts_mcp_server(), *market_mcp_servers()]


def manish_trader_mcp_servers() -> list[MCPServerStdio]:
    """Return Manish's account server plus a compact market-data tool set."""

    return [_accounts_mcp_server(), *focused_market_mcp_servers()]


def mukesh_trader_mcp_servers() -> list[MCPServerStdio]:
    """Backward-compatible alias for Manish's trader MCP server bundle."""

    return manish_trader_mcp_servers()


def manoj_trader_mcp_servers() -> list[MCPServerStdio]:
    """Return Manoj's account server plus a compact market-data tool set."""

    return [_accounts_mcp_server(), *focused_market_mcp_servers()]


def _accounts_mcp_server() -> MCPServerStdio:
    return MCPServerStdio(
        params=_project_cwd_params(
            UV_COMMAND,
            ["run", "-m", "backend.accounts_server"],
        ),
        client_session_timeout_seconds=TIMEOUT_SECONDS,
    )


def market_mcp_servers() -> list[MCPServerStdio]:
    """Return market-data-only servers that cannot execute account actions."""

    return [
        MCPServerStdio(
            params=_project_cwd_params(
                UV_COMMAND,
                ["run", "-m", "backend.market_server"],
            ),
            client_session_timeout_seconds=TIMEOUT_SECONDS,
        )
    ]


def focused_market_mcp_servers() -> list[MCPServerStdio]:
    """Return Mukesh's compact market-data tool set to limit model context."""

    return [
        MCPServerStdio(
            params=_project_cwd_params(
                UV_COMMAND,
                ["run", "-m", "backend.market_server"],
            ),
            client_session_timeout_seconds=TIMEOUT_SECONDS,
            tool_filter=create_static_tool_filter(
                allowed_tool_names=MUKESH_MARKET_TOOL_NAMES
            ),
        )
    ]


def _fetch_mcp_server() -> MCPServerStdio:
    """Return a fetch MCP server configured for the current mcp package version."""

    return MCPServerStdio(
        params={
            "command": UVX_COMMAND,
            "args": ["--with", "mcp<1", "mcp-server-fetch"],
            "env": _env_with(),
        },
        client_session_timeout_seconds=TIMEOUT_SECONDS,
    )


def researcher_mcp_servers(name: str, lastname: str) -> list[MCPServerStdio]:
    """Return stdio MCP servers available to a named research agent."""

    fetch = _fetch_mcp_server()
    search = MCPServerStdio(
        params={
            "command": NPX_COMMAND,
            "args": ["--yes", "--loglevel=error", "tavily-mcp@latest"],
            "env": _env_with(TAVILY_API_KEY=os.getenv("TAVILY_API_KEY", "")),
        },
        client_session_timeout_seconds=TIMEOUT_SECONDS,
        tool_filter=create_static_tool_filter(
            allowed_tool_names=["tavily_search"]
        ),
    )
    memory = MCPServerStdio(
        params={
            "command": NPX_COMMAND,
            "args": ["--yes", "--loglevel=error", "mcp-memory-libsql"],
            "cwd": str(PROJECT_ROOT),
            "env": _env_with(
                LIBSQL_URL=f"file:./memory/{_memory_db_name(name, lastname)}"
            ),
        },
        client_session_timeout_seconds=TIMEOUT_SECONDS,
    )
    return [fetch, search, memory]
