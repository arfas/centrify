import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import requests_mock
from main import app, get_reddit_posts, summarize_text, limiter, cache
from database import init_db, get_summary_from_db, save_summary_to_db
import requests
import os
import time

limiter.enabled = False

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()

@pytest.fixture
def test_db():
    init_db()
    yield
    if os.path.exists("summaries.db"):
        os.remove("summaries.db")

@pytest.fixture
def mock_reddit_api():
    with requests_mock.Mocker() as m:
        m.post(
            "https://www.reddit.com/api/v1/access_token",
            json={"access_token": "test_token", "token_type": "bearer", "expires_in": 3600},
        )
        m.get(
            "https://oauth.reddit.com/search",
            json={
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "Post 1",
                                "selftext": "This is the first post and it is long enough.",
                                "is_reddit_media_domain": False,
                                "is_video": False,
                                "post_hint": "text",
                                "url": "http://test.com/1"
                            }
                        },
                        {
                            "data": {
                                "title": "Post 2",
                                "selftext": "This is the second post and it is also long enough.",
                                "is_reddit_media_domain": False,
                                "is_video": False,
                                "post_hint": "text",
                                "url": "http://test.com/2"
                            }
                        },
                    ]
                }
            },
        )
        yield m

def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Reddit & Hacker News Summarizer" in response.text


@patch("main.client.chat.completions.create")
def test_summarize_get_endpoint(mock_openai_create, mock_reddit_api, test_db):
    mock_openai_create.return_value.choices[0].message.content = "This is a summary."

    response = client.get("/summarize?topic=python")

    assert response.status_code == 200
    assert response.json()["summary"] == "This is a summary."

    # Check that the OpenAI API was called with the correct prompt
    assert mock_openai_create.call_count == 2 # one for summary, one for ui summary

@patch("main.client.chat.completions.create")
def test_summarize_post_endpoint(mock_openai_create, mock_reddit_api, test_db):
    mock_openai_create.return_value.choices[0].message.content = "This is a summary."

    response = client.post("/summarize", json={"topic": "python"})

    assert response.status_code == 200
    assert response.json()["summary"] == "This is a summary."

    # Check that the OpenAI API was called with the correct prompt
    assert mock_openai_create.call_count == 2 # one for summary, one for ui summary

@patch("main.client.chat.completions.create")
def test_summarize_filters_empty_selftext(mock_openai_create, mock_reddit_api, test_db):
    # Override the mock to return one post with empty selftext
    mock_reddit_api.get(
        "https://oauth.reddit.com/search",
        json={
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Post 1",
                            "selftext": "This is the first post and it is long enough.",
                            "is_reddit_media_domain": False,
                            "is_video": False,
                            "post_hint": "text",
                            "url": "http://test.com/1"
                        }
                    },
                    {
                        "data": {
                            "title": "Post 2",
                            "selftext": "", # Empty selftext
                        }
                    },
                    {
                        "data": {
                            "title": "Post 3",
                            "selftext": "   ", # Whitespace selftext
                        }
                    },
                ]
            }
        },
    )
    mock_openai_create.return_value.choices[0].message.content = "This is a summary."

    response = client.get("/summarize?topic=python")

    assert response.status_code == 200
    assert response.json()["summary"] == "This is a summary."

    # Check that the OpenAI API was called with the correct prompt
    assert mock_openai_create.call_count == 2 # one for summary, one for ui summary

def test_summarize_no_results(mock_reddit_api, test_db):
    # Override the mock to return no posts
    mock_reddit_api.get(
        "https://oauth.reddit.com/search",
        json={"data": {"children": []}},
    )

    response = client.get("/summarize?topic=python")

    assert response.status_code == 404
    assert response.json() == {"detail": "No Reddit posts found for this topic."}

def test_summarize_invalid_topic(test_db):
    response = client.get("/summarize?topic=a")
    assert response.status_code == 400
    assert response.json() == {"detail": "Topic must be a non-empty string with at least 3 characters."}

    response = client.get("/summarize?topic=%20%20")
    assert response.status_code == 400
    assert response.json() == {"detail": "Topic must be a non-empty string with at least 3 characters."}

    response = client.post("/summarize", json={"topic": "a"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Topic must be a non-empty string with at least 3 characters."}

    response = client.post("/summarize", json={"topic": "  "})
    assert response.status_code == 400
    assert response.json() == {"detail": "Topic must be a non-empty string with at least 3 characters."}

@patch("main.get_reddit_posts", side_effect=requests.exceptions.HTTPError("Reddit API is down"))
def test_summarize_reddit_api_error(mock_get_reddit_posts, test_db):
    response = client.get("/summarize?topic=python")
    assert response.status_code == 502
    assert response.json() == {"detail": "Error fetching data from Reddit."}

@patch("main.summarize_text", side_effect=Exception("OpenAI API is down"))
def test_summarize_openai_api_error(mock_summarize_text, mock_reddit_api, test_db):
    response = client.get("/summarize?topic=python")
    assert response.status_code == 500
    assert "Error generating summary: OpenAI API is down" in response.json()["detail"]

def test_get_trending_topics(requests_mock):
    requests_mock.get("https://www.reddit.com/api/trending_subreddits.json", json={"subreddit_names": ["news", "gaming"]})
    response = client.get("/trending-topics")
    assert response.status_code == 200
    assert response.json() == ["r/news", "r/gaming"]

@patch("main.get_hacker_news_posts")
def test_summarize_hackernews(mock_get_hacker_news_posts, test_db):
    mock_get_hacker_news_posts.return_value = [{"title": "Test Post", "text": "This is a test post.", "url": "http://test.com"}]
    with patch("main.summarize_text") as mock_summarize_text:
        mock_summarize_text.return_value = "This is a summary.", "This is a UI summary."
        response = client.get("/summarize-hackernews")
        assert response.status_code == 200
        assert response.json()["summary"] == "This is a summary."

def test_caching(test_db):
    topic = "test_topic"
    summary = "test_summary"
    ui_summary = "test_ui_summary"
    timestamp = time.time()
    save_summary_to_db(topic, summary, ui_summary, timestamp)
    cached_summary, cached_ui_summary, cached_timestamp = get_summary_from_db(topic)
    assert summary == cached_summary
    assert ui_summary == cached_ui_summary
    assert timestamp == cached_timestamp

def test_get_admin_summaries_no_auth():
    response = client.get("/admin")
    assert response.status_code == 401

def test_get_admin_summaries_with_auth(test_db):
    response = client.get("/admin", auth=("admin", "admin123"))
    assert response.status_code == 200

def test_delete_summary(test_db):
    topic = "test_topic"
    summary = "test_summary"
    ui_summary = "test_ui_summary"
    timestamp = time.time()
    save_summary_to_db(topic, summary, ui_summary, timestamp)

    response = client.delete(f"/admin/delete/{topic}", auth=("admin", "admin123"))
    assert response.status_code == 200
    assert response.json() == {"message": "Summary deleted successfully."}

    cached_summary = get_summary_from_db(topic)
    assert cached_summary is None
