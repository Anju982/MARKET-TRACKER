import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import SYMBOL_MAP, CATEGORIES, WS_EXCLUDED_SYMBOLS
from PricesStore import PricesStore
from WebSocket import WebSocketManager
from NewsStore import NewsStore
from historical import get_historical_prices

# ── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Load Environment ────────────────────────────────────────────────────────
load_dotenv()
finhub_api_key = os.getenv("FinHubAPI")

# ── Global Stores ───────────────────────────────────────────────────────────
price_store = PricesStore()
news_store = NewsStore(api_token=finhub_api_key)

# WebSocket symbols
ws_symbols = [
    s for s in SYMBOL_MAP.keys()
    if (s.startswith("OANDA:") or s.startswith("BINANCE:"))
    and s not in WS_EXCLUDED_SYMBOLS
]
# Yahoo-polled symbols
yahoo_symbols = [s for s in SYMBOL_MAP.keys() if s not in ws_symbols]

websocket_manager = WebSocketManager(
    symbols=ws_symbols,
    store=price_store,
    FINNHUB_TOKEN=finhub_api_key,
    excluded_symbols=WS_EXCLUDED_SYMBOLS,
)

# ── Historical Cache ────────────────────────────────────────────────────────
historical_cache = {}
CACHE_TTL = timedelta(minutes=60)
MAX_CACHE_ENTRIES = 20  # Limit memory usage for GCP Free Tier

RANGE_MAP = {
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "5Y": timedelta(days=365*5),
    "MAX": timedelta(days=365*10),
}

import yfinance as yf
def get_current_yahoo_price(symbol: str) -> Optional[Dict]:
    """Fetch current price via yfinance. Runs in executor."""
    from historical import YFINANCE_TICKERS
    ticker = YFINANCE_TICKERS.get(symbol, symbol)
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, 'last_price', None) or getattr(info, 'regular_market_price', None)

        if price is None:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])

        if price is not None and float(price) > 0:
            return {
                "p": float(price),
                "v": 0.0,
                "t": int(datetime.now().timestamp() * 1000),
            }
    except Exception as e:
        logger.error(f"[Yahoo] Error polling {symbol}: {e}")
    return None

# ── Background Tasks ────────────────────────────────────────────────────────
async def news_fetcher_task():
    while True:
        try:
            await news_store.update_news()
        except Exception as e:
            logger.error(f"Error in news fetch: {e}")
        await asyncio.sleep(600)

async def yahoo_poller_task():
    while True:
        if not yahoo_symbols: break
        loop = asyncio.get_running_loop()
        for sym in yahoo_symbols:
            try:
                data = await loop.run_in_executor(None, get_current_yahoo_price, sym)
                if data:
                    price_store.update(raw_symbol=sym, price=data["p"], volume=data["v"], ts_ms=data["t"])
            except Exception as e:
                logger.error(f"Failed to poll {sym}: {e}")
        await asyncio.sleep(120)

async def cache_cleanup_task():
    while True:
        now = datetime.now()
        expired_keys = [k for k, (ts, _) in historical_cache.items() if now - ts > CACHE_TTL]
        for k in expired_keys:
            del historical_cache[k]
        
        # Enforce max size (FIFO-ish)
        if len(historical_cache) > MAX_CACHE_ENTRIES:
            sorted_keys = sorted(historical_cache.keys(), key=lambda k: historical_cache[k][0])
            to_remove = len(historical_cache) - MAX_CACHE_ENTRIES
            for i in range(to_remove):
                del historical_cache[sorted_keys[i]]
            logger.info(f"Historical cache capped. Removed {to_remove} old entries.")

        await asyncio.sleep(1800)

# ── Lifespan Manager ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    websocket_manager.start(loop)
    news_task = asyncio.create_task(news_fetcher_task())
    cleanup_task = asyncio.create_task(cache_cleanup_task())
    yahoo_task = asyncio.create_task(yahoo_poller_task())
    yield
    await websocket_manager.stop()
    for task in [news_task, cleanup_task, yahoo_task]:
        task.cancel()

# ── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Optimized Market API",
    version="1.2.0",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/prices")
async def get_all_prices():
    return {
        "data": price_store.get_all(),
        "categories": CATEGORIES,
        "server_time": datetime.now().isoformat() + "Z"
    }

@app.get("/news")
async def get_news(since_timestamp: Optional[str] = None):
    return news_store.get_news_since(since_timestamp)

@app.get("/api/historical")
async def get_historical(symbol: str, range: str = "1Y"):
    actual_symbol = next((k for k, v in SYMBOL_MAP.items() if v.upper() == symbol.upper() or k.upper() == symbol.upper()), None)
    if not actual_symbol:
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}")
        
    range_delta = RANGE_MAP.get(range.upper(), RANGE_MAP["1Y"])
    now = datetime.now()
    
    cache_key = (actual_symbol, range.upper())
    if cache_key in historical_cache:
        ts, cached_data = historical_cache[cache_key]
        if now - ts < CACHE_TTL:
            return {"symbol": symbol, "range": range, "data": cached_data, "cached": True}
            
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(None, get_historical_prices, actual_symbol, now - range_delta, now)
        if data:
            historical_cache[cache_key] = (now, data)
            return {"symbol": symbol, "range": range, "data": data, "cached": False}
        raise HTTPException(status_code=404, detail="No data available.")
    except Exception as e:
        logger.error(f"Error fetching historical: {e}")
        raise HTTPException(status_code=500, detail="Fetch failed.")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tracked_symbols": len(SYMBOL_MAP),
        "ws_active": websocket_manager._task is not None and not websocket_manager._task.done(),
    }
