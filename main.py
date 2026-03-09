import asyncio
import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional
import websocket
from fastapi import FastAPI
from dotenv import load_dotenv
from config import SYMBOL_MAP, CATEGORIES
from PricesStore import PricesStore
from WebSocket import WebSocketManager
from NewsStore import NewsStore
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tracked_symbols": len(SYMBOL_MAP),
        "active_prices": len(price_store.get_all()),
        "ws_token_configured": bool(finhubAPIkey),
    }