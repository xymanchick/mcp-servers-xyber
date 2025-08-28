import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp_server_deepresearcher.deepresearcher.config import LLM_Config, SearchMCP_Config
from mcp_server_deepresearcher.deepresearcher.graph import DeepResearcher
from mcp_server_deepresearcher.deepresearcher.utils import (
    load_mcp_servers_config,
    setup_llm,
    setup_spare_llm,
)
from mcp_server_deepresearcher.schemas import DeepResearchRequest

logger = logging.getLogger(__name__)


# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage server startup/shutdown.
    Initializes shared resources like LLMs and MCP tools once at startup.
    """
    logger.info("Lifespan: Initializing shared resources...")

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
            mcp_arxiv_url=search_mcp_config.MCP_ARXIV_URL,
        )

        client = MultiServerMCPClient(mcp_servers_config)

        logger.info("Connecting to dependent MCPs to fetch tools...")
        mcp_tools = await client.get_tools()
        logger.info(
            f"Successfully fetched {len(mcp_tools)} tools for the agent to use."
        )

        # Yield shared resources to the server context
        yield {
            "llm": llm_with_fallbacks,
            "mcp_tools": mcp_tools,
        }

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        # Re-raise the error to prevent the server from starting in a bad state
        raise startup_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed.")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(name="deep_researcher", lifespan=app_lifespan)


# --- Tool Definitions --- #
@mcp_server.tool()
async def deep_research(
    ctx: Context, request: DeepResearchRequest
) -> str:
    """Performs deep research on a topic and returns a structured report."""
    logger.info(f"Received request for deep_research on topic: '{request.research_topic}'")

    # Retrieve shared resources from lifespan context
    lifespan_ctx = ctx.request_context.lifespan_context
    llm = lifespan_ctx.get("llm")
    mcp_tools = lifespan_ctx.get("mcp_tools")

    if not llm or not mcp_tools:
        raise ToolError(
            "Shared resources (LLM, tools) not available. The server may have failed to initialize properly."
        )

    # Create a new, stateless agent for each request
    agent = DeepResearcher(llm, tools=mcp_tools)
    logger.info("Created new stateless agent for this request.")

    try:
        config = {"configurable": {"max_web_research_loops": request.max_web_research_loops}}
        result_dict = await agent.graph.ainvoke(
            {"research_topic": request.research_topic}, config=config
        )

        final_report = json.dumps(result_dict.get("running_summary", {}), indent=2)
        logger.info("Successfully completed deep research.")
        return final_report

    except Exception as e:
        logger.error(
            f"An unexpected error occurred during deep research: {e}", exc_info=True
        )
        raise ToolError(f"An unexpected error occurred during research: {e}") from e
