from __future__ import annotations

import subprocess
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.runtime_commands import resolve_command


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVER_PARAMS = StdioServerParameters(
    command=resolve_command("uv"),
    args=["run", "-m", "backend.accounts_server"],
    cwd=PROJECT_ROOT,
    env=None,
)


async def _read_resource(uri: str) -> str:
    async with stdio_client(SERVER_PARAMS, errlog=subprocess.DEVNULL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(uri)
            return result.contents[0].text


async def read_accounts_resource(name: str) -> str:
    """Read the account report resource for an account name."""

    return await _read_resource(f"accounts://accounts_server/{name}")


async def read_strategy_resource(name: str) -> str:
    """Read the strategy resource for an account name."""

    return await _read_resource(f"accounts://strategy/{name}")
