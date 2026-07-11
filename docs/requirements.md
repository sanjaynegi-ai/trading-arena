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

Share prices come from a function get_share_price(ticker). For testing, this
function returns fixed prices for five symbols: MSFT, AAPL, AMZN, TSLA, GOOGL.
