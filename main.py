import os
import time
import logging
import requests
import secrets
import sqlite3
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db
from reddit import get_reddit_posts, get_trending_topics
from hackernews import get_hacker_news_posts
from summarizer import summarize_text

load_dotenv()

init_db()

limiter = Limiter(key_func=get_remote_address)

security = HTTPBasic()

# Hardcoded credentials (should be moved to environment variables)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")

class SummaryRequest(BaseModel):
    topic: str
    summary_format: str = "text"
    sentiment_analysis: bool = False
    summary_length: str = "medium"
    prompt_template: str = "basic"

class Post(BaseModel):
    title: str
    text: str
    url: str

class SummaryResponse(BaseModel):
    summary: str
    ui_summary: str
    posts: list[Post]
    timestamp: float

class UrlRequest(BaseModel):
    url: str

class TextRequest(BaseModel):
    text: str

def is_valid_topic(topic: str):
    """Checks if a topic is valid."""
    if not topic or not topic.strip() or len(topic.strip()) < 3:
        return False
    return True

@app.post("/summarize-url", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_url(request: Request, url_request: UrlRequest):
    """Summarizes the content of a given URL."""
    try:
        res = requests.get(url_request.url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        posts = [{"title": url_request.url, "text": text, "url": url_request.url}]
        summary, ui_summary = summarize_text(posts, "URL Content")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts, "timestamp": time.time()}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_url: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from URL.")
    except Exception as e:
        logger.error(f"Exception in summarize_url: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")

@app.post("/summarize-text", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_text_endpoint(request: Request, text_request: TextRequest):
    """Summarizes a given text."""
    try:
        posts = [{"title": "Raw Text", "text": text_request.text, "url": ""}]
        summary, ui_summary = summarize_text(posts, "Raw Text")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Exception in summarize_text_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")

@app.get("/trending-topics")
async def trending_topics():
    """Returns a list of trending topics from Reddit."""
    return await get_trending_topics()

@app.get("/summarize-hackernews", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_hackernews(request: Request):
    """Summarizes the top stories from Hacker News."""
    try:
        posts = await get_hacker_news_posts()
        summary, ui_summary = summarize_text(posts, "Hacker News")
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts, "timestamp": time.time()}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Exception in summarize_hackernews: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")

@app.get("/summarize", response_model=SummaryResponse)
@limiter.limit("5/minute")
async def summarize_get(request: Request, topic: str, summary_format: str = "text", sentiment_analysis: bool = False, summary_length: str = "medium", prompt_template: str = "basic"):
    """Summarizes a given topic from Reddit."""
    if not is_valid_topic(topic):
        raise HTTPException(status_code=400, detail="Topic must be a non-empty string with at least 3 characters.")
    logger.info(f"Received GET request for topic: {topic}")
    try:
        posts = get_reddit_posts(topic)
        summary, ui_summary = summarize_text(posts, topic, summary_format, sentiment_analysis, summary_length, prompt_template)
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts, "timestamp": time.time()}
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
    """Summarizes a given topic from Reddit."""
    if not is_valid_topic(summary_request.topic):
        raise HTTPException(status_code=400, detail="Topic must be a non-empty string with at least 3 characters.")
    logger.info(f"Received POST request for topic: {summary_request.topic}")
    try:
        posts = get_reddit_posts(summary_request.topic)
        summary, ui_summary = summarize_text(posts, summary_request.topic, summary_request.summary_format, summary_request.sentiment_analysis, summary_request.summary_length, summary_request.prompt_template)
        return {"summary": summary, "ui_summary": ui_summary, "posts": posts, "timestamp": time.time()}
    except HTTPException as e:
        raise e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_post: {e}")
        raise HTTPException(status_code=502, detail="Error fetching data from Reddit.")
    except Exception as e:
        logger.error(f"Exception in summarize_post: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")

@app.get("/admin")
async def get_admin_summaries(username: str = Depends(get_current_username)):
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("SELECT topic, summary, ui_summary, timestamp FROM summaries")
    summaries = c.fetchall()
    conn.close()
    return summaries

@app.delete("/admin/delete/{topic}")
async def delete_summary(topic: str, username: str = Depends(get_current_username)):
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("DELETE FROM summaries WHERE topic=?", (topic,))
    conn.commit()
    conn.close()
    return {"message": "Summary deleted successfully."}

from fastapi.responses import FileResponse

@app.get("/admin-ui")
async def get_admin_ui():
    return FileResponse("admin.html")

if __name__ == "__main__":
    import uvicorn

    def summarize_trending_topics():
        """Summarizes the trending topics from Reddit."""
        logger.info("Starting daily summary of trending topics...")
        try:
            trending_topics_list = get_trending_topics()
            for topic in trending_topics_list:
                posts = get_reddit_posts(topic)
                summarize_text(posts, topic)
            logger.info("Finished daily summary of trending topics.")
        except Exception as e:
            logger.error(f"Error in summarize_trending_topics: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(summarize_trending_topics, 'interval', days=1)
    scheduler.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
