from __future__ import annotations

import importlib
import unittest


class DashboardImportTests(unittest.TestCase):
    def test_dashboard_module_imports_without_missing_trader_module(self) -> None:
        module = importlib.import_module("backend.trading_arena")
        self.assertTrue(hasattr(module, "names"))


if __name__ == "__main__":
    unittest.main()
