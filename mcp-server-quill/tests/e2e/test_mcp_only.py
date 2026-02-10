from __future__ import annotations

import pytest

from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_mcp_search_token_address_tool() -> None:
    """Test search_token_address MCP tool - searches for token address by name/symbol."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="search_token_address",
        arguments={"query": "WETH", "chain": "ethereum"},
    )
    # This tool is priced; expect 402 until payment flow is wired for MCP tools.
    assert response.status_code == 402


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_mcp_get_evm_token_info_tool_requires_payment() -> None:
    """Test get_evm_token_info MCP tool - requires payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_evm_token_info",
        arguments={"query": "WETH", "quill_chain_id": "1"},
    )
    # Currently priced; we expect 402 until payment flow is wired for MCP tools.
    assert response.status_code == 402
