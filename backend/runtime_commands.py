"""Resolve optional local command-line tools used by MCP subprocesses."""

from __future__ import annotations

import os
from pathlib import Path
from shutil import which


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_command(command: str) -> str:
    """Return a runnable command path, including the project venv and local bin."""

    discovered = which(command)
    if discovered:
        return discovered

    local_command = Path.home() / ".local" / "bin" / command
    if local_command.is_file():
        return str(local_command)

    venv_bin = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    project_command = venv_bin / command
    if project_command.is_file():
        return str(project_command)

    return command


def with_local_bin_path(environment: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment that can run tools installed in the local bin and venv."""

    env = dict(environment or {})
    path_entries = [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]
    candidate_bins = [str(Path.home() / ".local" / "bin")]

    venv_bin = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    candidate_bins.append(str(venv_bin))

    for bin_dir in reversed(candidate_bins):
        if bin_dir not in path_entries:
            path_entries.insert(0, bin_dir)

    env["PATH"] = os.pathsep.join(path_entries)
    return env
