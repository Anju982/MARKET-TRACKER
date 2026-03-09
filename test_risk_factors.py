import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from historical import get_historical_prices

end = datetime.now()
start = end - timedelta(days=7)

symbols = ["OANDA:VIX_USD", "OANDA:USDOLLAR"]

for sym in symbols:
    print(f"\n--- Testing {sym} ---")
    data = get_historical_prices(sym, start, end)
    if data:
        print(f"Success! Found {len(data)} data points for {sym}")
        print(f"Sample data: {data[:2]}")
    else:
        print(f"Failed to fetch data for {sym}")
