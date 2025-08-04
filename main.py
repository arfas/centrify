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

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

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


class SummaryResponse(BaseModel):
    summary: str


def is_valid_topic(topic: str):
    if not topic or not topic.strip() or len(topic.strip()) < 3:
        return False
    return True


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
        {"title": post["data"]["title"], "text": post["data"].get("selftext", "")}
        for post in posts
        if post["data"].get("selftext", "").strip()
        and len(post["data"].get("selftext", "").strip()) >= 20
        and not post["data"].get("is_reddit_media_domain", False)
        and not post["data"].get("is_video", False)
        and post["data"].get("post_hint") != "link"
    ]
    logger.info(f"Found {len(filtered_posts)} filtered posts")
    return filtered_posts


def summarize_text(posts: list, topic: str):
    if not posts:
        return "No meaningful posts found to summarize."
    if topic in cache:
        summary, timestamp = cache[topic]
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"Returning cached summary for topic: {topic}")
            return summary

    prompt = (
        f"Summarize the following Reddit posts on the topic '{topic}'.\n"
        f"Highlight key opinions, major concerns, and recurring themes:\n\n"
    )
    for post in posts:
        prompt += f"Title: {post['title']}\n"
        prompt += f"Text: {post['text']}\n\n"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # switched from gpt-4 to gpt-3.5-turbo
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": prompt},
        ],
    )
    summary = response.choices[0].message.content
    cache[topic] = (summary, time.time())
    return summary


@app.get("/", response_class=FileResponse)
async def read_index():
    return FileResponse("static/index.html")


@app.get("/summarize", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_get(request: Request, topic: str):
    if not is_valid_topic(topic):
        raise HTTPException(status_code=400, detail="Topic must be a non-empty string with at least 3 characters.")
    logger.info(f"Received GET request for topic: {topic}")
    try:
        posts = get_reddit_posts(topic)
        summary = summarize_text(posts, topic)
        return {"summary": summary}
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
        summary = summarize_text(posts, summary_request.topic)
        return {"summary": summary}
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
