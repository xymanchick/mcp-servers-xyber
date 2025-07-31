import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

class LLM_Config(BaseModel):
    """Configuration settings for the LLMs."""
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "google")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-1.5-pro-latest")
    MODEL_PROVIDER_SPARE: str = os.getenv("MODEL_PROVIDER_SPARE", "together")
    MODEL_NAME_SPARE: str = os.getenv("MODEL_NAME_SPARE", "deepseek-ai/DeepSeek-V2")

class SearchMCP_Config(BaseModel):
    """Configuration settings for the dependent search MCP servers."""
    MCP_TAVILY_URL: str = os.getenv("MCP_TAVILY_URL")
    MCP_ARXIV_URL: str = os.getenv("MCP_ARXIV_URL")
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN")