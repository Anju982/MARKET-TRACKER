import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

# Mapping from Finnhub/Internal symbols to Yahoo Finance tickers
YFINANCE_TICKERS = {
    "OANDA:XAU_USD":    "GC=F",   # Gold
    "OANDA:XAG_USD":    "SI=F",   # Silver
    "OANDA:BCO_USD":    "BZ=F",   # Brent Crude
    "OANDA:WTICO_USD":  "CL=F",   # WTI Crude
    "OANDA:NATGAS_USD": "NG=F",   # Natural Gas
    "OANDA:XCU_USD":    "HG=F",   # Copper
    "OANDA:WHEAT_USD":  "ZW=F",   # Wheat
    "OANDA:CORN_USD":   "ZC=F",   # Corn
    "OANDA:SOYBN_USD":  "ZS=F",   # Soybeans
    "OANDA:SUGAR_USD":  "SB=F",   # Sugar
    "OANDA:XPT_USD":    "PL=F",   # Platinum
    "OANDA:XPD_USD":    "PA=F",   # Palladium
    "BINANCE:BTCUSDT":  "BTC-USD",
    "BINANCE:ETHUSDT":  "ETH-USD",
    "BINANCE:SOLUSDT":  "SOL-USD",
    "OANDA:USB10Y_USD": "^TNX",   # US 10Y
    "OANDA:USB30Y_USD": "^TYX",   # US 30Y
    "OANDA:US30_USD":   "^DJI",   # Dow Jones
    "OANDA:NAS100_USD": "^IXIC",  # Nasdaq
    "OANDA:SPX500_USD": "^GSPC",  # S&P 500
    "OANDA:DE30_EUR":   "^GDAXI", # DAX
    "OANDA:UK100_GBP":  "^FTSE",  # FTSE 100
    "OANDA:VIX_USD":    "^VIX",   # VIX
    "OANDA:USDOLLAR":   "DX=F",   # US Dollar Index
}

def get_historical_prices(symbol: str, start: datetime, end: datetime, api_token: Optional[str] = None) -> List[Dict]:
    """
    Fetch historical prices (candles) using yfinance.
    Returns a list of { "date": ISO8601, "price": float }.
    """
    ticker = YFINANCE_TICKERS.get(symbol)
    if not ticker:
        # Fallback if symbol is already a ticker or not in map
        ticker = symbol.split(':')[-1] if ':' in symbol else symbol
    
    print(f"Fetching historical data for {symbol} using ticker {ticker}...")
    
    try:
        # Download data
        data = yf.download(ticker, start=start, end=end, progress=False)
        
        if data.empty:
            print(f"No data found for {ticker}")
            return []
            
        # Reformat
        result = []
        for index, row in data.iterrows():
            # index is the Date
            # Row has Open, High, Low, Close, Adj Close, Volume
            # Use 'Adj Close' or 'Close'
            price = float(row['Close'])
            result.append({
                "date": index.strftime("%Y-%m-%dT%H:%M:%S"),
                "price": price
            })
            
        print(f"Retrieved {len(result)} data points for {ticker}")
        return result
        
    except Exception as e:
        print(f"Error fetching historical data for {ticker}: {e}")
        return []

if __name__ == "__main__":
    # Test
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    res = get_historical_prices("OANDA:XAU_USD", start, end)
    print(res[:5])