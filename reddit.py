import os
import requests
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

def get_reddit_posts(topic: str, limit: int = 5):
    """Fetches posts from Reddit for a given topic."""
    auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    headers = {"User-Agent": REDDIT_USER_AGENT}

    # Get an access token
    res = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=auth,
        data={"grant_type": "client_credentials"},
        headers=headers,
    )
    res.raise_for_status()
    access_token = res.json()["access_token"]

    # Search for posts
    headers["Authorization"] = f"bearer {access_token}"
    url = "https://oauth.reddit.com/search"
    params = {"q": topic, "limit": limit, "sort": "top", "type": "link"}
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()

    posts = res.json()["data"]["children"]
    logger.info(f"Found {len(posts)} posts")
    if not posts:
        raise HTTPException(status_code=404, detail="No Reddit posts found for this topic.")

    filtered_posts = [
        {"title": post["data"]["title"], "text": post["data"].get("selftext", ""), "url": post["data"].get("url", "")}
        for post in posts
        if post["data"].get("selftext", "").strip()
        and len(post["data"].get("selftext", "").strip()) >= 20
        and not post["data"].get("is_reddit_media_domain", False)
        and not post["data"].get("is_video", False)
        and post["data"].get("post_hint") != "link"
    ]
    logger.info(f"Found {len(filtered_posts)} filtered posts")
    return filtered_posts

def get_trending_topics():
    """Fetches trending topics from Reddit."""
    try:
        headers = {"User-Agent": REDDIT_USER_AGENT}
        res = requests.get("https://www.reddit.com/api/trending_subreddits.json", headers=headers)
        res.raise_for_status()
        data = res.json()
        return [f"r/{subreddit}" for subreddit in data["subreddit_names"]]
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in get_trending_topics: {e}")
        raise HTTPException(status_code=502, detail="Error fetching trending topics from Reddit.")
    except Exception as e:
        logger.error(f"Exception in get_trending_topics: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching trending topics: {e}")
