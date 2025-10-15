import asyncio
import base64
import logging
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from rich.logging import RichHandler

# --- Basic logging setup --- #
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("mcp-client")


async def main() -> None:
    """Main function to run the client."""
    client = MultiServerMCPClient(
        {
            # This should match the service name in your docker-compose.yml
            "mcp_server_together_imgen": {
                "url": "http://localhost:8016/mcp",
                "transport": "streamable_http",
            }
        }
    )
    output_dir = Path("generated_images")
    output_dir.mkdir(exist_ok=True)

    try:
        tools = await client.get_tools()
    except Exception as e:
        logger.error(f"Failed to connect to the server or get tools: {e}")
        logger.error(
            "Please ensure the mcp-server-together-imgen is running and accessible at http://localhost:8016"
        )
        return

    if not tools:
        logger.error("No tools found on the server.")
        return

    generate_image_tool = next(
        (tool for tool in tools if tool.name == "generate_image"), None
    )

    if not generate_image_tool:
        logger.error("`generate_image` tool not found.")
        return

    logger.info(f"Found tool: {generate_image_tool.name}")

    # --- Test 1: without lora and refinement ---
    logger.info("Running test 1: without lora and refinement")
    request_1 = {
        "prompt": "a minimal abstract geometric icon",
        "width": 128,
        "height": 128,
        "seed": 12345,
        "lora_scale": 0.0,
        "refine_prompt": False,
    }
    try:
        response_1 = await generate_image_tool.ainvoke(input=request_1)
        image_data_1 = base64.b64decode(response_1)
        image_path_1 = output_dir / "test_1_no_lora.png"
        with open(image_path_1, "wb") as f:
            f.write(image_data_1)
        logger.info(f"Image for test 1 saved to {image_path_1}")
    except Exception as e:
        logger.error(f"Error in test 1: {e}", exc_info=True)

    # --- Test 2: with lora and refinement ---
    logger.info("Running test 2: with lora and refinement")
    request_2 = {
        "prompt": "a minimal abstract geometric icon",
        "width": 128,
        "height": 128,
        "seed": 12345,
        "lora_scale": 0.8,
        "refine_prompt": True,
    }
    try:
        response_2 = await generate_image_tool.ainvoke(input=request_2)
        image_data_2 = base64.b64decode(response_2)
        image_path_2 = output_dir / "test_2_with_lora.png"
        with open(image_path_2, "wb") as f:
            f.write(image_data_2)
        logger.info(f"Image for test 2 saved to {image_path_2}")
    except Exception as e:
        logger.error(f"Error in test 2: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user.")
