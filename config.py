from typing import Dict

# ── Symbol map ────────────────────────────────────────────────────────────────
SYMBOL_MAP: Dict[str, str] = {
    "OANDA:XAU_USD":    "GOLD",
    "OANDA:XAG_USD":    "SILVER",
    "OANDA:BCO_USD":    "BRENT OIL",
    "OANDA:WTICO_USD":  "WTI OIL",
    "OANDA:NATGAS_USD": "NAT GAS",
    "OANDA:XCU_USD":    "COPPER",
    "OANDA:WHEAT_USD":  "WHEAT",
    "OANDA:CORN_USD":   "CORN",
    "OANDA:SOYBN_USD":  "SOYBEANS",
    "OANDA:SUGAR_USD":  "SUGAR",
    "OANDA:XPT_USD":    "PLATINUM",
    "OANDA:XPD_USD":    "PALLADIUM",
    "OANDA:USB10Y_USD": "US 10Y NOTE",
    "OANDA:USB30Y_USD": "US 30Y BOND",
    "OANDA:UK10YB_GBP": "UK 10Y GILT",
    "OANDA:DE10YB_EUR": "GER 10Y BUND",
    "OANDA:US30_USD":   "DOW JONES",
    "OANDA:NAS100_USD": "NASDAQ 100",
    "OANDA:SPX500_USD": "S&P 500",
    "OANDA:DE30_EUR":   "DAX 30",
    "OANDA:UK100_GBP":  "UK 100",
    "BINANCE:BTCUSDT":  "BTC/USDT",
    "BINANCE:ETHUSDT":  "ETH/USDT",
    "BINANCE:SOLUSDT":  "SOLUSDT",
    "OANDA:VIX_USD":    "VIX",
    "OANDA:USDOLLAR":   "DXY",
}

CATEGORIES: Dict[str, list] = {
    "Commodities": [
        "GOLD", "SILVER", "BRENT OIL", "WTI OIL", "NAT GAS",
        "COPPER", "WHEAT", "CORN", "SOYBEANS", "SUGAR", "PLATINUM", "PALLADIUM",
    ],
    "Bonds": [
        "US 10Y NOTE", "US 30Y BOND", "UK 10Y GILT", "GER 10Y BUND",
    ],
    "Indices": [
        "DOW JONES", "NASDAQ 100", "S&P 500", "DAX 30", "UK 100",
    ],
    "Crypto": [
        "BTC/USDT", "ETH/USDT", "SOL/USDT",
    ],
    "Risk Factors": [
        "VIX", "DXY",
    ],
}
