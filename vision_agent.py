import os
import json
import logging
import tempfile
import asyncio
from typing import List, Dict, Tuple
from PIL import Image

import pandas as pd
import plotly.graph_objects as go
from google import genai
from google.genai import types

from historical import get_historical_prices
from technical import calculate_indicators, add_indicators_to_fig
from intelligence import get_intelligence_engine

logger = logging.getLogger(__name__)

VISION_PROMPT = """
You are a Senior Technical Analyst with an expert understanding of market structure, volume-price analysis, and moving average dynamics.
You are given a Candlestick chart with technical overlays (such as SMA, EMA, and Bollinger Bands) and an RSI indicator.
You are also provided with recent market news and context:
<WEB_SIGNALS>

Your task is to analyze the chart and return a machine-readable JSON structure based on the chart's current technical posture and the fundamental web context.

CRITICAL CONSTRAINTS:
1. ONLY return valid JSON. Do not include any conversational filler, markdown formatting (like ```json), or explanatory text outside the JSON.
2. The JSON must exactly match the following schema:
{
  "symbol": "<TICKER>",
  "direction": "<BULLISH|BEARISH|NEUTRAL>",
  "recommendation": "<BUY|HOLD|SELL>",
  "key_levels": {
    "support": <number or null>,
    "resistance": <number or null>
  },
  "narrative": "<1-2 sentences explaining the technical justification (e.g., 'Price is rejecting the upper Bollinger Band with bearish divergence on RSI.')>",
  "web_signals": "<1 sentence summarizing how the provided web signals align or conflict with the technicals>"
}

Analyze the chart and context now and generate the JSON.
"""

class VisionAgent:
    def __init__(self, gemini_api_key: str):
        self.api_key = gemini_api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = 'gemini-2.0-flash'
        else:
            self.client = None
            logger.warning("Gemini API key not found. Vision features will be limited.")

    async def generate_chart_image(self, symbol: str, df: pd.DataFrame, indicators: List[str]) -> str:
        """
        Generates a Plotly chart and saves it to a temporary PNG file.
        Returns the absolute path to the temporary file.
        """
        if df.empty:
            raise ValueError(f"Cannot generate chart for {symbol}: Empty DataFrame")

        # Basic Candlestick
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['price'],
            name="Price"
        )])

        # Add indicators
        add_indicators_to_fig(fig, df, indicators)

        # Style the chart for clear AI consumption (dark mode, clean grid)
        fig.update_layout(
            title=f"{symbol} Technical Chart",
            plot_bgcolor='rgb(17, 17, 17)',
            paper_bgcolor='rgb(17, 17, 17)',
            font_color='white',
            xaxis_rangeslider_visible=False,
            margin=dict(l=40, r=40, t=40, b=40),
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            width=1000,
            height=600
        )

        # Create temporary file
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        # Save to PNG using kaleido (requires running in executor if synchronous, but write_image is relatively fast)
        fig.write_image(path)
        
        return path

    async def analyze_chart(self, symbol: str, image_path: str, web_signals: str) -> Dict:
        """
        Sends the image to Gemini 2.0 Flash and requests structured JSON output.
        """
        if not self.client:
            return {"error": "API Key not configured."}

        try:
            # Load the image using PIL
            img = Image.open(image_path)
            
            # Formulate the prompt
            prompt = VISION_PROMPT.replace("<TICKER>", symbol).replace("<WEB_SIGNALS>", web_signals)

            # Generate content
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )

            # Parse JSON response
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from Gemini: {response.text}")
                return {"error": "Invalid JSON response from model", "raw": response.text}
                
        except Exception as e:
            logger.error(f"Error during Vision analysis for {symbol}: {e}")
            return {"error": str(e)}

    async def process_ticker(self, symbol: str, time_range: str, indicators: List[str]) -> Tuple[str, Dict, str]:
        """
        End-to-end processing for a single ticker: Data Fetch -> Chart -> Vision AI
        Returns (symbol, analysis_result, image_path)
        """
        from datetime import datetime, timedelta
        
        # 1. Fetch data
        now = datetime.now()
        start = now - timedelta(days=90) # Default to 3M for visual analysis
        if time_range == "1M": start = now - timedelta(days=30)
        elif time_range == "6M": start = now - timedelta(days=180)
        elif time_range == "1Y": start = now - timedelta(days=365)
            
        data = await asyncio.to_thread(get_historical_prices, symbol, start, now)
        if not data:
            return symbol, {"error": "No data found"}, ""
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate all indicators base (required by add_indicators_to_fig)
        df = calculate_indicators(df)
        
        # Fetch Web Signals concurrently with Image generation
        intel_engine = get_intelligence_engine()
        search_query = f"{symbol} stock market news technical analysis today {now.strftime('%Y-%m-%d')}"
        
        signals = await intel_engine.get_search_signals(search_query, max_results=3)
        signal_text = "\n".join([f"- {s['title']}: {s['body']}" for s in signals]) if signals else "No relevant recent signals found."
        
        # 2. Generate Image
        image_path = ""
        try:
            image_path = await self.generate_chart_image(symbol, df, indicators)
            
            # 3. Analyze Image + Web Signals
            analysis = await self.analyze_chart(symbol, image_path, signal_text)
            
            return symbol, analysis, image_path
            
        except Exception as e:
            logger.error(f"Failed to process ticker {symbol}: {e}")
            return symbol, {"error": str(e)}, image_path

    async def batch_analyze(self, symbols: List[str], time_range: str, indicators: List[str]) -> List[Tuple[str, Dict, str]]:
        """
        Process multiple symbols concurrently.
        """
        tasks = [self.process_ticker(sym, time_range, indicators) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Batch task failed with exception: {res}")
            else:
                final_results.append(res)
                
        return final_results

# Singleton
vision_agent_instance = None

def get_vision_agent() -> VisionAgent:
    global vision_agent_instance
    if vision_agent_instance is None:
        api_key = os.getenv("GEMINI_API_KEY")
        vision_agent_instance = VisionAgent(api_key)
    return vision_agent_instance
