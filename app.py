"""
Live Market Data Dashboard – Streamlit Frontend
Optimized for performance and aesthetics.
"""

import os
import time
from datetime import datetime
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import urllib.parse

import technical

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_REFRESH_INTERVAL = 3000  # 3 seconds in milliseconds

CATEGORY_ICONS = {
    "Commodities": "🏅",
    "Bonds": "📊",
    "Indices": "📈",
    "Crypto": "🪙",
    "Risk Factors": "⚠️",
}

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live Market Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load CSS ──────────────────────────────────────────────────────────────────
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

if os.path.exists("style.css"):
    load_css("style.css")

# ── Helpers ───────────────────────────────────────────────────────────────────
if "pinned_symbols" not in st.session_state:
    st.session_state.pinned_symbols = set()

def toggle_pin(symbol: str):
    if symbol in st.session_state.pinned_symbols:
        st.session_state.pinned_symbols.remove(symbol)
    else:
        st.session_state.pinned_symbols.add(symbol)

@st.cache_data(ttl=2)
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

@st.cache_data(ttl=60)
def fetch_historical(symbol: str, time_range: str = "1Y") -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/api/historical?symbol={symbol}&range={time_range}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "data": []}

def fmt_price(price: float, symbol: str) -> str:
    if symbol and any(c in symbol for c in ["BTC", "ETH", "SOL"]):
        return f"{price:,.2f}"
    if price >= 10_000:
        return f"{price:,.1f}"
    if price >= 100:
        return f"{price:,.2f}"
    return f"{price:,.4f}"

def render_card(record: dict) -> str:
    symbol  = record["symbol"]
    price   = record.get("price")
    chg_pct = record.get("change_pct")
    vol     = record.get("volume")
    t       = record.get("time", "—")
    error   = record.get("error")
    
    is_pinned = symbol in st.session_state.pinned_symbols
    pin_icon = "★" if is_pinned else "☆"
    encoded_sym = urllib.parse.quote(symbol)
    
    header_html = f'<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;"><div class="card-symbol">{symbol}</div><a href="/?pin={encoded_sym}" target="_self" class="pin-btn" style="text-decoration: none; color: inherit;">{pin_icon}</a></div>'

    price_html = f'<div class="card-price">{fmt_price(price, symbol)}</div>' if price is not None else ""
    
    change_html = ""
    if chg_pct is not None:
        arrow = "▲" if chg_pct >= 0 else "▼"
        cls = "card-change-up" if chg_pct >= 0 else "card-change-down"
        change_html = f'<div class="{cls}"><span>{arrow}</span> {abs(chg_pct):.3f}%</div>'
    
    status_html = ""
    if error:
        status_html = f'<div class="card-error">ERR: {error}</div>'
    elif price is None:
        status_html = f'<div class="card-error">⏳ INITIALIZING...</div>'

    vol_str = f"{vol:,.0f}" if (vol is not None and vol > 0) else "—"

    return f'<div class="price-card">{header_html}<a href="/?symbol={encoded_sym}" target="_self" style="text-decoration: none; color: inherit; display: block;">{price_html}{change_html}{status_html}<div class="card-time">🕐 {t}</div><div class="card-vol">VOL {vol_str}</div></a></div>'

def render_no_data(symbol: str) -> str:
    encoded_sym = urllib.parse.quote(symbol)
    return f'<div class="price-card"><div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;"><div class="card-symbol">{symbol}</div><a href="/?pin={encoded_sym}" target="_self" class="pin-btn" style="text-decoration: none; color: inherit;">☆</a></div><div class="card-error">⏳ CONNECTING...</div></div>'

def render_historical_page(symbol: str):
    if st.button("← Back to Dashboard"):
        st.query_params.clear()
        st.rerun()
    
    st.markdown(f'<div class="dash-title">📉 {symbol} Historical</div>', unsafe_allow_html=True)
    
    col_range, col_ind = st.columns([1, 2])
    with col_range:
        time_range = st.select_slider(
            "Range",
            options=["1M", "3M", "6M", "1Y", "5Y", "MAX"],
            value="1Y"
        )
    
    with col_ind:
        selected_indicators = st.multiselect(
            "Technical Indicators",
            options=["SMA 20", "SMA 50", "EMA 20", "Bollinger Bands", "RSI 14"],
            default=[]
        )
    
    with st.spinner(f"Fetching data..."):
        result = fetch_historical(symbol, time_range)
    
    if "error" in result:
        st.error(f"Error: {result['error']}")
        return
    
    data = result.get("data", [])
    if not data:
        st.warning("No data available.")
        return
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    if selected_indicators:
        df = technical.calculate_indicators(df)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['price'], mode='lines', name='Price', line=dict(color='#00e5a0', width=2)))
    
    if selected_indicators:
        technical.add_indicators_to_fig(fig, df, selected_indicators)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#94a3b8', margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(size=10)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10))
    )
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if "RSI 14" in selected_indicators:
        rsi_fig = px.line(df, x='date', y='RSI_14', range_y=[0, 100], height=200)
        rsi_fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#c9d8e8', margin=dict(l=0, r=0, t=20, b=0))
        rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
        rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
        st.plotly_chart(rsi_fig, use_container_width=True)

