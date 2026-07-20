from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import database
from backend.accounts import Account
from dashboard.ui import LeaderboardView, Trader, TraderView


class LeaderboardRefreshTests(unittest.TestCase):
    def test_refresh_returns_latest_persisted_account_value(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            try:
                database.DB_PATH = Path(temp_dir) / "accounts.db"
                database._init_db()

                with patch("backend.accounts.get_share_price", return_value=100.0):
                    account = Account.get("Sanjay")
                    account.reset()

                    leaderboard = LeaderboardView(
                        [Trader("Sanjay", "Negi", "test-model")]
                    )
                    first_update = leaderboard.refresh()
                    self.assertIn("$50,000.00", first_update["value"])

                    account.deposit(1234.0)

                    second_update = leaderboard.refresh()
                    self.assertIn("$51,234.00", second_update["value"])
                    self.assertNotEqual(first_update["value"], second_update["value"])
            finally:
                database.DB_PATH = original_db_path


class TraderPanelRefreshTests(unittest.TestCase):
    def test_refresh_returns_latest_transactions_after_second_sell(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            try:
                database.DB_PATH = Path(temp_dir) / "accounts.db"
                database._init_db()

                with patch("backend.accounts.get_share_price", return_value=10.0):
                    account = Account.get("Neil")
                    account.reset()
                    account.buy_shares("VERA", 400.0, "buy")
                    account.sell_shares("VERA", 100.0, "first trim")

                    view = TraderView(Trader("Neil", "Sharma", "test-model"))
                    first_refresh = view.refresh()
                    self.assertEqual([["VERA", 300.0]], first_refresh[1]["value"])
                    self.assertEqual(2, len(first_refresh[2]["value"]))

                    account = Account.get("Neil")
                    account.sell_shares("VERA", 100.0, "second trim")

                    second_refresh = view.refresh()
                    holdings = second_refresh[1]["value"]
                    transactions = second_refresh[2]["value"]

                    self.assertEqual([["VERA", 200.0]], holdings)
                    self.assertEqual(3, len(transactions))
                    self.assertEqual(["sell", "sell"], [row[1] for row in transactions[-2:]])
                    self.assertEqual([100.0, 100.0], [row[3] for row in transactions[-2:]])
            finally:
                database.DB_PATH = original_db_path


if __name__ == "__main__":
    unittest.main()
