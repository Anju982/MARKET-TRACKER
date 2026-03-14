import aiohttp
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

async def fetch_symbol_news_async(symbol: str, api_token: str, days_back: int = 7) -> List[Dict]:
    """
    Fetches company-specific news from Finnhub API asynchronously.
    """
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    base_url = "https://finnhub.io/api/v1/company-news"
    params = {
        'symbol': symbol,
        'from': start_date,
        'to': end_date,
        'token': api_token
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status == 429:
                    logger.warning(f"Rate limit exceeded (429) for {symbol}")
                    return []
                
                response.raise_for_status()
                articles = await response.json()

                if not articles:
                    return []

                all_data = []
                for article in articles[:20]: # Limit to top 20
                    dt = datetime.fromtimestamp(article.get('datetime', 0), tz=timezone.utc)
                    all_data.append({
                        'title': article.get('headline'),
                        'source_name': article.get('source'),
                        'published_at': dt.isoformat(),
                        'url': article.get('url'),
                        'uuid': str(article.get('id', hash(article.get('url')))),
                        'image': article.get('image'),
                        'summary': article.get('summary')
                    })
                return all_data
        except Exception as e:
            logger.error(f"Error fetching symbol news for {symbol}: {e}")
    return []

async def fetch_commodity_news_async(api_token: str, max_pages: int = 1, since_timestamp: Optional[str] = None) -> List[Dict]:
    """
    Fetches commodity news from Finnhub API asynchronously.
    """
    base_url = "https://finnhub.io/api/v1/news"
    max_retries = 3
    base_delay = 2

    params = {
        'category': 'general',
        'token': api_token
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                async with session.get(base_url, params=params, timeout=10) as response:
                    if response.status == 429:
                        logger.warning(f"Rate limit exceeded (429). Attempt {attempt + 1}/{max_retries}")
                        await asyncio.sleep(base_delay * (attempt + 2))
                        continue
                    
                    response.raise_for_status()
                    articles = await response.json()

                    if not articles:
                        return []

                    all_data = []
                    for article in articles:
                        dt = datetime.fromtimestamp(article.get('datetime', 0), tz=timezone.utc)
                        all_data.append({
                            'title': article.get('headline'),
                            'source_name': article.get('source'),
                            'published_at': dt.isoformat(),
                            'url': article.get('url'),
                            'uuid': str(article.get('id', hash(article.get('url')))),
                            'image': article.get('image'),
                            'summary': article.get('summary')
                        })
                    
                    # Filter if since_timestamp is provided
                    if since_timestamp:
                        try:
                            cutoff = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                            all_data = [a for a in all_data if datetime.fromisoformat(a['published_at'].replace("Z", "+00:00")) > cutoff]
                        except ValueError:
                            pass
                    
                    return all_data

            except Exception as e:
                logger.error(f"Error fetching news (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (attempt + 1))
                else:
                    break
    return []

# Legacy wrapper for compatibility if needed (synchronous)
def fetch_commodity_news(api_token: str, max_pages: int = 1, since_timestamp: Optional[str] = None) -> list:
    import requests
    # ... existing sync code if really needed, but better to use async ...
    # For now, let's keep the file consistent with its name.
    # I'll just leave the async version as the primary one.
    return asyncio.run(fetch_commodity_news_async(api_token, max_pages, since_timestamp))
