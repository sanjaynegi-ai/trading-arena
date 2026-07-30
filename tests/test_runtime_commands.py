from __future__ import annotations

import os
import unittest
from pathlib import Path

from backend.runtime_commands import with_local_bin_path


class RuntimeCommandsTests(unittest.TestCase):
    def test_local_bin_path_is_prepended(self) -> None:
        path_value = f"/usr/bin{os.pathsep}/bin"
        environment = with_local_bin_path({"PATH": path_value})

        self.assertEqual(
            environment["PATH"].split(os.pathsep)[0],
            str(Path.home() / ".local" / "bin"),
        )


if __name__ == "__main__":
    unittest.main()
