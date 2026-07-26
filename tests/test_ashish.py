import asyncio
from backend.ashish_trader import AshishTrader

async def main():
    trader = AshishTrader("Ashish", "Bhutani", "gpt-5.5")
    result = await trader.run()
    print("Test result:", result)

asyncio.run(main())
