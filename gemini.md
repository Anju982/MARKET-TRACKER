# Project Context for Gemini / LLM Assistants

This file provides system instructions and architectural context for AI coding assistants working on the **Commodity Price Tracker**. When interacting with the Gemini CLI or other AI agents, provide this file as context so they understand the project's structure, goals, and conventions.

## Project Overview

The Commodity Price Tracker is a real-time dashboard that fetches live market data via Finnhub/Yahoo Finance and displays it using a Streamlit frontend. It features a standardized Data Hydration Pipeline that automatically synchronizes historical data, technical analysis, market intelligence, and Multimodal Vision reasoning upon asset selection.

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** Python + Streamlit
- **Data Source:** Finnhub WebSocket API (`wss://ws.finnhub.io`)
- **Concurrency:** Threading (for the WebSocket connection) and Uvicorn for standard async HTTP handling.

## Code Architecture

1. **`app.py`:** The Streamlit dashboard. It polls `http://localhost:8000/prices` every N seconds and builds the UI. Contains custom CSS for a dark-themed, glassmorphic layout.
2. **`main.py`:** The FastAPI application. Manages background polling, WebSockets, and the `/api/hydrate` pipe which orchestrates concurrent analysis layers.
3. **`PricesStore.py`:** An in-memory, thread-safe data structure holding the latest price updates.
4. **`WebSocket.py`:** A `WebSocketManager` class running in a daemon thread. Parses Finnhub trade messages.
5. **`config.py`:** Central configuration for `SYMBOL_MAP` and `CATEGORIES`.
6. **`intelligence.py`:** `MarketIntelligence` engine that synthesizes market signals via DuckDuckGo and the Gemini API.
7. **`vision_agent.py`:** `VisionAgent` that generates technical charts and performs multimodal reasoning using `gemini-2.5-flash`.
8. **`historical.py`:** Data fetcher for Yahoo Finance historical candles.
9. **`technical.py`:** Technical indicator calculations and Plotly visualization overlays.

## Future Development Guidelines

When adding features or fixing bugs in this project, adhere to the following rules:

1. **State Management:** The `PricesStore` must remain thread-safe. Always use `with self.lock:` when reading or mutating `self.data`.
2. **Configuration vs Code:** Do not hardcode new symbols inside the logic files. Any new assets to be tracked must be added to `SYMBOL_MAP` and `CATEGORIES` in `config.py`.
3. **Hydration Sync:** Page-load functions in `app.py` should ideally use the `/api/hydrate` suite for atomicity and performance.
5. **Model Versioning:** Use `gemini-2.5-flash` for all vision and intelligence tasks unless low-latency requirements dictate otherwise.
6. **Concurrency:** Always use `asyncio.gather` for independent external API calls (e.g., in the hydration pipeline) to avoid blocking the main thread.
7. **Dependencies:** Update `requirements.txt` when adding new AI or data libraries.
