import requests
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def get_hacker_news_posts(limit: int = 5):
    """Fetches top stories from Hacker News."""
    try:
        res = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        res.raise_for_status()
        top_stories_ids = res.json()

        posts = []
        for story_id in top_stories_ids[:limit]:
            story_res = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            story_res.raise_for_status()
            story_data = story_res.json()
            if story_data.get("text"):
                posts.append({"title": story_data["title"], "text": story_data["text"], "url": story_data.get("url", "")})
        return posts
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in get_hacker_news_posts: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from Hacker News.")
    except Exception as e:
        logger.error(f"Exception in get_hacker_news_posts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching data from Hacker News: {e}")
