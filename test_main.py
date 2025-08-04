import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import requests_mock
from main import app

client = TestClient(app)

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

def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "<h1>Reddit Summarizer</h1>" in response.text


@patch("main.client.chat.completions.create")
def test_summarize_endpoint(mock_openai_create, mock_reddit_api):
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
