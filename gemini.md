# Project Context for Gemini / LLM Assistants

This file provides system instructions and architectural context for AI coding assistants working on the **Commodity Price Tracker**. When interacting with the Gemini CLI or other AI agents, provide this file as context so they understand the project's structure, goals, and conventions.

## Project Overview

The Commodity Price Tracker is a real-time dashboard that fetches live market data via the Finnhub WebSocket API and displays it using a Streamlit frontend. It uses a FastAPI backend to manage the connection and serve the latest prices to the frontend.

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** Python + Streamlit
- **Data Source:** Finnhub WebSocket API (`wss://ws.finnhub.io`)
- **Concurrency:** Threading (for the WebSocket connection) and Uvicorn for standard async HTTP handling.

## Code Architecture

1. **`app.py`:** The Streamlit dashboard. It polls `http://localhost:8000/prices` every N seconds and builds the UI. Contains custom CSS for a dark-themed, glassmorphic layout.
2. **`main.py`:** The FastAPI application. Initializes the application state, manages CORS, and exposes `/prices` and `/health` REST endpoints.
3. **`PricesStore.py`:** An in-memory, thread-safe data structure (`self.data`) wrapped with a `threading.Lock()` to hold the latest price updates.
4. **`WebSocket.py`:** A `WebSocketManager` class running in a daemon thread. It parses incoming Finnhub JSON `trade` messages and pushes the latest `p` (price), `v` (volume), and `t` (timestamp) to the `PricesStore`.
5. **`config.py`:** Centralized configuration containing `SYMBOL_MAP` (mapping API symbols to readable names) and `CATEGORIES` (grouping assets).
6. **`news.py`:** Fetches market news from Finnhub API.
7. **`NewsStore.py`:** Thread-safe in-memory store for news articles with debounced fetching.
8. **`historical.py`:** Fetches historical price data from Yahoo Finance and maps API symbols to tickers.
9. **`technical.py`:** Calculates technical indicators (SMA, EMA, RSI, Bollinger Bands) and adds them to Plotly charts.

## Future Development Guidelines

When adding features or fixing bugs in this project, adhere to the following rules:

1. **State Management:** The `PricesStore` must remain thread-safe. Always use `with self.lock:` when reading or mutating `self.data`.
2. **Configuration vs Code:** Do not hardcode new symbols inside the logic files. Any new assets to be tracked must be added to `SYMBOL_MAP` and `CATEGORIES` in `config.py`.
3. **Frontend Styling:** Do not remove the custom CSS injected in `app.py` without replacing it with an equivalent modern aesthetic. Avoid basic Streamlit layouts—aim for a polished, professional look.
4. **Error Handling:** When updating the `WebSocket.py` message parser, ensure exceptions are caught inside `on_message` so that a malformed payload doesn't crash the background thread.
5. **Dependencies:** Use the activated `venvcomodity` virtual environment before running or testing. New dependencies must be appended to `requirment.txt`.
