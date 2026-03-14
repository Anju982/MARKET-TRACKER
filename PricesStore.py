from datetime import datetime
from typing import Dict, Optional, Any
import logging

from config import SYMBOL_MAP

logger = logging.getLogger(__name__)

class PricesStore:
    """
    In-memory store for the latest market prices and changes.
    Optimized for asyncio (no threading locks required if updated in event loop).
    """
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}

    def update(self, raw_symbol: str, price: float, volume: float, ts_ms: int):
        """
        Updates the store with a new trade record.
        Calculates change and percentage change relative to the previous stored price.
        """
        name = SYMBOL_MAP.get(raw_symbol, raw_symbol)
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        time_str = dt.strftime("%H:%M:%S")
        date_str = dt.strftime("%Y-%m-%d")

        prev = self.data.get(name, {})
        # Use previous price to calculate change. 
        prev_price = prev.get("price", price)
        change = price - prev_price 
        change_pct = (change / prev_price) * 100 if prev_price != 0 else 0
        
        self.data[name] = {
            "symbol": name,
            "raw_symbol": raw_symbol,
            "price": price,
            "volume": volume,
            "time": time_str,
            "date": date_str,
            "timestamp_ms": ts_ms,
            "change": round(change, 6),
            "change_pct": round(change_pct, 4),
            "direction": "up" if change >= 0 else "down",
        }
            
    def update_error(self, raw_symbol: str, error_msg: str):
        """Stores an error message for a symbol."""
        name = SYMBOL_MAP.get(raw_symbol, raw_symbol)
        if name not in self.data:
            self.data[name] = {"symbol": name, "raw_symbol": raw_symbol}
        self.data[name]["error"] = error_msg
        self.data[name]["timestamp_ms"] = int(datetime.now().timestamp() * 1000)

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Returns all current price records."""
        return self.data

    def get_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """Returns the latest price record for a specific symbol name."""
        return self.data.get(name)
