from __future__ import annotations

import subprocess

from backend.accounts import Account
from backend.market import get_share_price


def main() -> None:
    print("Resetting roster accounts...")
    subprocess.run(["uv", "run", "-m", "backend.reset"], check=True)

    print("Importing FastAPI app...")
    from backend.api import app

    print(f"API title: {app.title}")

    print("Generating Warren account report...")
    report = Account.get("Warren").report()
    print(report)

    print("Looking up AAPL share price...")
    price = get_share_price("AAPL")
    print(f"AAPL: {price:.2f}")

    print("Start the API with:")
    print("uv run uvicorn backend.api:app --port 8000")


if __name__ == "__main__":
    main()
