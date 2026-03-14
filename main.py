import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import SYMBOL_MAP, CATEGORIES, WS_EXCLUDED_SYMBOLS
from PricesStore import PricesStore
from WebSocket import WebSocketManager
from NewsStore import NewsStore
from historical import get_historical_prices
from intelligence import get_intelligence_engine
from vision_agent import get_vision_agent
import technical
from fastapi.staticfiles import StaticFiles

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

# ── Caches ──────────────────────────────────────────────────────────────────
historical_cache = {}
intelligence_cache = {}
CACHE_TTL = timedelta(minutes=60)
INTEL_CACHE_TTL = timedelta(hours=6)
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

from pydantic import BaseModel

class ChatRequest(BaseModel):
    symbol: str
    query: str

@app.post("/api/chat")
async def chat_analyst(request: ChatRequest):
    """Interactive chat with the market analyst."""
    # Resolve to friendly name (e.g. "GOLD") or keep as is if not in map
    actual_symbol = SYMBOL_MAP.get(request.symbol.upper(), request.symbol.upper())
    
    # price_store.get_symbol returns a dict or None
    current_metrics = price_store.get_symbol(actual_symbol) or {}
    
    engine = get_intelligence_engine()
    if not engine.client:
        return {"symbol": request.symbol, "response": "💬 **Chat Offline**: Analyst AI is not connected. Configure `GEMINI_API_KEY`."}

    response = await engine.chat_with_analyst(actual_symbol, request.query, {"metrics": current_metrics})
    
    return {"symbol": request.symbol, "response": response}

@app.get("/api/intelligence")
async def get_intelligence(symbol: str):
    """
    Synthesize market intelligence for a given symbol.
    """
    # 1. Resolve actual symbol (e.g. "GOLD")
    actual_symbol = SYMBOL_MAP.get(symbol.upper(), symbol.upper())
    
    # 2. Check cache
    now = datetime.now()
    if actual_symbol in intelligence_cache:
        ts, cached_intel = intelligence_cache[actual_symbol]
        if now - ts < INTEL_CACHE_TTL:
            return {"symbol": symbol, "analysis": cached_intel, "cached": True}

    # 3. Fetch current metrics
    current_metrics = price_store.get_symbol(actual_symbol) or {}
    
    # 4. Resolve category
    category = next((cat for cat, syms in CATEGORIES.items() if actual_symbol.upper() in [s.upper() for s in syms]), "General")

    # 5. Fetch historical snapshot for context
    historical_data = []
    try:
        # Get the technical key for yfinance/oanda (e.g. "OANDA:XAU_USD")
        tech_key = next((k for k, v in SYMBOL_MAP.items() if v.upper() == actual_symbol.upper()), actual_symbol)
        loop = asyncio.get_running_loop()
        historical_data = await loop.run_in_executor(None, get_historical_prices, tech_key, now - timedelta(days=7), now)
    except Exception as e:
        logger.warning(f"Could not fetch historical for intel: {e}")

    # 6. Synthesize via engine
    try:
        engine = get_intelligence_engine()
        if not engine.client:
            return {"symbol": symbol, "analysis": "🤖 **Intelligence Terminal Offline**: `GEMINI_API_KEY` is not configured on the server. Please check environment variables.", "cached": False}
            
        analysis = await engine.synthesize_market_view(actual_symbol, category, current_metrics, historical_data)
        intelligence_cache[actual_symbol] = (now, analysis)
        return {"symbol": symbol, "analysis": analysis, "cached": False}
    except Exception as e:
        logger.error(f"Intelligence synthesis failed: {e}")
        return {"symbol": symbol, "analysis": f"⚠️ **Synthesis Error**: {str(e)}", "cached": False}

class VisionRequest(BaseModel):
    symbols: list[str]
    time_range: str = "3M"
    indicators: list[str] = ["SMA 20", "Bollinger Bands", "RSI 14"]
    
