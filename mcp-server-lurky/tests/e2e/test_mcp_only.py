from __future__ import annotations

import pytest
from tests.e2e.config import (load_e2e_config, require_base_url,
                              require_lurky_api_key)
from tests.e2e.utils import (call_mcp_tool, initialize_mcp_session,
                             negotiate_mcp_session_id)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_mcp_search_spaces_requires_payment() -> None:
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="lurky_search_spaces",
        arguments={"q": "bitcoin"},
    )
    # Currently priced; we expect 402 until payment flow is wired for MCP tools.
    assert response.status_code == 402
