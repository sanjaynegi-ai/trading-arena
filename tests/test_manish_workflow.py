from __future__ import annotations

import asyncio
import unittest

from backend.manish_trader import ManishTrader
from backend.mcp_servers import MANISH_MARKET_TOOL_NAMES, manish_trader_mcp_servers
from backend.researchers.manish_research_team import (
    _compact_specialist_output,
    get_research_coordinator,
    risk_researcher_instructions,
)
from backend.runtime_commands import with_local_bin_path
from backend.traders import Trader
from backend.trading_arena import create_traders


class ManishWorkflowTests(unittest.TestCase):
    def test_scheduler_uses_custom_trader_only_for_manish(self) -> None:
        traders = {trader.name: trader for trader in create_traders()}

        self.assertIsInstance(traders["Manish"], ManishTrader)
        self.assertIs(type(traders["Sanjay"]), Trader)
        self.assertIs(type(traders["Neil"]), Trader)

    def test_manish_market_tools_are_small_and_expected(self) -> None:
        self.assertEqual(
            MANISH_MARKET_TOOL_NAMES,
            [
                "get_current_stock_price",
                "get_historical_stock_prices",
                "get_news",
                "get_earning_dates",
                "get_income_statement",
            ],
        )
        self.assertEqual(len(manish_trader_mcp_servers()), 2)

    def test_research_coordinator_has_no_direct_tools(self) -> None:
        coordinator = asyncio.run(get_research_coordinator("gpt-5.4-mini"))

        self.assertEqual(coordinator.name, "Manish Research Coordinator")
        self.assertEqual(coordinator.tools, [])

    def test_risk_researcher_is_research_only(self) -> None:
        instructions = " ".join(risk_researcher_instructions().split())

        self.assertIn("Do not recommend or execute trades", instructions)

    def test_specialist_output_is_compacted(self) -> None:
        long_output = "x" * 2_100
        compacted = _compact_specialist_output(long_output)

        self.assertIn("Brief truncated for synthesis", compacted)
        self.assertLess(len(compacted), len(long_output))

    def test_local_bin_path_is_prepended(self) -> None:
        environment = with_local_bin_path({"PATH": "/usr/bin:/bin"})

        self.assertTrue(environment["PATH"].split(":")[0].endswith("/.local/bin"))


if __name__ == "__main__":
    unittest.main()
