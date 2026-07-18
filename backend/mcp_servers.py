from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from agents.mcp import MCPServerStdio, create_static_tool_filter


load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 120


def _env_with(**updates: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(updates)
    return env


def _project_cwd_params(command: str, args: list[str]) -> dict[str, object]:
    return {
        "command": command,
        "args": args,
        "cwd": str(PROJECT_ROOT),
    }


def trader_mcp_servers() -> list[MCPServerStdio]:
    """Return stdio MCP servers available to trading agents."""

    params = [
        _project_cwd_params("uv", ["run", "-m", "backend.accounts_server"]),
        {"command": "uvx", "args": ["mcp-yahoo-finance"]},
    ]
    return [
        MCPServerStdio(
            params=server_params,
            client_session_timeout_seconds=TIMEOUT_SECONDS,
        )
        for server_params in params
    ]


def researcher_mcp_servers(name: str) -> list[MCPServerStdio]:
    """Return stdio MCP servers available to a named research agent."""

    fetch = MCPServerStdio(
        params={"command": "uvx", "args": ["mcp-server-fetch"]},
        client_session_timeout_seconds=TIMEOUT_SECONDS,
    )
    search = MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "tavily-mcp@latest"],
            "env": _env_with(TAVILY_API_KEY=os.getenv("TAVILY_API_KEY", "")),
        },
        client_session_timeout_seconds=TIMEOUT_SECONDS,
        tool_filter=create_static_tool_filter(
            allowed_tool_names=["tavily_search"]
        ),
    )
    memory = MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "cwd": str(PROJECT_ROOT),
            "env": _env_with(LIBSQL_URL=f"file:./memory/{name}.db"),
        },
        client_session_timeout_seconds=TIMEOUT_SECONDS,
    )
    return [fetch, search, memory]
