import os
import requests
import openai
import logging
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, get_summary_from_db, save_summary_to_db

load_dotenv()

init_db()

limiter = Limiter(key_func=get_remote_address)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")

cache = {}
CACHE_TTL = 300

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

required_env_vars = [
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("REDDIT_CLIENT_ID", REDDIT_CLIENT_ID),
    ("REDDIT_CLIENT_SECRET", REDDIT_CLIENT_SECRET),
    ("REDDIT_USER_AGENT", REDDIT_USER_AGENT),
]

for var_name, value in required_env_vars:
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {var_name}")

client = openai.OpenAI(api_key=OPENAI_API_KEY)


class SummaryRequest(BaseModel):
    topic: str
    summary_format: str = "text"
    sentiment_analysis: bool = False


class Post(BaseModel):
    title: str
    text: str
    url: str

class SummaryResponse(BaseModel):
    summary: str
    ui_summary: str
    posts: list[Post]


class UrlRequest(BaseModel):
    url: str

class TextRequest(BaseModel):
    text: str


@app.post("/summarize-url", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_url(request: Request, url_request: UrlRequest):
    try:
        res = requests.get(url_request.url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        posts = [{"title": url_request.url, "text": text, "url": url_request.url}]
        summary, ui_summary = summarize_text(posts, "URL Content")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_url: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from URL.")
    except Exception as e:
        logger.error(f"Exception in summarize_url: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")

@app.post("/summarize-text", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_text_endpoint(request: Request, text_request: TextRequest):
    try:
        posts = [{"title": "Raw Text", "text": text_request.text, "url": ""}]
        summary, ui_summary = summarize_text(posts, "Raw Text")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts}
    except Exception as e:
        logger.error(f"Exception in summarize_text_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


def is_valid_topic(topic: str):
    if not topic or not topic.strip() or len(topic.strip()) < 3:
        return False
    return True


async def get_hacker_news_posts(limit: int = 5):
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


def get_reddit_posts(topic: str, limit: int = 5):
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


def summarize_text(posts: list, topic: str, summary_format: str = "text", sentiment_analysis: bool = False):
    if not posts:
        return "No meaningful posts found to summarize.", ""

    # Check cache first
    cache_key = f"{topic}-{summary_format}-{sentiment_analysis}"
    cached_summary = get_summary_from_db(cache_key)
    if cached_summary:
        summary, ui_summary, timestamp = cached_summary
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"Returning cached summary for topic: {topic}")
            return summary, ui_summary

    # Main summary prompt
    prompt = f"Summarize the following posts on the topic '{topic}'."
    if summary_format == "bullets":
        prompt += " Use bullet points."
    elif summary_format == "tldr":
        prompt += " Provide a TL;DR."

    if sentiment_analysis:
        prompt += " Also, provide a sentiment analysis (positive, negative, or neutral)."

    prompt += "\n\n"

    for post in posts:
        prompt += f"Title: {post['title']}\n"
        prompt += f"Text: {post['text']}\n\n"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": prompt},
        ],
    )
    summary = response.choices[0].message.content

    # UI summary prompt
    ui_summary_prompt = f"Provide a very short, one-sentence summary of the following posts on the topic '{topic}':\n\n"
    for post in posts:
        ui_summary_prompt += f"Title: {post['title']}\n"
        ui_summary_prompt += f"Text: {post['text']}\n\n"

    ui_summary_response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides very short summaries."},
            {"role": "user", "content": ui_summary_prompt},
        ],
    )
    ui_summary = ui_summary_response.choices[0].message.content

    save_summary_to_db(cache_key, summary, ui_summary, time.time())
    return summary, ui_summary


@app.get("/trending-topics")
async def get_trending_topics():
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


@app.get("/summarize-hackernews", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_hackernews(request: Request):
    try:
        posts = await get_hacker_news_posts()
        summary, ui_summary = summarize_text(posts, "Hacker News")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Exception in summarize_hackernews: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


@app.get("/summarize", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_get(request: Request, topic: str, summary_format: str = "text", sentiment_analysis: bool = False):
    if not is_valid_topic(topic):
        raise HTTPException(status_code=400, detail="Topic must be a non-empty string with at least 3 characters.")
    logger.info(f"Received GET request for topic: {topic}")
    try:
        posts = get_reddit_posts(topic)
        summary, ui_summary = summarize_text(posts, topic, summary_format, sentiment_analysis)
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts}
    except HTTPException as e:
        raise e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_get: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from Reddit.")
    except Exception as e:
        logger.error(f"Exception in summarize_get: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


@app.post("/summarize", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_post(request: Request, summary_request: SummaryRequest):
    if not is_valid_topic(summary_request.topic):
        raise HTTPException(status_code=400, detail="Topic must be a non-empty string with at least 3 characters.")
    logger.info(f"Received POST request for topic: {summary_request.topic}")
    try:
        posts = get_reddit_posts(summary_request.topic)
        summary, ui_summary = summarize_text(posts, summary_request.topic, summary_request.summary_format, summary_request.sentiment_analysis)
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts}
    except HTTPException as e:
        raise e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_post: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from Reddit.")
    except Exception as e:
        logger.error(f"Exception in summarize_post: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


if __name__ == "__main__":
    import uvicorn

    def summarize_trending_topics():
        logger.info("Starting daily summary of trending topics...")
        try:
            trending_topics = requests.get("https://www.reddit.com/api/trending_subreddits.json", headers={"User-Agent": REDDIT_USER_AGENT}).json()["subreddit_names"]
            for topic in trending_topics:
                posts = get_reddit_posts(f"r/{topic}")
                summarize_text(posts, f"r/{topic}")
            logger.info("Finished daily summary of trending topics.")
        except Exception as e:
            logger.error(f"Error in summarize_trending_topics: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(summarize_trending_topics, 'interval', days=1)
    scheduler.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
