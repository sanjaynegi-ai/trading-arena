Account management system for a trading simulation platform.

Users can:
- Create an account
- Deposit and withdraw cash
- Record buying or selling shares (with quantity)

The system can report, at any time:
- Total portfolio value
- Profit or loss compared to the original deposit
- Current share holdings
- Full transaction history

Rules the system must enforce:
- Can't withdraw more cash than the account holds
- Can't buy more shares than the account can afford
- Can't sell shares the account doesn't hold

Share prices come from a function `get_share_price(ticker)`.

Current implementation note: `backend.market.get_share_price(symbol)` uses
Yahoo Finance through `yfinance`. It normalizes the ticker, tries fast price
data first, then falls back to recent historical close prices. The original
course requirement expected fixed test prices for a small set of symbols, but
this implementation now supports any ticker Yahoo Finance can price.
