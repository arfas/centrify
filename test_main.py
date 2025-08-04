import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import requests_mock
from main import app

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test_agent")
    return TestClient(app)


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
                                "selftext": "This is the first post.",
                            }
                        },
                        {
                            "data": {
                                "title": "Post 2",
                                "selftext": "This is the second post.",
                            }
                        },
                    ]
                }
            },
        )
        yield m


def test_read_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "<h1>Reddit Summarizer</h1>" in response.text


@patch("main.client.chat.completions.create")
def test_summarize_get_endpoint(mock_openai_create, mock_reddit_api, client):
    mock_openai_create.return_value.choices[0].message.content = "This is a summary."

    response = client.get("/summarize?topic=python")

    assert response.status_code == 200
    assert response.json() == {"summary": "This is a summary."}

    # Check that the OpenAI API was called with the correct prompt
    mock_openai_create.assert_called_once()
    args, kwargs = mock_openai_create.call_args
    messages = kwargs["messages"]
    assert "Summarize the following Reddit posts on the topic 'python'" in messages[1]["content"]
    assert "Highlight key opinions, major concerns, and recurring themes" in messages[1]["content"]
    assert "Title: Post 1" in messages[1]["content"]
    assert "Text: This is the first post." in messages[1]["content"]
    assert "Title: Post 2" in messages[1]["content"]
    assert "Text: This is the second post." in messages[1]["content"]


@patch("main.client.chat.completions.create")
def test_summarize_post_endpoint(mock_openai_create, mock_reddit_api, client):
    mock_openai_create.return_value.choices[0].message.content = "This is a summary."

    response = client.post("/summarize", json={"topic": "python"})

    assert response.status_code == 200
    assert response.json() == {"summary": "This is a summary."}


@patch("main.get_reddit_posts", return_value=[])
def test_summarize_no_posts_found(mock_get_posts, client):
    response = client.get("/summarize?topic=xyz123noresults")
    assert response.status_code == 404
    assert response.json() == {"detail": "No Reddit posts found for this topic."}
