from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Custom Error Classes --- #


class AaveError(Exception):
    """Base class for AAVE-related errors."""

    pass


class AaveApiError(AaveError):
    """Raised when AAVE API returns an error."""

    pass


class AaveConfigError(AaveError):
    """Raised when there's an issue with configuration."""

    pass


class AaveClientError(AaveError):
    """Raised when there's an issue with the AAVE client."""

    pass


class AaveContractError(AaveError):
    """Raised when there's an issue with smart contract interactions."""

    pass


# --- Configuration Model --- #


class AaveConfig(BaseSettings):
    """
    Configuration for the AAVE DeFi protocol service.

    Attributes:
        rpc_url: Ethereum RPC URL for blockchain interactions
        api_base_url: AAVE API base URL
        timeout_seconds: Timeout for API requests in seconds
        enable_caching: Whether to enable caching of responses
        cache_ttl_seconds: Cache time-to-live in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    """

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_prefix="AAVE_",  # Look for env vars like AAVE_RPC_URL
        env_file=".env",  # Load from .env file if it exists
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from the environment
        case_sensitive=False,  # Environment variables are case-insensitive
    )

    # Blockchain configuration
    rpc_url: str = "https://eth-mainnet.g.alchemy.com/v2/your-api-key"

    # API configuration
    api_base_url: str = "https://api.v3.aave.com/graphql"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # Caching configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes

    # Contract addresses (will be loaded from AAVE API)
    pool_addresses_provider: str = (
        "0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5"  # Ethereum V3
    )

    # Gas estimation
    gas_limit_multiplier: float = 1.2
    max_gas_price_gwei: int = 100

    # Risk parameters
    max_slippage_percent: float = 0.5
    min_health_factor: float = 1.1


@lru_cache(maxsize=1)
def get_aave_config() -> AaveConfig:
    """
    Get a cached instance of AaveConfig.

    Returns:
        Validated AaveConfig instance

    Raises:
        AaveConfigError: If configuration validation fails

    """
    try:
        config = AaveConfig()
        return config
    except Exception as e:
        raise AaveConfigError(f"Failed to load AAVE configuration: {e}") from e
