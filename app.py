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

def fetch_historical(symbol: str, time_range: str = "1Y") -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/api/historical?symbol={symbol}&range={time_range}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "data": []}

@st.cache_data(ttl=3600)
def fetch_intelligence(symbol: str) -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/api/intelligence?symbol={symbol}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "analysis": "Could not synthesize intelligence at this time."}

def fetch_hydration_suite(symbol: str, time_range: str = "1Y") -> dict:
    try:
        r = requests.get(f"{BACKEND_URL}/api/hydrate?symbol={symbol}&range={time_range}", timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": f"Hydration service failure: {str(e)}"}

def post_chat(symbol: str, query: str) -> str:
    try:
        r = requests.post(f"{BACKEND_URL}/api/chat", json={"symbol": symbol, "query": query}, timeout=30)
        r.raise_for_status()
        return r.json().get("response", "No response received.")
    except Exception as e:
        return f"Analytical system failure: {str(e)}"

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
    
    st.markdown(f'<div class="dash-title">📉 {symbol} Overview</div>', unsafe_allow_html=True)
    
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
    
    with st.spinner(f"Hydrating {symbol} intelligence suite..."):
        hydration = fetch_hydration_suite(symbol, time_range)
    
    if "error" in hydration:
        st.error(f"Pipeline Error: {hydration['error']}")
        # Fallback to basic historical if hydration fails? For now, just error.
    else:
        # ── Historical & Technical ──
        data = hydration.get("historical", [])
        if not data:
            st.warning("No historical data available.")
        else:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Indicators are pre-calculated on backend, but we reuse calculate_indicators for df compatibility with plotter
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

        # ── Intelligence & Vision (Automated Loading) ──
        st.divider()
        col_intel, col_vis = st.columns([1, 1])
        
        with col_intel:
            st.markdown("#### 💬 Market Intelligence Synthesis")
            intel_text = hydration.get("intelligence", {}).get("synthesis", "No synthesis available.")
            st.markdown(intel_text)
            
            # Quick chat option integrated
            with st.expander("Inquire further"):
                prompt = st.text_input("Ask about this signal", key="quick_chat_input")
                if prompt:
                    with st.spinner("Analyzing..."):
                        resp = post_chat(symbol, prompt)
                        st.write(resp)

        with col_vis:
            st.markdown("#### 👁️ Multimodal AI Reasoning")
            vision = hydration.get("vision", {})
            analysis = vision.get("analysis", {})
            
            if analysis.get("error"):
                st.error(analysis["error"])
            else:
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.metric("Signal", analysis.get("direction", "N/A"))
                with c2:
                    st.metric("Rec", analysis.get("recommendation", "N/A"))
                
                st.info(analysis.get("narrative", "—"))
                
                if vision.get("image_base64"):
                    import base64
                    img_bytes = base64.b64decode(vision["image_base64"])
                    st.image(img_bytes, use_column_width=True, caption="Pipeline Generated Analysis Chart")

# ── Sub-Pages ────────────────────────────────────────────────────────────────

def render_multimodal_analyst():
    st.markdown('<div class="dash-header"><div class="dash-title">🧠 MULTIMODAL AI ANALYST</div><div class="dash-subtitle">Visual Reasoning with Gemini 2.0 Flash + Web Search</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tickers = st.text_input("Tickers to analyze (comma separated)", "AAPL, MSFT, BTC-USD")
    with col2:
        time_range = st.selectbox("Time Range", ["1M", "3M", "6M", "1Y"], index=1)
        
    indicators = st.multiselect(
        "Technical Indicators",
        options=["SMA 20", "SMA 50", "EMA 20", "Bollinger Bands", "RSI 14"],
        default=["SMA 20", "Bollinger Bands", "RSI 14"]
    )
    
    if st.button("🚀 Run Analysis", type="primary"):
        symbols_list = [s.strip() for s in tickers.split(",") if s.strip()]
        if not symbols_list:
            st.warning("Please enter at least one ticker.")
            return
            
        with st.spinner(f"Analyzing {len(symbols_list)} assets concurrently..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/vision_analysis",
                    json={"symbols": symbols_list, "time_range": time_range, "indicators": indicators},
                    timeout=90
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    st.error(data["error"])
                    return
                    
                results = data.get("results", [])
                
                st.markdown("### 📊 Batch Analysis Summary")
                summary_data = []
                for res in results:
                    analysis = res.get("analysis", {})
                    if "error" in analysis:
                        summary_data.append({"Symbol": res["symbol"], "Signal": "ERROR", "Recommendation": "ERROR", "Support": "-", "Resistance": "-"})
                    else:
                        summary_data.append({
                            "Symbol": res["symbol"],
                            "Signal": analysis.get("direction", "N/A"),
                            "Recommendation": analysis.get("recommendation", "N/A"),
                            "Support": analysis.get("key_levels", {}).get("support", "N/A"),
                            "Resistance": analysis.get("key_levels", {}).get("resistance", "N/A")
                        })
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                
                st.markdown("---")
                
                if results:
                    tabs = st.tabs([r["symbol"] for r in results])
                    for i, tab in enumerate(tabs):
                        with tab:
                            res = results[i]
                            st.markdown(f"### {res['symbol']} Deep Dive")
                            
                            analysis = res.get("analysis", {})
                            if "error" in analysis:
                                st.error(f"Analysis failed: {analysis['error']}")
                            else:
                                c1, c2 = st.columns([2, 1])
                                with c1:
                                    if res.get("image_base64"):
                                        import base64
                                        img_bytes = base64.b64decode(res["image_base64"])
                                        st.image(img_bytes, use_column_width=True, caption=f"Generated Technical Chart for {res['symbol']}")
                                    else:
                                        st.warning("No chart image returned.")
                                
                                with c2:
                                    st.markdown("#### The Narrative")
                                    st.info(analysis.get("narrative", "No narrative provided."))
                                    
                                    st.markdown("#### Foundational Signals")
                                    if analysis.get("web_signals"):
                                        st.markdown(analysis["web_signals"])
                                    else:
                                        st.caption("No real-time web signals provided.")
                                        
                                    st.markdown("#### Key Levels")
                                    col_sup, col_res = st.columns(2)
                                    with col_sup:
                                        st.metric("Support", analysis.get("key_levels", {}).get("support", "N/A"))
                                    with col_res:
                                        st.metric("Resistance", analysis.get("key_levels", {}).get("resistance", "N/A"))
                                        
            except Exception as e:
                st.error(f"Failed to communicate with backend: {e}")

def render_market_intelligence():
    st.markdown('<div class="dash-header"><div class="dash-title">💬 MARKET INTELLIGENCE</div><div class="dash-subtitle">Real-time Synthesis & Analysis Chat</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Enter a ticker to analyze (e.g., OANDA:XAU_USD, AAPL, BTC-USD)", "AAPL")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Generate Report", type="primary", use_container_width=True)
        
    if run_btn:
        st.session_state.intel_symbol = symbol.strip()
        
    target_symbol = st.session_state.get("intel_symbol", "")
    
    if target_symbol:
        st.markdown("---")
        st.markdown(f"### 🤖 AI Market Analyst: {target_symbol}")
        
        with st.expander("📊 View Market Synthesis Report", expanded=True):
            with st.spinner("Synthesizing market signals..."):
                intel = fetch_intelligence(target_symbol)
                
                if "error" in intel and intel["analysis"] == "Could not synthesize intelligence at this time.":
                    st.error(f"Intelligence Error: {intel['error']}")
                else:
                    st.markdown(intel.get("analysis", "No analysis available."))
                    if intel.get("cached"):
                        st.caption("✨ Synthesized from cached intelligence reports")
                    else:
                        st.caption("⚡ Live synthesis from real-time signals")
                        
        st.divider()
        st.markdown("#### 💬 Inquiry Terminal")
        
        chat_key = f"chat_history_{target_symbol}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []
            
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt := st.chat_input(f"Inquire about {target_symbol} (e.g., 'What is the RSI trend?')"):
            st.session_state[chat_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Analyzing signals..."):
                    response = post_chat(target_symbol, prompt)
                    st.markdown(response)
                    st.session_state[chat_key].append({"role": "assistant", "content": response})

# ── Main ──────────────────────────────────────────────────────────────────────
target_symbol = st.query_params.get("symbol")
if target_symbol:
    render_historical_page(target_symbol)
    st.stop()

# Main Top Navigation
st.markdown("<br>", unsafe_allow_html=True)
nav_selection = st.radio(
    "Select View", 
    ["📡 Live Tracking", "🧠 Multimodal Analyst", "💬 Market Intelligence"],
    horizontal=True, 
    label_visibility="collapsed"
)
st.divider()

if nav_selection == "🧠 Multimodal Analyst":
    render_multimodal_analyst()
    st.stop()
elif nav_selection == "💬 Market Intelligence":
    render_market_intelligence()
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
