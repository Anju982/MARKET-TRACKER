import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import time

from news import fetch_commodity_news

class NewsStore:
    def __init__(self, api_token: str):
        self.lock = threading.Lock()
        self.fetch_lock = threading.Lock()
        self.last_scraped_at: Optional[str] = None
        self.articles: Dict[str, dict] = {}  # Deduplicated by url or uuid
        self.api_token = api_token

    def get_news_since(self, since_timestamp: Optional[str] = None) -> dict:
        """
        Fetches news since the given timestamp.
        Debounces concurrent fetches using fetch_lock.
        """
        # If no timestamp provided or older than 48h, we use now - 48h.
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        
        target_since = None
        if since_timestamp:
            try:
                 # Try parsing ISO 8601
                 dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                 if dt.tzinfo is None:
                     dt = dt.replace(tzinfo=timezone.utc)
                 if dt < cutoff:
                     target_since = cutoff
                 else:
                     target_since = dt
            except ValueError:
                 target_since = cutoff
        else:
            target_since = cutoff

        # Convert target_since to string for the fetch function
        target_since_str = target_since.isoformat()

        # Check if we should fetch. If another thread is fetching, wait for it.
        acquired = self.fetch_lock.acquire(blocking=False)
        if acquired:
            try:
                # Perform the fetch
                new_articles = fetch_commodity_news(
                    api_token=self.api_token, 
                    since_timestamp=target_since_str,
                    max_pages=3 # limited to prevent hitting API limits hard
                )
                
                with self.lock:
                    for article in new_articles:
                        # Assuming each article has a 'url' we can use as stable ID if 'uuid' missing
                        article_id = article.get('uuid') or article.get('url')
                        if article_id and article_id not in self.articles:
                            self.articles[article_id] = article
                            
                    # Update last scraped to the max published_at or now
                    if new_articles:
                        try:
                            # find max published_at
                            max_pub = max(
                                [datetime.fromisoformat(a['published_at'].replace("Z", "+00:00")) 
                                 for a in new_articles if a.get('published_at')]
                            )
                            if not self.last_scraped_at:
                                self.last_scraped_at = max_pub.isoformat()
                            else:
                                current_last = datetime.fromisoformat(self.last_scraped_at.replace("Z", "+00:00"))
                                if max_pub > current_last:
                                    self.last_scraped_at = max_pub.isoformat()
                        except Exception:
                            pass
            except Exception as e:
                print(f"Error fetching news: {e}")
            finally:
                self.fetch_lock.release()
        else:
            # Another thread is fetching; wait for it to finish then return what we have
            with self.fetch_lock:
                pass


        # Return filtered articles
        with self.lock:
            # return articles strictly newer than since_timestamp (if provided)
            # or all recent articles if since_timestamp is None
            
            result = []
            for art in self.articles.values():
                pub_str = art.get('published_at')
                if not pub_str:
                    continue
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    if pub_dt > target_since:
                        result.append(art)
                except ValueError:
                    continue
            
            # Sort descending by date
            result.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            return {
                "items": result,
                "scraped_at": self.last_scraped_at or now.isoformat()
            }
