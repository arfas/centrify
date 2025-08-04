import os
import requests
import openai
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

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
    if not posts:
        raise HTTPException(status_code=404, detail="No Reddit posts found for this topic.")
    return [
        {"title": post["data"]["title"], "text": post["data"].get("selftext", "")}
        for post in posts
        if post["data"].get("selftext", "").strip()
    ]


def summarize_text(posts: list, topic: str):
    prompt = (
        f"Summarize the following Reddit posts on the topic '{topic}'.\n"
        f"Highlight key opinions, major concerns, and recurring themes:\n\n"
    )
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
    return response.choices[0].message.content


@app.get("/", response_class=FileResponse)
async def read_index():
    return FileResponse("static/index.html")


@app.get("/summarize", response_model=SummaryResponse)
async def summarize_get(topic: str):
    logger.info(f"Received GET request for topic: {topic}")
    try:
        posts = get_reddit_posts(topic)
        summary = summarize_text(posts, topic)
        return {"summary": summary}
    except HTTPException as e:
        raise e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_get: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Exception in summarize_get: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_post(request: SummaryRequest):
    logger.info(f"Received POST request for topic: {request.topic}")
    try:
        posts = get_reddit_posts(request.topic)
        summary = summarize_text(posts, request.topic)
        return {"summary": summary}
    except HTTPException as e:
        raise e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError in summarize_post: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Exception in summarize_post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
