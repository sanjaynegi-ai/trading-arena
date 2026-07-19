from __future__ import annotations

import asyncio
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from agents import add_trace_processor
from dotenv import load_dotenv

from backend.database import write_log
from backend.roster import TRADER_PROFILES, resolve_model_names
from backend.tracers import LogTracer
from backend.traders import Trader


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "15"))
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower()
    == "true"
)
SCHEDULER_TIME_WINDOW = os.getenv("SCHEDULER_TIME_WINDOW", "us_market").strip().lower()
USE_MANY_MODELS = (
    os.getenv("USE_MANY_MODELS", "false").strip().lower() == "true"
)

VALID_SCHEDULER_TIME_WINDOWS = {
    "us_market",
    "us_office",
    "india_office",
    "us_or_india_office",
    "always",
}

if SCHEDULER_TIME_WINDOW not in VALID_SCHEDULER_TIME_WINDOWS:
    raise ValueError(
        "SCHEDULER_TIME_WINDOW must be one of: "
        + ", ".join(sorted(VALID_SCHEDULER_TIME_WINDOWS))
    )

names = [profile.name for profile in TRADER_PROFILES]
lastnames = [profile.lastname for profile in TRADER_PROFILES]
model_names = resolve_model_names(USE_MANY_MODELS)


def is_market_open() -> bool:
    """Return whether the regular US stock market session is open now."""

    return _is_weekday_time_window_open(
        timezone_name="America/New_York",
        start=time(9, 30),
        end=time(16, 0),
    )


def _is_weekday_time_window_open(
    timezone_name: str,
    start: time,
    end: time,
) -> bool:
    now = datetime.now(ZoneInfo(timezone_name))
    if now.weekday() >= 5:
        return False
    return start <= now.time() < end


def is_us_office_hours_open() -> bool:
    """Return whether it is a weekday 9 AM-5 PM in New York."""

    return _is_weekday_time_window_open(
        timezone_name="America/New_York",
        start=time(9, 0),
        end=time(17, 0),
    )


def is_india_office_hours_open() -> bool:
    """Return whether it is a weekday 9 AM-5 PM in India."""

    return _is_weekday_time_window_open(
        timezone_name="Asia/Kolkata",
        start=time(9, 0),
        end=time(17, 0),
    )


def is_scheduler_window_open() -> bool:
    """Return whether the configured scheduler time window allows a trader run."""

    if RUN_EVEN_WHEN_MARKET_IS_CLOSED or SCHEDULER_TIME_WINDOW == "always":
        return True
    if SCHEDULER_TIME_WINDOW == "us_market":
        return is_market_open()
    if SCHEDULER_TIME_WINDOW == "us_office":
        return is_us_office_hours_open()
    if SCHEDULER_TIME_WINDOW == "india_office":
        return is_india_office_hours_open()
    if SCHEDULER_TIME_WINDOW == "us_or_india_office":
        return is_us_office_hours_open() or is_india_office_hours_open()
    return False


def create_traders() -> list[Trader]:
    """Create trader instances from the configured roster."""

    return [
        Trader(profile.name, profile.lastname, model_name)
        for profile, model_name in zip(TRADER_PROFILES, model_names)
    ]


def _log(message: str) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{timestamp} {message}", flush=True)


def _write_trader_log(trader: Trader, log_type: str, message: str) -> None:
    try:
        write_log(trader.name, log_type, message)
    except Exception:
        pass


async def run_every_n_minutes() -> None:
    """Run all traders on a fixed interval while the scheduler is active."""

    add_trace_processor(LogTracer())
    traders = create_traders()
    _log(
        "Created traders: "
        + ", ".join(f"{trader.name} ({trader.model_name})" for trader in traders)
    )

    while True:
        market_open = is_market_open()
        scheduler_window_open = is_scheduler_window_open()
        _log(
            "Scheduler tick: "
            f"market_open={market_open}, "
            f"scheduler_time_window={SCHEDULER_TIME_WINDOW}, "
            f"scheduler_window_open={scheduler_window_open}, "
            f"run_when_closed={RUN_EVEN_WHEN_MARKET_IS_CLOSED}"
        )

        if scheduler_window_open:
            results = await asyncio.gather(*(trader.run() for trader in traders))
            for trader, result in zip(traders, results):
                _log(f"{trader.name} result: {result}")
                _write_trader_log(trader, "agent", f"Run result: {result}")
        else:
            message = (
                "Scheduler skipped run because "
                f"SCHEDULER_TIME_WINDOW={SCHEDULER_TIME_WINDOW} is closed."
            )
            _log(message)
            for trader in traders:
                _write_trader_log(trader, "trace", message)

        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)


if __name__ == "__main__":
    _log(f"Starting trading arena every {RUN_EVERY_N_MINUTES} minutes")
    asyncio.run(run_every_n_minutes())
