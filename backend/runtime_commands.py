"""Resolve optional local command-line tools used by MCP subprocesses."""

from __future__ import annotations

from pathlib import Path
from shutil import which


def resolve_command(command: str) -> str:
    """Return a runnable command path, including the common local uv location."""

    discovered = which(command)
    if discovered:
        return discovered

    local_command = Path.home() / ".local" / "bin" / command
    if local_command.is_file():
        return str(local_command)

    return command


def with_local_bin_path(environment: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment that can run tools installed under ``~/.local/bin``."""

    env = dict(environment or {})
    local_bin = str(Path.home() / ".local" / "bin")
    path_entries = env.get("PATH", "").split(":")
    if local_bin not in path_entries:
        env["PATH"] = ":".join(
            [local_bin, *[entry for entry in path_entries if entry]]
        )
    return env
