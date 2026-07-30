from __future__ import annotations

import asyncio
import unittest

from backend.accounts import Account
from backend.gaurav_trader import GauravTrader
from backend.mcp_servers import researcher_mcp_servers, trader_mcp_servers
from backend.roster import TRADER_PROFILES
from backend.trading_arena import create_traders


class GauravTraderTests(unittest.TestCase):
    def test_scheduler_creates_gaurav_trader(self) -> None:
        traders = {trader.name: trader for trader in create_traders()}

        self.assertIn("Gaurav", traders)
        self.assertIsInstance(traders["Gaurav"], GauravTrader)

    def test_gaurav_account_and_strategy_are_initialized(self) -> None:
        profile = next(profile for profile in TRADER_PROFILES if profile.name == "Gaurav")
        account = Account.get("Gaurav")
        account.reset(profile.strategy)

        self.assertEqual(account.name, "gaurav")
        self.assertEqual(account.balance, 50000.0)
        self.assertEqual(account.holdings, {})
        self.assertIn(profile.strategy, account.strategy)

    def test_gaurav_agent_can_be_created(self) -> None:
        trader = GauravTrader("Gaurav", "Jain", "gpt-5.4-mini")

        async def build_agent() -> None:
            agent = await trader.create_agent([], [])
            self.assertIsNotNone(agent)
            self.assertEqual(agent.name, trader.name)
            self.assertTrue(
                any(
                    getattr(tool, "name", None) == "GauravResearcher"
                    for tool in agent.tools or []
                )
            )

        asyncio.run(build_agent())


if __name__ == "__main__":
    unittest.main()
