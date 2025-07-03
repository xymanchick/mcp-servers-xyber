# MCP Server for Twitter

This repository provides an MCP (Multi-Context Prompting) server implementation for Twitter actions. It exposes the following tools:

## Available Tools

### create_tweet
Create a new tweet with optional media, polls, replies or quotes.

**Args:**
- `text` (str): The text content of the tweet. Will be truncated to the configured maximum tweet length if necessary.
- `image_content` (optional, str): A Base64-encoded string of image data to attach as media. Requires media uploads to be enabled in config.
- `poll_options` (optional, list[str]): A list of 2 to 4 options to include in a poll.
- `poll_duration` (optional, int): Duration of the poll in minutes (must be between 5 and 10080).
- `in_reply_to_tweet_id` (optional, str): The ID of an existing tweet to reply to. Your text must include the author’s `@username`.
- `quote_tweet_id` (optional, str): The ID of an existing tweet to quote.

**Returns:**
- `str`: The ID of the created tweet on success, or an error message string.

### get_user_tweets
Retrieve recent tweets posted by a list of users.

**Args:**
- `user_ids` (List[str]): A list of Twitter user IDs whose tweets to fetch.
- `max_results` (optional, int): The maximum number of tweets to return per user (1–100, default 10).

**Returns:**
- `dict`: A mapping from user ID to a list of tweet texts, e.g. `{ "12345": ["Tweet1", "Tweet2"], "67890": ["Another tweet"] }`.

### follow_user
Follow another Twitter user by their user ID.

**Args:**
- `user_id` (str): The ID of the user to follow.

**Returns:**
- `str`: A success message confirming the follow.

### retweet_tweet
Retweet an existing tweet on behalf of the authenticated user.

**Args:**
- `tweet_id` (str): The ID of the tweet to retweet.

**Returns:**
- `str`: A success message confirming the retweet.

### `get_trends` 
Retrieve trending topics for one or more countries.

**Args**

| Name | Type | Description |
|------|------|-------------|
| `countries` | `list[str]` | One or more countries. |
| `max_trends` | `int`, optional | Maximum trends to return per country (1 – 50, default 50). |

**Returns**

`dict` – Maps each countries to a list of trending topic names.  
If an error occurs for a country, the list contains a single error string.


### `search_hashtag` 
Search recent tweets that contain a specific hashtag and return their texts, ordered by relevancy

**Args**

| Name | Type | Description |
|------|------|-------------|
| `hashtag` | `str` | Hashtag to search (with or without “#”). |
| `max_results` | `int`, optional | Maximum tweets to return (10 – 100, default 10). |

**Returns**

`list[str]` – The text of matched tweets, ordered by **likes + retweets**.

---

## Configuration

Create a `.env` file in the root directory containing:

```
TWITTER_API_KEY=<your_api_key>
TWITTER_API_SECRET_KEY=<your_api_secret_key>
TWITTER_ACCESS_TOKEN=<your_access_token>
TWITTER_ACCESS_TOKEN_SECRET=<your_access_token_secret>
TWITTER_BEARER_TOKEN=<your_bearer_token>
```

## Running the Server

Build and run the Docker container:

```bash
docker build -t mcp_server_twitter .
docker run -p 8008:8008 --env-file .env mcp_server_twitter
```

The server will be available at `http://localhost:8008/sse`.

## Example Client

```python
import os
import asyncio
import uuid

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_together import ChatTogether
from langchain_core.tools import StructuredTool

async def main():
    # Load environment variables from .env, should contain OPENAI_API_KEY
    load_dotenv()
    TOGETHER_TOKEN = os.getenv("TOGETHER_TOKEN")
    # Initialize LLM
    model = ChatTogether(
        together_api_key=TOGETHER_TOKEN,
        model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
    )

    # Connect to MCP server
    client = MultiServerMCPClient({
        "calculate": {
            "url": "http://localhost:8008/sse",
            "transport": "sse",
        }
    })

    # Get available tools
    tools: list[StructuredTool] = await client.get_tools()
    c_t = None
    for tool in tools:
        tool.return_direct = True
        if tool.name == "create_tweet":
            c_t = tool

    # Use case 1: Create agent with tools
    agent = create_react_agent(model, tools)

    # Example query using the agent
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Create a tweet about oranges"
        }]
    })
    print(response["messages"][-1].content)

    # Use case 2: Direct tool call
    image = "your base64 image"
    result: ToolMessage = await c_t.arun(
        tool_input={"text": "apples", "image_content": image},
        type=dict,
        response_format="content_and_artifact",
        tool_call_id=uuid.uuid4()
    )
    print("Tool result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```
