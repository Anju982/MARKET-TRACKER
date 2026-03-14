from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import asyncio
import logging

from news import fetch_commodity_news_async

logger = logging.getLogger(__name__)

MAX_ARTICLES = 50

class NewsStore:
    """
    In-memory store for market news articles.
    Optimized for memory usage and asyncio concurrency.
    """
    def __init__(self, api_token: str):
        self.fetch_lock = asyncio.Lock()
        self.last_scraped_at: Optional[str] = None
        self.articles: Dict[str, dict] = {}
        self.api_token = api_token

    def get_news_since(self, since_timestamp: Optional[str] = None) -> dict:
        """
        Returns cached news since the given timestamp.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        
        try:
            if since_timestamp:
                target_since = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                if target_since.tzinfo is None:
                    target_since = target_since.replace(tzinfo=timezone.utc)
                if target_since < cutoff:
                    target_since = cutoff
            else:
                target_since = cutoff
        except Exception:
            target_since = cutoff

        result = []
        for art in self.articles.values():
            pub_str = art.get('published_at')
            if not pub_str: continue
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt > target_since:
                    result.append(art)
            except ValueError:
                continue
        
        result.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        return {
            "items": result,
            "scraped_at": self.last_scraped_at or now.isoformat()
        }

    async def update_news(self):
        """Async method to fetch and update news articles."""
        async with self.fetch_lock:
            try:
                # Use current last_scraped_at or 48h ago
                since = self.last_scraped_at
                if not since:
                    since = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
                
                new_articles = await fetch_commodity_news_async(
                    api_token=self.api_token,
                    since_timestamp=since
                )
                
                if not new_articles:
                    return

                for article in new_articles:
                    article_id = article.get('uuid') or article.get('url')
                    if article_id and article_id not in self.articles:
                        self.articles[article_id] = article
                
                # Update last_scraped_at
                all_published = [
                    datetime.fromisoformat(a['published_at'].replace("Z", "+00:00")) 
                    for a in self.articles.values() if a.get('published_at')
                ]
                if all_published:
                    self.last_scraped_at = max(all_published).isoformat()
                
                # --- Optimization: Limit memory usage ---
                if len(self.articles) > MAX_ARTICLES:
                    # Sort articles by date and keep latest
                    sorted_articles = sorted(
                        self.articles.items(),
                        key=lambda x: x[1].get('published_at', ''),
                        reverse=True
                    )
                    self.articles = dict(sorted_articles[:MAX_ARTICLES])

                logger.info(f"NewsStore updated with {len(new_articles)} new articles. Total: {len(self.articles)}")
            except Exception as e:
                logger.error(f"Error updating news in NewsStore: {e}")