# ── Main ──────────────────────────────────────────────────────────────────────
target_symbol = st.query_params.get("symbol")
if target_symbol:
    render_historical_page(target_symbol)
    st.stop()

# Auto-refresh
refresh_secs = st.sidebar.slider("Refresh (seconds)", 1, 30, 3)
st_autorefresh(interval=refresh_secs * 1000, key="data_refresh")

# Header
st.markdown(
f"""<div class="dash-header">
<div>
<div class="dash-title">MARKET TRACKER</div>
<div class="dash-subtitle"><span class="live-dot"></span>LIVE GLOBAL MARKET FEEDS</div>
</div>
<div style="text-align: right;">
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #94a3b8;">SYSTEM STATUS: <span style="color: #22c55e;">OPERATIONAL</span></div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #475569;">FINNHUB REAL-TIME OVER WS</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# Fetch data
payload = fetch_prices()
prices = payload.get("data", {})
cats = payload.get("categories", {})
err = payload.get("error")

if err:
    st.error(f"⚠️ Backend error: {err}")
    st.stop()

# Sidebar info
with st.sidebar:
    st.markdown("### ⚙️ Info")
    st.info(f"Connected to {BACKEND_URL}")
    if st.button("🔄 Reload Page"):
        st.rerun()

# News handling in session state
if "news_items" not in st.session_state:
    st.session_state.news_items = []
if "last_news_fetch" not in st.session_state:
    st.session_state.last_news_fetch = 0

if time.time() - st.session_state.last_news_fetch > 300: # 5 mins
    news_res = fetch_news()
    st.session_state.news_items = news_res.get("items", [])[:20]
    st.session_state.last_news_fetch = time.time()

# Layout
main_col, news_col = st.columns([3, 1], gap="medium")

with main_col:
    # Top metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Active Feeds", len(prices))
    m2.metric("Total Tracked", sum(len(v) for v in cats.values()))
    m3.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

    # Pinned Section
    if st.session_state.pinned_symbols:
        st.markdown('<div class="cat-header">📌 Pinned Assets</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sym in enumerate(sorted(st.session_state.pinned_symbols)):
            record = prices.get(sym)
            with cols[i % 4]:
                if record:
                    st.markdown(render_card(record), unsafe_allow_html=True)
                else:
                    st.markdown(render_no_data(sym), unsafe_allow_html=True)

    # Grids
    for cat_name, symbols in cats.items():
        icon = CATEGORY_ICONS.get(cat_name, "📌")
        st.markdown(f'<div class="cat-header">{icon} {cat_name}</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sym in enumerate(symbols):
            record = prices.get(sym)
            with cols[i % 4]:
                if record:
                    st.markdown(render_card(record), unsafe_allow_html=True)
                else:
                    st.markdown(render_no_data(sym), unsafe_allow_html=True)

with news_col:
    st.markdown('<div class="cat-header">📰 Market Intelligence</div>', unsafe_allow_html=True)
    for item in st.session_state.news_items:
        st.markdown(
f"""<div class="news-item">
<div style='font-size: 0.85rem; font-weight: 600; line-height: 1.4; margin-bottom: 6px;'>
<a href='{item.get("url")}' target='_blank' style='color: #f1f5f9; text-decoration: none;'>{item.get("title")}</a>
</div>
<div style='display: flex; justify-content: space-between; align-items: center;'>
<span style='font-size: 0.65rem; color: #64748b; background: rgba(100, 116, 139, 0.1); padding: 2px 6px; border-radius: 4px;'>{item.get("source_name")}</span>
<span style='font-size: 0.6rem; color: #475569;'>{datetime.fromtimestamp(item.get("datetime", time.time())).strftime("%H:%M")}</span>
</div>
</div>""", unsafe_allow_html=True)

# Status bar
st.markdown(
f"""<div class="status-bar">
<span>MARKET TRACKER v1.1</span>
<span>STATUS: ONLINE</span>
<span>REFRESH: {refresh_secs}s</span>
</div>""",
    unsafe_allow_html=True,
)
