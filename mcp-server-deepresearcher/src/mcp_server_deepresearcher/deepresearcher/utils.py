from langchain_together import ChatTogether
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai.chat_models import ChatMistralAI
from typing import Dict, Any, Optional, List
from mcp_server_deep_researcher.deep_researcher.config import LLM_Config
import re
import logging

logger = logging.getLogger(__name__)




def setup_llm(LLM_Config: LLM_Config):
    """Initialize the LLM based on environment configuration"""
    logger.info("Setting up main LLM...")
    MODEL_PROVIDER = LLM_Config.MODEL_PROVIDER
    MODEL_NAME = LLM_Config.MODEL_NAME
    TOGETHER_API_KEY = LLM_Config.TOGETHER_API_KEY
    GOOGLE_API_KEY = LLM_Config.GOOGLE_API_KEY
    MISTRAL_API_KEY = LLM_Config.MISTRAL_API_KEY
    
    logger.info(f"Using model provider: {MODEL_PROVIDER}, model: {MODEL_NAME}")
    
    if MODEL_PROVIDER == "together":
        if not TOGETHER_API_KEY:
            logger.error("TOGETHER_API_KEY environment variable is required for Together AI")
            raise ValueError("TOGETHER_API_KEY environment variable is required for Together AI")
        try:
            logger.info("Initializing Together AI model")
            return ChatTogether(
                together_api_key=TOGETHER_API_KEY, #type: ignore
                model=MODEL_NAME #type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to initialize Together AI model: {e}")
            raise
    elif MODEL_PROVIDER == "google":
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY environment variable is required for Google AI")
            raise ValueError("GOOGLE_API_KEY environment variable is required for Google AI")
        try:
            logger.info("Initializing Google AI model")
            return ChatGoogleGenerativeAI(
                google_api_key=GOOGLE_API_KEY, #type: ignore
                model=MODEL_NAME #type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google AI model: {e}")
            raise
    elif MODEL_PROVIDER == "mistral":
        if not MISTRAL_API_KEY:
            logger.error("MISTRAL_API_KEY environment variable is required for Mistral AI")
            raise ValueError("MISTRAL_API_KEY environment variable is required for Mistral AI")
        try:
            logger.info("Initializing Mistral AI model")
            return ChatMistralAI(
                api_key=MISTRAL_API_KEY, #type: ignore
                model=MODEL_NAME #type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to initialize Mistral AI model: {e}")
            raise
    else:
        logger.error(f"Unsupported model provider: {MODEL_PROVIDER}")
        raise ValueError(f"Unsupported model provider: {MODEL_PROVIDER}")


def setup_spare_llm(LLM_Config: LLM_Config):
    """Initialize the LLM based on environment configuration"""
    logger.info("Setting up main LLM...")
    MODEL_PROVIDER_SPARE = LLM_Config.MODEL_PROVIDER_SPARE
    MODEL_NAME_SPARE = LLM_Config.MODEL_NAME_SPARE
    TOGETHER_API_KEY = LLM_Config.TOGETHER_API_KEY
    GOOGLE_API_KEY = LLM_Config.GOOGLE_API_KEY
    MISTRAL_API_KEY = LLM_Config.MISTRAL_API_KEY
    
    logger.info(f"Using model provider: {MODEL_PROVIDER_SPARE}, model: {MODEL_NAME_SPARE}")
    
    if MODEL_PROVIDER_SPARE == "together":
        if not TOGETHER_API_KEY:
            logger.error("TOGETHER_API_KEY environment variable is required for Together AI")
            raise ValueError("TOGETHER_API_KEY environment variable is required for Together AI")
        try:
            logger.info("Initializing Together AI model")
            return ChatTogether(
                together_api_key=TOGETHER_API_KEY, #type: ignore
                model=MODEL_NAME_SPARE
            )
        except Exception as e:
            logger.error(f"Failed to initialize Together AI model: {e}")
            raise
    elif MODEL_PROVIDER_SPARE == "google":
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY environment variable is required for Google AI")
            raise ValueError("GOOGLE_API_KEY environment variable is required for Google AI")
        try:
            logger.info("Initializing Google AI model")
            return ChatGoogleGenerativeAI(
                google_api_key=GOOGLE_API_KEY, #type: ignore
                model=MODEL_NAME_SPARE #type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google AI model: {e}")
            raise
    elif MODEL_PROVIDER_SPARE == "mistral":
        if not MISTRAL_API_KEY:
            logger.error("MISTRAL_API_KEY environment variable is required for Mistral AI")
            raise ValueError("MISTRAL_API_KEY environment variable is required for Mistral AI")
        try:
            logger.info("Initializing Mistral AI model")
            return ChatMistralAI(
                api_key=MISTRAL_API_KEY,
                model=MODEL_NAME_SPARE  #type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to initialize Mistral AI model: {e}")
            raise
    else:
        logger.error(f"Unsupported model provider: {MODEL_PROVIDER_SPARE}")
        raise ValueError(f"Unsupported model provider: {MODEL_PROVIDER_SPARE}")
    
def clean_response(response_text: str) -> str:
    """Clean the response text by removing markdown code block markers if present."""
    try:
        # Clean response text by removing markdown code block markers if present
        cleaned_response = response_text.strip()
        if cleaned_response.startswith('```json'):
            # Remove ```json from start and ``` from end
            cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove ```
        elif cleaned_response.startswith('```'):
            # Remove ``` from start and end (generic code block)
            cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()
        return cleaned_response 
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")
        return response_text


def load_mcp_servers_config(
    apify_token: Optional[str] = None,
    mcp_telegram_url: Optional[str] = None,
    telegram_token: Optional[str] = None,
    telegram_channel: Optional[str] = None,
    mcp_youtube_url: Optional[str] = None,
    mcp_tavily_url: Optional[str] = None,
    mcp_arxiv_url: Optional[str] = None,
    mcp_twitter_url: Optional[str] = None,
    apify_actors_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Load and configure MCP servers based on provided environment variables.
    
    Args:
        apify_token: Apify API token
        mcp_telegram_url: Telegram MCP server URL
        telegram_token: Telegram bot token
        telegram_channel: Telegram channel
        mcp_youtube_url: YouTube MCP server URL
        mcp_tavily_url: Tavily MCP server URL
        mcp_arxiv_url: Arxiv MCP server URL
        mcp_twitter_url: Twitter MCP server URL
        apify_actors_list: List of Apify actors to include (defaults to tweet-scraper)
    
    Returns:
        Dictionary containing MCP server configurations
    """
    mcp_servers_config = {}
    
    # Default Apify actors if not specified
    if apify_actors_list is None:
        apify_actors_list = ["apidojo/tweet-scraper"]
    
    # --- Apify MCP Server ---
    try:
        logger.info(f"DEBUG: Checking Apify configuration - APIFY_TOKEN={'SET' if apify_token else 'NOT SET'} ({len(apify_token) if apify_token else 0} chars)")
        if apify_token is not None:
            # Build URL with specific actors to limit what's available
            actors_param = ",".join(apify_actors_list)
            apify_url = f"https://mcp.apify.com/sse?actors={actors_param}"
            
            mcp_servers_config["apify"] = {
                "transport": "sse",
                "url": apify_url,
                "headers": {
                    "Authorization": "Bearer " + apify_token
                }
            }
            logger.info(f"Apify MCP server configured with {len(apify_actors_list)} specific actors: {apify_actors_list}")
        else:
            logger.info("Apify MCP server not configured - APIFY_TOKEN is None. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Apify MCP server: {e}")

    # --- Telegram MCP Server ---
    try:
        if mcp_telegram_url and telegram_token and telegram_channel:
            mcp_servers_config["telegram"] = {
                "name": "telegram",
                "url": mcp_telegram_url,
                "transport": "streamable_http",
                "description": "MCP server for Telegram messaging",
                "headers": {
                    "X-Telegram-Token": telegram_token,
                    "X-Telegram-Channel": telegram_channel
                }
            }
            logger.info("Telegram MCP server configured")
        else:
            logger.info("Telegram MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Telegram MCP server: {e}")

    # --- YouTube MCP Server ---
    try:
        if mcp_youtube_url and mcp_youtube_url != "":
            mcp_servers_config["youtube"] = {
                "name": "youtube", 
                "url": mcp_youtube_url,
                "transport": "streamable_http",
                "description": "MCP server for YouTube video search and transcripts"
            }
            logger.info("YouTube MCP server configured")
        else:
            logger.info("YouTube MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring YouTube MCP server: {e}")

    # --- Tavily MCP Server ---
    try:
        if mcp_tavily_url and mcp_tavily_url != "":
            mcp_servers_config["tavily"] = {
                "name": "tavily",
                "url": mcp_tavily_url,
                "transport": "streamable_http", 
                "description": "MCP server for Tavily web search"
            }
            logger.info("Tavily MCP server configured")
        else:
            logger.info("Tavily MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Tavily MCP server: {e}")

    # --- Arxiv MCP Server ---
    try:
        if mcp_arxiv_url and mcp_arxiv_url != "":
            mcp_servers_config["arxiv"] = {
                "name": "arxiv",
                "url": mcp_arxiv_url,
                "transport": "streamable_http",
                "description": "MCP server for searching arXiv papers"
            }
            logger.info("Arxiv MCP server configured")
        else:
            logger.info("Arxiv MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Arxiv MCP server: {e}")

    # --- Twitter MCP Server ---
    try:
        if mcp_twitter_url and mcp_twitter_url != "":
            mcp_servers_config["twitter"] = {
                "name": "twitter",
                "url": mcp_twitter_url,
                "transport": "streamable_http",
                "description": "MCP server for Twitter integration"
            }
            logger.info("Twitter MCP server configured")
        else:
            logger.info("Twitter MCP server not configured. Skipping...")
    except Exception as e:
        logger.error(f"Error configuring Twitter MCP server: {e}")

    logger.info(f"Total MCP servers configured: {len(mcp_servers_config)}")
    return mcp_servers_config




def create_mcp_tasks(mcp_tools, search_query):
    tasks = []
    task_names = []
    for tool in mcp_tools:
        if tool.name == 'tavily_web_search':
            # Use ** to unpack the dictionary into keyword arguments
            tasks.append(tool.coroutine(**{"query": search_query, "max_results": 3}))
            task_names.append(tool.name) # Track the name
            logging.info(f"  - Added task: {tool.name}")
        elif tool.name == 'arxiv_search':
            tasks.append(tool.coroutine(**{"query": search_query, "max_results": 3}))
            task_names.append(tool.name) # Track the name
            logging.info(f"  - Added task: {tool.name}")
        elif tool.name == 'youtube_search_and_transcript':
            tasks.append(tool.coroutine(**{"query": search_query, "max_results": 2}))
            task_names.append(tool.name) # Track the name
            logging.info(f"  - Added task: {tool.name}")
        # This is where you match and activate the Apify tool
        elif tool.name == 'apidojo-slash-tweet-scraper':
            logging.info(f"  - Adding task: {tool.name}")
            
            actor_input = {
                "searchTerms": [search_query],
                "limit": 15
            }
                        
            tasks.append(tool.coroutine(**actor_input))
            task_names.append(tool.name)
    return tasks, task_names

def extract_source_info(content: str, source_name: str) -> Dict[str, str]:
    """Extracts Title and URL from a tool's string output."""
    source_info = {"name": source_name, "title": "N/A", "url": "N/A"}
    
    # Try to find a URL first
    url_match = re.search(r'URL: (https?://[^\s]+)', content)
    if url_match:
        source_info["url"] = url_match.group(1)
    
    # Try to find a Title
    title_match = re.search(r'Title: ([^\n]+)', content)
    if title_match:
        source_info["title"] = title_match.group(1).strip()
    # If no title, use the first line as a fallback
    elif not title_match:
        source_info["title"] = content.split('\n')[0].strip()
        
    return source_info

# --- Helper Function 2: To format the final sources list ---

def format_sources(sources: List[Dict[str, str]]) -> str:
    """Formats a list of source dictionaries into a numbered string."""
    if not sources:
        return "No valid sources found."
    
    formatted_list = []
    for i, source in enumerate(sources):
        # Format as: 1. [Source Name] Title of Content (URL)
        formatted_list.append(
            f"{i + 1}. [{source['name']}] {source['title']} ({source.get('url', 'No URL')})"
        )
    return "\n".join(formatted_list)