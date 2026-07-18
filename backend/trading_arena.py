from __future__ import annotations

import asyncio
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from agents import add_trace_processor
from dotenv import load_dotenv

from backend.roster import TRADER_PROFILES, resolve_model_names
from backend.tracers import LogTracer
from backend.traders import Trader


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "60"))
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower()
    == "true"
)
USE_MANY_MODELS = (
    os.getenv("USE_MANY_MODELS", "false").strip().lower() == "true"
)

names = [profile.name for profile in TRADER_PROFILES]
lastnames = [profile.lastname for profile in TRADER_PROFILES]
model_names = resolve_model_names(USE_MANY_MODELS)


def is_market_open() -> bool:
    """Return whether the regular US stock market session is open now."""

    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    return time(9, 30) <= now.time() < time(16, 0)


def create_traders() -> list[Trader]:
    """Create trader instances from the configured roster."""

    return [
        Trader(profile.name, profile.lastname, model_name)
        for profile, model_name in zip(TRADER_PROFILES, model_names)
    ]


async def run_every_n_minutes() -> None:
    """Run all traders on a fixed interval while the scheduler is active."""

    add_trace_processor(LogTracer())
    traders = create_traders()

    while True:
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED or is_market_open():
            await asyncio.gather(*(trader.run() for trader in traders))
        else:
            print("Market is closed, skipping trader run")

        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)


if __name__ == "__main__":
    print(f"Starting trading arena every {RUN_EVERY_N_MINUTES} minutes")
    asyncio.run(run_every_n_minutes())
