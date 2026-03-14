# Market Tracker (GCP Optimized)

A real-time market dashboard built with FastAPI and Streamlit that tracks live prices for Commodities, Bonds, Indices, and Cryptocurrencies.

## ✨ Latest Optimizations for GCP Free Tier
- **Low Memory Footprint:** Optimized to run comfortably on a **Google Compute Engine `e2-micro`** instance (1GB RAM).
- **In-Memory Cache Capping:** Added strict limits to `historical_cache` and `NewsStore` to prevent memory exhaustion (OOM).
- **Async Concurrency:** Removed redundant `threading.Locks` and moved all store updates to the main `asyncio` event loop for better performance.
- **Hydration Pipeline:** Standardized endpoint for synchronized data loading, technical analysis, and AI intelligence synthesis.
- **Multimodal AI Reasoning:** Integrated Gemini 2.5 Flash for visual chart analysis and narrative reasoning.
- **Single-Container Deployment:** Combined FastAPI and Streamlit into a single Docker image to minimize resource overhead.

## 🚀 Quick Start (Docker)

1. **Clone and Setup Environment:**
   ```bash
   git clone https://github.com/Anju982/MARKET-TRACKER.git
   cd MARKET-TRACKER
   cp .env.example .env
   # Edit .env and add your FinHubAPI key
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```
   - Dashboard: `http://localhost:8501`
   - API Docs: `http://localhost:8000/docs`

## ☁️ Deployment on GCP Free Tier (Compute Engine)

The best way to run this for free 24/7 is on a **Google Compute Engine `e2-micro`** instance.

1. **Create an Instance:**
   - **Region:** `us-central1` (Iowa), `us-west1` (Oregon), or `us-east1` (South Carolina).
   - **Machine Type:** `e2-micro` (2 vCPU, 1GB RAM).
   - **Firewall:** Allow HTTP traffic.

2. **Setup on VM:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose
   ```

3. **Deploy:**
   - Clone the repo on the VM.
   - Run `docker-compose up -d`.

## 🛠 Project Structure

- **`main.py`**: Optimized FastAPI backend managing API endpoints, background tasks, and the `/api/hydrate` orchestration pipeline.
- **`app.py`**: Streamlit frontend with a unified historical overview and real-time market dashboard.
- **`PricesStore.py`**: In-memory store for live market prices.
- **`WebSocket.py`**: Persistent WebSocket connection to Finnhub.
- **`news.py` & `NewsStore.py`**: Fetches and manages real-time news articles with a 50-article limit.
- **`historical.py`**: Fetches historical data using Yahoo Finance.
- **`technical.py`**: Computes and visualizes technical indicators.
- **`intelligence.py`**: Synthesizes market signals, news, and macro factors using LLMs.
- **`vision_agent.py`**: Automated chart generation and multimodal vision reasoning via Gemini.
- **`config.py`**: Constants like `SYMBOL_MAP` and `CATEGORIES`.

## 🛠 Tech Stack
- **Backend:** FastAPI, `websockets`, `yfinance`.
- **Frontend:** Streamlit, `plotly`, `streamlit-autorefresh`.
- **Infrastructure:** Docker, GCP (e2-micro).
