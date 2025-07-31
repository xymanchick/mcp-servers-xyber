import logging
import json
from typing import AsyncIterator, Dict, Any
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_server_deepresearcher.deepresearcher.graph import DeepResearcher
from mcp_server_deepresearcher.deepresearcher.utils import (
    setup_llm, 
    setup_spare_llm, 
    load_mcp_servers_config
)
from mcp_server_deepresearcher.deepresearcher.config import SearchMCP_Config, LLM_Config

logger = logging.getLogger(__name__)

# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup/shutdown. Initializes the Deep Researcher agent."""
    logger.info("Lifespan: Initializing Deep Researcher agent...")
    
    agent = None  # Initialize agent as None
    try:
        # Load configurations
        llm_config = LLM_Config()
        search_mcp_config = SearchMCP_Config()

        # Initialize LLMs
        llm = setup_llm(llm_config)
        llm_spare = setup_spare_llm(llm_config)
        llm_with_fallbacks = llm.with_fallbacks([llm_spare])
        logger.info("LLMs initialized successfully.")

        # Initialize MCP client to fetch tools for the agent
        mcp_servers_config = load_mcp_servers_config(
            apify_token=search_mcp_config.APIFY_TOKEN,
            mcp_tavily_url=search_mcp_config.MCP_TAVILY_URL,
            mcp_arxiv_url=search_mcp_config.MCP_ARXIV_URL
        )
        
        # --- FIX: REMOVED THE 'async with' CONTEXT MANAGER ---
        # The library was updated and this is no longer supported.
        # We now create the client and use it directly as the error message suggests.
        
        client = MultiServerMCPClient(mcp_servers_config)
        
        logger.info("Connecting to dependent MCPs to fetch tools...")
        mcp_tools = await client.get_tools()
        logger.info(f"Successfully fetched {len(mcp_tools)} tools for the agent to use.")

        # Instantiate the DeepResearcher agent
        agent = DeepResearcher(llm_with_fallbacks, tools=mcp_tools)
        logger.info("Deep Researcher agent initialized successfully.")

        # --- END OF FIX ---

        # Yield the agent to the server context
        yield {"deep_researcher_agent": agent}

    except Exception as startup_err:
        logger.error(f"FATAL: Unexpected error during lifespan initialization: {startup_err}", exc_info=True)
        # Re-raise the error to prevent the server from starting in a bad state
        raise startup_err
    
    finally:
        logger.info("Lifespan: Shutdown cleanup completed.")

# --- MCP Server Initialization --- #
mcp_server = FastMCP(
    name="deep_researcher",
    lifespan=app_lifespan
)

# --- Tool Definitions --- #
@mcp_server.tool()
async def deep_research(
    ctx: Context,
    research_topic: str,
    max_web_research_loops: int = 3
) -> str:
    """Performs deep research on a topic and returns a structured report."""
    logger.info(f"Received request for deep_research on topic: '{research_topic}'")
    agent = ctx.request_context.lifespan_context.get("deep_researcher_agent")

    if not agent:
        raise ToolError("Deep Researcher agent is not available. The server may have failed to initialize properly.")

    try:
        config = {"configurable": {"max_web_research_loops": max_web_research_loops}}
        result_dict = await agent.graph.ainvoke({"research_topic": research_topic}, config=config)
        
        final_report = json.dumps(result_dict.get('running_summary', {}), indent=2)
        logger.info("Successfully completed deep research.")
        return final_report

    except Exception as e:
        logger.error(f"An unexpected error occurred during deep research: {e}", exc_info=True)
        raise ToolError(f"An unexpected error occurred during research: {e}") from e