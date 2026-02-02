from __future__ import annotations

import httpx
import pytest_asyncio
from eth_account import Account
from x402.client import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm.exact import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


@pytest_asyncio.fixture
async def rest_client():
    """Fixture providing a standard HTTP client for e2e tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def paid_client():
    """Fixture providing an x402-enabled HTTP client for paid e2e tests.

    Uses x402HttpxClient which automatically handles 402 responses and
    payment signing for EVM networks.
    """
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)

    # Create eth account from private key
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    signer = EthAccountSigner(account)

    # Create x402 client and register EVM scheme
    x402_client = x402Client()
    register_exact_evm_client(x402_client, signer)

    # Create x402HttpxClient which handles payments automatically
    async with x402HttpxClient(
        x402_client,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        yield config, client
