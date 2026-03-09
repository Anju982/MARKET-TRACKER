import asyncio
import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional
import websocket
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from config import SYMBOL_MAP, CATEGORIES
from PricesStore import PricesStore
from WebSocket import WebSocketManager
from NewsStore import NewsStore
from historical import get_historical_prices
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from datetime import timedelta

app = FastAPI(title="Live Market Data API", version="1.0.0", description="API for fetching live market data")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


load_dotenv()

finhubAPIkey = os.getenv("FinHubAPI")


price_store = PricesStore()
websocket_manager = WebSocketManager(symbols=list(SYMBOL_MAP.keys()), store=price_store, FINNHUB_TOKEN=finhubAPIkey)

news_store = NewsStore(api_token=finhubAPIkey)

# ── Historical Data Cache ───────────────────────────────────────────────────
# Simple cache: { (symbol, range_str): (timestamp, data) }
historical_cache = {}
CACHE_TTL = timedelta(minutes=60)

RANGE_MAP = {
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "5Y": timedelta(days=365*5),
    "MAX": timedelta(days=365*10), # Default to 10 years for MAX
}

@app.on_event("startup")
def startup():
    websocket_manager.start_websocket()

@app.get("/prices")
def get_all_prices():
    """Return latest prices for every tracked symbol."""
    return {
        "data": price_store.get_all(),
        "categories": CATEGORIES,
        "server_time": datetime.now().isoformat() + "Z"
    }

@app.get("/prices/{symbol_name}")
def get_symbol_price(symbol_name: str):
    """Return latest price for a single symbol (use readable name, URL-encoded)."""
    record = price_store.get_symbol(symbol_name)
    if record is None:
        return {"error": f"Symbol '{symbol_name}' not found or no data yet."}
    return record


@app.get("/news")
def get_news(since_timestamp: Optional[str] = None):
    """Return news strictly newer than since_timestamp (optional)."""
    return news_store.get_news_since(since_timestamp)


@app.get("/api/historical")
def get_historical(
    symbol: str, 
    range: str = "1Y"
):
    """Return historical prices for a symbol."""
    # Validate symbol - it needs to be the OANDA:... or BINANCE:... key
    # If the user sends the readable name (GOLD), we need to reverse map it.
    actual_symbol = None
    for sym_key, name in SYMBOL_MAP.items():
        if name.upper() == symbol.upper() or sym_key.upper() == symbol.upper():
            actual_symbol = sym_key
            break
            
    if not actual_symbol:
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}")
        
    range_delta = RANGE_MAP.get(range.upper(), RANGE_MAP["1Y"])
    end_date = datetime.now()
    start_date = end_date - range_delta
    
    # Check cache
    cache_key = (actual_symbol, range.upper())
    now = datetime.now()
    if cache_key in historical_cache:
        ts, cached_data = historical_cache[cache_key]
        if now - ts < CACHE_TTL:
            return {"symbol": symbol, "range": range, "data": cached_data, "cached": True}
            
    # Fetch from Finnhub
    data = get_historical_prices(actual_symbol, start_date, end_date, finhubAPIkey)
    
    if data:
        historical_cache[cache_key] = (now, data)
        return {"symbol": symbol, "range": range, "data": data, "cached": False}
    else:
        raise HTTPException(status_code=404, detail="Failed to fetch historical data or no data available.")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tracked_symbols": len(SYMBOL_MAP),
        "active_prices": len(price_store.get_all()),
        "ws_token_configured": bool(finhubAPIkey),
    }