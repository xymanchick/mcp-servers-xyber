# MCP Server - Wikipedia

> **General:** This repository provides an MCP (Model Context Protocol) server implementation for interacting with the Wikipedia API.

## Overview

This project implements a microservice that exposes a comprehensive set of Wikipedia tools through the Model Context Protocol (MCP). It uses the `wikipedia-api` library to search, retrieve, and process Wikipedia articles.

## MCP Tools

-   `search_wikipedia`: Searches for articles matching a query and returns a list of titles.
-   `get_article`: Retrieves the full summary and content of an article by its exact title.
-   `get_summary`: Fetches just the summary of an article.
-   `get_sections`: Lists all section titles in an article.
-   `get_links`: Lists all links within an article.
-   `get_related_topics`: Finds related topics based on an article's internal links.

## Requirements

-   Python 3.12+
-   UV (for dependency management)
-   Docker (optional, for containerization)

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd mcp-server-wikipedia
    ```
2.  **Create `.env` File from `.env.example`:**
    Create a `.env` file and customize the settings. It is highly recommended to set a descriptive `WIKIPEDIA_USER_AGENT`.
    ```dotenv
    # .env
    MCP_WIKIPEDIA_PORT=8006
    WIKIPEDIA_USER_AGENT="MyCoolAgent/1.0 (https://example.com/my-agent; my-email@example.com)"
    WIKIPEDIA_LANGUAGE="en"
    ```

3.  **Install Dependencies:**
    ```bash
    uv sync
    ```

## Running the Server

### Locally

```bash
# Basic run (uses port 8006 by default)
python -m mcp_server_wikipedia

# Custom port and host
python -m mcp_server_wikipedia --host 127.0.0.1 --port 8007