# Market Tracker

A real-time market dashboard built with FastAPI and Streamlit that tracks live prices for Commodities, Bonds, Indices, and Cryptocurrencies using the Finnhub WebSocket API.

## Project Structure

- **`main.py`**: The FastAPI backend entry point. It manages API endpoints and initializes the WebSocket connection.
- **`app.py`**: The Streamlit frontend application. It connects to the FastAPI backend to visualize the live market data.
- **`PricesStore.py`**: An in-memory thread-safe store managing the state of all tracked symbols.
- **`WebSocket.py`**: Manages the persistent WebSocket connection to Finnhub to stream live market trades.
- **`news.py` & `NewsStore.py`**: Fetches and manages real-time news articles from Finnhub.
- **`historical.py`**: Fetches historical price data using Yahoo Finance.
- **`technical.py`**: Computes and visualizes technical indicators (SMA, BB, etc.) on interactive charts.
- **`config.py`**: Contains constants like `SYMBOL_MAP` and `CATEGORIES` for what the application tracks.
- **`requirment.txt`**: List of Python dependencies required to run the application.

## Prerequisites

1. Python 3.8+
2. A free Finnhub API Key (Get one from [Finnhub](https://finnhub.io/))

## Setup & Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Anju982/MARKET-TRACKER.git
   cd MARKET-TRACKER
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirment.txt
   ```

   _(Note: Make sure `websocket-client` and `python-dotenv` are installed)._

4. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add your Finnhub API key:
   ```env
   FinHubAPI=your_finnhub_api_key_here
   ```

## Running the Application

This project requires running both the backend API server and the frontend dashboard.

### 1. Start the FastAPI Backend

In your terminal, run the following command to start the backend server:

```bash
python -m uvicorn main:app
```

The backend API will be available at `http://localhost:8000`. You can verify it's working by navigating to `http://localhost:8000/health`.

### 2. Start the Streamlit Frontend

Open a **new terminal tab/window**, ensure your virtual environment is activated, and run:

```bash
streamlit run app.py
```

The live dashboard will automatically open in your default web browser (typically at `http://localhost:8501`).

## Troubleshooting

- **No data appearing**: Check your backend terminal for any WebSocket authentication errors. Ensure your `FinHubAPI` key in the `.env` file is valid and hasn't exceeded its rate limits.
- **ModuleNotFoundError**: Ensure all packages in `requirment.txt` are installed in your active Python environment.
