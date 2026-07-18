from __future__ import annotations

from backend.accounts import Account
from backend.roster import TRADER_PROFILES


def reset_traders() -> None:
    """Reset every roster account to its starter strategy."""

    for profile in TRADER_PROFILES:
        Account.get(profile.name).reset(profile.strategy)


if __name__ == "__main__":
    reset_traders()
    print(f"Reset {len(TRADER_PROFILES)} trader accounts.")
