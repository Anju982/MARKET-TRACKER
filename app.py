"""
Live Market Data Dashboard – Streamlit Frontend
Polls the FastAPI backend every N seconds and displays live prices.
"""

import os
import time
from datetime import datetime

import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_SECS", "3"))

CATEGORY_ICONS = {
    "Commodities": "🏅",
    "Bonds": "📊",
    "Indices": "📈",
    "Crypto": "🪙",
}

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live Market Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'JetBrains Mono', monospace;
        background-color: #080c14;
        color: #c9d8e8;
    }

    /* ── Main background ── */
    .stApp {
        background: radial-gradient(ellipse at top left, #0d1b2e 0%, #080c14 60%);
    }

    /* ── Header ── */
    .dash-header {
        display: flex;
        align-items: baseline;
        gap: 18px;
        padding: 18px 0 10px 0;
        border-bottom: 1px solid #1a2a40;
        margin-bottom: 24px;
    }
    .dash-title {
        font-family: 'Syne', sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -1px;
        color: #e8f4ff;
        margin: 0;
    }
    .dash-subtitle {
        font-size: 0.72rem;
        color: #4a6a8a;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    .live-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #00e5a0;
        box-shadow: 0 0 8px #00e5a0;
        animation: pulse 1.4s ease-in-out infinite;
        margin-right: 6px;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.5; transform: scale(1.5); }
    }

    /* ── Category header ── */
    .cat-header {
        font-family: 'Syne', sans-serif;
        font-size: 0.7rem;
        letter-spacing: 4px;
        text-transform: uppercase;
        color: #3a5a7a;
        border-left: 3px solid #1e4060;
        padding-left: 10px;
        margin: 28px 0 14px 0;
    }

    /* ── Price card ── */
    .price-card {
        background: linear-gradient(135deg, #0d1e30 0%, #0a1622 100%);
        border: 1px solid #162336;
        border-radius: 10px;
        padding: 14px 16px;
        transition: border-color 0.2s, box-shadow 0.2s;
        position: relative;
        overflow: hidden;
    }
    .price-card:hover {
        border-color: #2a5080;
        box-shadow: 0 0 18px rgba(0, 140, 255, 0.08);
    }
    .price-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #1e4060, transparent);
    }
    .card-symbol {
        font-size: 0.65rem;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #3a6080;
        margin-bottom: 6px;
    }
    .card-price {
        font-family: 'Syne', sans-serif;
        font-size: 1.45rem;
        font-weight: 700;
        color: #d8eeff;
        letter-spacing: -0.5px;
        line-height: 1;
    }
    .card-change-up {
        font-size: 0.72rem;
        color: #00e5a0;
        margin-top: 5px;
    }
    .card-change-down {
        font-size: 0.72rem;
        color: #ff4d6a;
        margin-top: 5px;
    }
    .card-time {
        font-size: 0.6rem;
        color: #2a4a6a;
        margin-top: 6px;
    }
    .card-vol {
        font-size: 0.6rem;
        color: #2a4a6a;
    }
    .no-data {
        color: #2a4060;
        font-size: 0.8rem;
        padding: 6px 0;
    }

    /* ── Status bar ── */
    .status-bar {
        display: flex;
        justify-content: space-between;
        font-size: 0.62rem;
        color: #2a4060;
        letter-spacing: 1.5px;
        border-top: 1px solid #101e2e;
        padding-top: 10px;
        margin-top: 30px;
    }

    /* ── Sidebar / controls ── */
    div[data-testid="stSidebar"] { background: #060a10; }

    /* hide streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_prices() -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/prices", timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "data": {}, "categories": {}}

def fetch_news(since=None) -> dict:
    url = f"{BACKEND_URL}/news"
    if since:
        url += f"?since_timestamp={since}"
    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"items": [], "scraped_at": None, "error": str(e)}


def fmt_price(price: float, symbol: str) -> str:
    if symbol in {"BTC/USDT", "ETH/USDT"}:
        return f"{price:,.2f}"
    if price >= 10_000:
        return f"{price:,.1f}"
    if price >= 100:
        return f"{price:,.2f}"
    return f"{price:,.4f}"


def render_card(record: dict) -> str:
    symbol  = record["symbol"]
    price   = record["price"]
    chg     = record.get("change", 0)
    chg_pct = record.get("change_pct", 0)
    vol     = record.get("volume", 0)
    t       = record.get("time", "—")
    arrow   = "▲" if chg >= 0 else "▼"
    cls     = "card-change-up" if chg >= 0 else "card-change-down"

    return f"""
    <div class="price-card">
        <div class="card-symbol">{symbol}</div>
        <div class="card-price">{fmt_price(price, symbol)}</div>
        <div class="{cls}">{arrow} {abs(chg_pct):.3f}%</div>
        <div class="card-time">🕐 {t}</div>
        <div class="card-vol">vol {vol:,.4f}</div>
    </div>
    """


def render_no_data() -> str:
    return '<div class="price-card"><div class="no-data">⏳ Waiting for data…</div></div>'


# ── Main render ───────────────────────────────────────────────────────────────
# Header
st.markdown(
    """
    <div class="dash-header">
        <div>
            <div class="dash-title">📡 MARKET TRACKER</div>
            <div class="dash-subtitle"><span class="live-dot"></span>Live prices · Finnhub WebSocket</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar controls
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    refresh = st.slider("Refresh (seconds)", 1, 30, REFRESH_INTERVAL)
    st.markdown("---")
    st.markdown("**Backend**")
    st.code(BACKEND_URL)
    if st.button("🔄 Force refresh"):
        st.rerun()

# Fetch
payload = fetch_prices()
prices  = payload.get("data", {})
cats    = payload.get("categories", {})
err     = payload.get("error")

if err:
    st.error(f"⚠️ Cannot reach backend: {err}")
    st.info(f"Make sure the FastAPI server is running at `{BACKEND_URL}`")
    time.sleep(3)
    st.rerun()

# News fetching
if "news_items" not in st.session_state:
    st.session_state.news_items = []
if "last_news_fetch_time" not in st.session_state:
    st.session_state.last_news_fetch_time = 0
if "news_scraped_at" not in st.session_state:
    st.session_state.news_scraped_at = None

current_time = time.time()
if current_time - st.session_state.last_news_fetch_time >= 600: # 10 minutes
    news_payload = fetch_news(st.session_state.news_scraped_at)
    new_items = news_payload.get("items", [])
    
    # Prepend new items and deduplicate based on URL/Title
    if new_items:
        existing_urls = {item.get("url") for item in st.session_state.news_items}
        filtered_new = [item for item in new_items if item.get("url") not in existing_urls]
        st.session_state.news_items = filtered_new + st.session_state.news_items
        
    if news_payload.get("scraped_at"):
        st.session_state.news_scraped_at = news_payload.get("scraped_at")
    st.session_state.last_news_fetch_time = current_time

# Stats row
active = len(prices)
total  = sum(len(v) for v in cats.values())
now    = datetime.now().strftime("%H:%M:%S")

main_col, news_col = st.columns([3, 1], gap="large")

with main_col:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Feeds", active, delta=None)
    col2.metric("Total Symbols", total)
    col3.metric("Last Update", now)
    col4.metric("Refresh Rate", f"{refresh}s")
    
    # Per-category grids
    for cat_name, symbols in cats.items():
        icon = CATEGORY_ICONS.get(cat_name, "")
        st.markdown(f'<div class="cat-header">{icon} {cat_name}</div>', unsafe_allow_html=True)
    
        cols = st.columns(4)
        for i, sym in enumerate(symbols):
            record = prices.get(sym)
            with cols[i % 4]:
                if record:
                    st.markdown(render_card(record), unsafe_allow_html=True)
                else:
                    st.markdown(render_no_data(), unsafe_allow_html=True)

with news_col:
    with st.expander("📰 News", expanded=True):
        updated_str = "Never"
        if st.session_state.news_scraped_at:
            try:
                dt = datetime.fromisoformat(st.session_state.news_scraped_at.replace("Z", "+00:00"))
                updated_str = dt.astimezone().strftime("%H:%M")
            except:
                updated_str = "Unknown"
                
        st.markdown(f"<div style='font-size: 0.8em; color: #888; margin-bottom: 10px;'>Updated at {updated_str}</div>", unsafe_allow_html=True)
        
        for item in st.session_state.news_items[:20]: # show top 20
            # format related time
            pub_date_str = item.get("published_at")
            relative_time = pub_date_str
            if pub_date_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    diff = datetime.now(pub_dt.tzinfo) - pub_dt
                    if diff.total_seconds() < 3600:
                        relative_time = f"{int(diff.total_seconds() / 60)} min ago"
                    elif diff.total_seconds() < 86400:
                        relative_time = f"{int(diff.total_seconds() / 3600)} hr ago"
                    else:
                        relative_time = f"{int(diff.total_seconds() / 86400)} days ago"
                except:
                    pass
                    
            st.markdown(f"""
            <div style='margin-bottom: 12px; border-bottom: 1px solid #1a2a40; padding-bottom: 8px;'>
                <div style='font-size: 0.9em; font-weight: bold; margin-bottom: 4px;'>
                    <a href='{item.get("url")}' target='_blank' style='color: #c9d8e8; text-decoration: none;'>{item.get("title")}</a>
                </div>
                <div style='font-size: 0.7em; color: #666;'>
                    {item.get("source_name")} • {relative_time}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Status bar
st.markdown(
    f"""
    <div class="status-bar">
        <span>MARKET TRACKER v1.0</span>
        <span>BACKEND {BACKEND_URL}</span>
        <span>NEXT REFRESH IN {refresh}s · {now}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Auto-refresh
time.sleep(refresh)
st.rerun()