@app.post("/api/vision_analysis")
async def vision_analysis(request: VisionRequest):
    """
    Multimodal AI Analyst endpoint.
    Takes a list of symbols and indicator preferences, generates charts, and passes them to Gemini Vision.
    """
    engine = get_vision_agent()
    if not engine.client:
        return {"error": "Multimodal AI Analyst requires GEMINI_API_KEY environment variable."}
        
    actual_symbols = [SYMBOL_MAP.get(s.upper(), s.upper()) for s in request.symbols]
    
    try:
        results = await engine.batch_analyze(actual_symbols, request.time_range, request.indicators)
        
        # Format response
        response_data = []
        for sym, analysis, image_path in results:
            # Revert actual symbol back to requested symbol for frontend mapping if needed
            req_sym = next((s for s in request.symbols if SYMBOL_MAP.get(s.upper(), s.upper()) == sym), sym)
            
            # Use a static endpoint to serve the image, or return base64. 
            # Returning Base64 is easier without exposing the temp directory directly via static files over uvicorn
            image_base64 = None
            if image_path and os.path.exists(image_path):
                import base64
                with open(image_path, "rb") as image_file:
                    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Clean up the temp file after reading
                os.remove(image_path)
                    
            response_data.append({
                "symbol": req_sym,
                "analysis": analysis,
                "image_base64": image_base64
            })
            
        return {"results": response_data}
        
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return {"error": str(e)}

@app.get("/api/hydrate")
async def hydrate_asset(symbol: str, range: str = "1Y"):
    """
    Standardized pipeline for asset data hydration.
    Returns historical data, technical indicators, market intelligence, and vision analysis.
    """
    # 1. Resolve Symbols
    actual_symbol = next((k for k, v in SYMBOL_MAP.items() if v.upper() == symbol.upper() or k.upper() == symbol.upper()), None)
    if not actual_symbol:
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}")
    
    friendly_symbol = SYMBOL_MAP.get(actual_symbol, actual_symbol)
    
    # 2. Time Range
    range_delta = RANGE_MAP.get(range.upper(), RANGE_MAP["1Y"])
    now = datetime.now()
    start_date = now - range_delta
    
    try:
        # A. Data Layer: Historical Fetch
        loop = asyncio.get_running_loop()
        hist_data = await loop.run_in_executor(None, get_historical_prices, actual_symbol, start_date, now)
        
        if not hist_data:
            raise HTTPException(status_code=404, detail="No historical data found.")
            
        # B. Compute Layer: Technical Analysis
        df = pd.DataFrame(hist_data)
        df['date'] = pd.to_datetime(df['date'])
        df = technical.calculate_indicators(df)
        indicators = technical.get_latest_indicators(df)
        
        # C. Intelligence & Vision Layers (Concurrent Execution)
        # We'll use 3M range for Vision as per its default for better visual resolution
        vision_agent = get_vision_agent()
        intel_engine = get_intelligence_engine()
        
        category = next((cat for cat, syms in CATEGORIES.items() if friendly_symbol.upper() in [s.upper() for s in syms]), "General")
        current_metrics = price_store.get_symbol(friendly_symbol) or {}
        
        # We'll run Intel and Vision in parallel
        intel_task = intel_engine.synthesize_market_view(friendly_symbol, category, current_metrics, hist_data[-10:])
        vision_task = vision_agent.process_ticker_with_data(friendly_symbol, df, ["SMA 20", "Bollinger Bands", "RSI 14"])
        
        intel_res, vision_results = await asyncio.gather(intel_task, vision_task)
        
        # vision_results is (symbol, analysis, image_path)
        vis_sym, vis_analysis, vis_image_path = vision_results
        
        # Image handling
        image_base64 = None
        if vis_image_path and os.path.exists(vis_image_path):
            import base64
            with open(vis_image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            os.remove(vis_image_path)
            
        return {
            "symbol": friendly_symbol,
            "historical": hist_data,
            "technical": indicators,
            "intelligence": {
                "synthesis": intel_res
            },
            "vision": {
                "analysis": vis_analysis,
                "image_base64": image_base64
            },
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Hydration failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Hydration pipeline failed: {str(e)}")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tracked_symbols": len(SYMBOL_MAP),
        "ws_active": websocket_manager._task is not None and not websocket_manager._task.done(),
    }
