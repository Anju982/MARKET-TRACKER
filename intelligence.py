import os
import logging
import asyncio
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from google import genai
from google.genai import types
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Analyst Persona Prompt ──────────────────────────────────────────────────
ANALYST_PROMPT = """
You are a Senior Market Intelligence Analyst with a FinTech and Quantitative focus.
Your objective is to synthesize raw web search data and real-time market metrics into high-density technical insights.

OPERATIONAL CONSTRAINTS:
- Tone: Concise, direct, and professional. Omit greetings and conversational filler.
- Formatting: Always start with a 1-2 sentence TL;DR. Use bullet points for key data and LaTeX for complex formulas.
- Context Awareness: Reference SYMBOL_MAP and CATEGORIES where appropriate.
- Data Handling: Prioritize technical indicators (RSI, SMA, EMA), volume trends, and macroeconomic/geopolitical risk factors.

Output analysis focusing on volatility, volume trends, and geopolitical risk factors.
"""

class MarketIntelligence:
    def __init__(self, gemini_api_key: str):
        self.api_key = gemini_api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = 'gemini-2.5-flash' # Updated to latest stable model
        else:
            self.client = None
            logger.warning("Gemini API key not found. Intelligence features will be limited.")

    async def get_search_signals(self, query: str, max_results: int = 5) -> List[Dict]:
        """Fetch raw search signals from DuckDuckGo."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def synthesize_market_view(self, symbol: str, category: str, current_metrics: Dict, historical_data: Optional[List] = None) -> str:
        """Synthesize market intelligence using Gemini."""
        if not self.client:
            return "Intelligence synthesis unavailable: GEMINI_API_KEY is not configured in the environment."

        # 1. Get raw signals
        search_query = f"{symbol} {category} market news technical analysis geopolitical risk {datetime.now().strftime('%Y-%m-%d')}"
        signals = await self.get_search_signals(search_query)
        
        signal_text = "\n".join([f"- {s['title']}: {s['body']}" for s in signals])

        # 2. Prepare context
        context = f"""
        SYMBOL: {symbol}
        CATEGORY: {category}
        CURRENT METRICS: {current_metrics}
        HISTORICAL SNAPSHOT: {historical_data[:10] if historical_data else 'N/A'}
        
        RAW SEARCH SIGNALS:
        {signal_text}
        """

        # 3. Generate Analysis
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=f"{ANALYST_PROMPT}\n\nUSER DATA:\n{context}"
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return f"Error synthesizing intelligence: {str(e)}"

    async def chat_with_analyst(self, symbol: str, query: str, context_data: Dict) -> str:
        """Interactive chat with the Analyst persona."""
        if not self.client:
            return "Chat unavailable: API key missing."

        # Fetch fresh signals for the query
        search_query = f"{symbol} {query} technical analysis market impact"
        signals = await self.get_search_signals(search_query, max_results=3)
        signal_text = "\n".join([f"- {s['title']}: {s['body']}" for s in signals])

        prompt = f"""
        {ANALYST_PROMPT}
        
        CURRENT CONTEXT:
        Symbol: {symbol}
        Market Data: {context_data.get('metrics', {})}
        Web Search Signals:
        {signal_text}
        
        USER QUERY: {query}
        
        Provide a shaped answer following the operational constraints.
        """

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Chat generation error: {e}")
            return "Analysis interrupted. Please re-query."

# Singleton instance
intelligence_engine: Optional[MarketIntelligence] = None

def get_intelligence_engine() -> MarketIntelligence:
    global intelligence_engine
    if intelligence_engine is None:
        api_key = os.getenv("GEMINI_API_KEY")
        intelligence_engine = MarketIntelligence(api_key)
    return intelligence_engine
