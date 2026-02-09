from __future__ import annotations

import pytest
from tests.e2e.config import require_lurky_api_key


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_search_spaces_requires_payment(rest_client) -> None:
    config, client = rest_client
    response = await client.get("/hybrid/search", params={"q": "bitcoin"})
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_search_spaces_succeeds_with_x402(paid_client) -> None:
    config, client = paid_client
    api_key = require_lurky_api_key(config)
    response = await client.get(
        "/hybrid/search",
        params={"q": "bitcoin"},
        headers={"Lurky-Api-Key": api_key},
    )
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"This indicates payment flow is not working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    body = response.json()
    assert "discussions" in body
