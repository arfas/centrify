import os
import time
import openai
from database import get_summary_from_db, save_summary_to_db
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CACHE_TTL = 300

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def summarize_text(posts: list, topic: str, summary_format: str = "text", sentiment_analysis: bool = False, summary_length: str = "medium", prompt_template: str = "basic"):
    """Summarizes text using the OpenAI API."""
    if not posts:
        return "No meaningful posts found to summarize.", ""

    # Check cache first
    cache_key = f"{topic}-{summary_format}-{sentiment_analysis}-{summary_length}-{prompt_template}"
    cached_summary = get_summary_from_db(cache_key)
    if cached_summary:
        summary, ui_summary, timestamp = cached_summary
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"Returning cached summary for topic: {topic}")
            return summary, ui_summary

    # Main summary prompt
    if prompt_template == "basic":
        prompt = f"Summarize the following social media posts about {topic} in a concise and neutral tone. Focus on key points, opinions, and emerging trends. Ignore spam or low-quality content."
    elif prompt_template == "sentiment":
        prompt = f"Analyze and summarize the following posts about {topic}. Identify the overall sentiment (positive, negative, mixed) and highlight representative comments for each perspective."
    elif prompt_template == "comparative":
        prompt = f"Given Reddit, Twitter, and YouTube posts about {topic}, summarize each platform’s dominant sentiment and highlight how the conversation differs between them."
    elif prompt_template == "daily":
        prompt = f"Provide a daily digest summary of online discussions about {topic} across Reddit, Twitter, and YouTube. Include major developments, shifts in sentiment, and any viral trends or keywords."
    elif prompt_template == "executive":
        prompt = f"Summarize the key insights from these social media discussions on {topic} as if reporting to an executive. Use bullet points, avoid slang, and emphasize impact and emerging patterns."
    elif prompt_template == "ui":
        prompt = f"Write a short and engaging summary of these posts on {topic}, suitable for display on a dashboard. Keep it under 100 words and highlight trending ideas or questions."
    else:
        prompt = f"Summarize the following posts on the topic '{topic}'."

    if summary_format == "bullets":
        prompt += " Use bullet points."
    elif summary_format == "tldr":
        prompt += " Provide a TL;DR."

    if sentiment_analysis:
        prompt += " Also, provide a sentiment analysis (positive, negative, or neutral)."

    if summary_length == "short":
        prompt += " The summary should be about 50 words."
    elif summary_length == "long":
        prompt += " The summary should be about 200 words."
    else:
        prompt += " The summary should be about 100 words."

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
