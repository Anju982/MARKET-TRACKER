import os
import time
import requests
from datetime import datetime, timezone
from typing import Optional

def fetch_commodity_news(api_token: str, max_pages: int = 1, since_timestamp: Optional[str] = None) -> list:
    """
    Fetches commodity news from Finnhub API.
    Returns a list of dicts for backend integration.
    """
    # Finnhub doesn't use pagination for market news, it returns the latest ~100 items.
    base_url = "https://finnhub.io/api/v1/news"
    
    # Retry configuration
    max_retries = 3
    base_delay = 2

    params = {
        'category': 'general', # We use general market news as Finnhub doesn't strictly isolate commodities
        'token': api_token
    }

    all_data = []

    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json()

            if not articles:
                print("EOF: No additional articles found.")
                break

            for article in articles:
                # Convert UNIX timestamp to ISO 8601 for our backend consistency
                dt = datetime.fromtimestamp(article.get('datetime', 0), tz=timezone.utc)
                
                normalized_article = {
                    'title': article.get('headline'),
                    'source_name': article.get('source'),
                    'published_at': dt.isoformat(),
                    'url': article.get('url'),
                    'uuid': str(article.get('id', hash(article.get('url')))),
                    'image': article.get('image'),
                    'summary': article.get('summary')
                }
                all_data.append(normalized_article)
            
            print(f"Ingested Finnhub News | Records: {len(all_data)}")
            break # break retry loop on success

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error on attempt {attempt + 1}: {e}")
            if response.status_code == 429:
                print("HTTP 429: Rate limit exceeded. Waiting longer...")
                time.sleep(base_delay * (attempt + 2))
            else:
                break # Break on other HTTP errors
        except requests.exceptions.RequestException as e:
            print(f"Network Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
            else:
                return all_data # Return what we have
    else:
        print("Max retries exceeded")

    # If since_timestamp provided, filter out old ones
    if since_timestamp is not None:
        try:
            cutoff = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
            filtered = []
            for art in all_data:
                pub = art.get('published_at')
                if pub:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    if dt > cutoff:
                        filtered.append(art)
            all_data = filtered
        except ValueError:
            pass

    return all_data

# Execution
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("FinHubAPI")
    
    news_list = fetch_commodity_news(api_token=TOKEN)

    if news_list:
        print("\n--- Extracted Commodity News ---")
        for idx, item in enumerate(news_list[:5]):
            print(f"{idx+1}. {item.get('title')} ({item.get('source_name')}) - {item.get('published_at')}")
        print(f"... and {len(news_list)-5 if len(news_list) > 5 else 0} more.")
    else:
        print("Pipeline yielded no data.")