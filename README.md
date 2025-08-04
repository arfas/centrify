# Centrify - Social Media Summarizer

This project is a lightweight web app that summarizes social media content (starting with Reddit) using OpenAI GPT.

## How to run

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up your environment variables:**

    Create a `.env` file in the root of the project and add your API keys:
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    REDDIT_CLIENT_ID=your_reddit_client_id_here
    REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
    REDDIT_USER_AGENT=your_reddit_user_agent_here
    ```

3.  **Run the app:**
    ```bash
    uvicorn main:app --reload
    ```

4.  **Access the API:**

    The API will be running at `http://127.0.0.1:8000`.

    You can access the summarize endpoint at `http://127.0.0.1:8000/summarize?topic=YOUR_TOPIC`