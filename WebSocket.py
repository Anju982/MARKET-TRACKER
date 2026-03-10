import asyncio
import json
import logging
from typing import List, Optional
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages an asynchronous WebSocket connection to Finnhub.
    """
    def __init__(self, symbols: List[str], store: "PricesStore", FINNHUB_TOKEN: str):
        self.symbols = symbols
        self.store = store
        self.FINNHUB_TOKEN = FINNHUB_TOKEN
        self.ws_url = f"wss://ws.finnhub.io?token={self.FINNHUB_TOKEN}"
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def _handle_messages(self, ws):
        async for message in ws:
            try:
                data = json.loads(message)
                if data.get("type") == "trade":
                    for trade in data.get("data", []):
                        self.store.update(
                            raw_symbol=trade.get("s", ""),
                            price=float(trade.get("p", 0)),
                            volume=float(trade.get("v", 0)),
                            ts_ms=int(trade.get("t", 0))
                        )
                elif data.get("type") == "error":
                    err_msg = data.get("msg", "Unknown API error")
                    logger.error(f"[WS] API Error: {err_msg}")
                    # If the error contains a symbol, update it in the store
                    sym = data.get("symbol")
                    if sym:
                        self.store.update_error(sym, err_msg)
                    else:
                        # Global error?
                        for s in self.symbols:
                            self.store.update_error(s, err_msg)
            except Exception as e:
                logger.error(f"[WS] Error processing message: {e}")

    async def _run(self):
        if not self.FINNHUB_TOKEN:
            logger.error("[WS] FINNHUB_TOKEN is not set")
            return

        reconnect_delay = 1
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url) as ws:
                    logger.info("[WS] Connected to Finnhub")
                    # Subscribe to symbols
                    for symbol in self.symbols:
                        await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                    
                    reconnect_delay = 1 # Reset delay on success
                    await self._handle_messages(ws)
            except (websockets.ConnectionClosed, Exception) as e:
                if self._stop_event.is_set():
                    break
                logger.warning(f"[WS] Connection lost ({e}). Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)

    def start(self, loop: asyncio.AbstractEventLoop):
        """Starts the WebSocket manager in the background of the given event loop."""
        self._stop_event.clear()
        self._task = loop.create_task(self._run())

    async def stop(self):
        """Stops the WebSocket manager."""
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[WS] Stopped")
