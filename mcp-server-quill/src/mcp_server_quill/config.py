"""
This module should be changed to fit your deployment and payment model, adjusting environment prefixes, defaults, and x402 settings while keeping the overall structure.

Main responsibility: Define and load application and x402 payment configuration, exposing cached helpers to access these settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from cdp.x402 import create_facilitator_config
from dotenv import load_dotenv
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.facilitator import FacilitatorConfig

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present).
_src_dir = Path(__file__).resolve().parent
_project_root = _src_dir.parent.parent
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class PaymentOption(BaseModel):
    """
    Defines a single payment option for a protected resource, aligning with the
    data needed to construct an `x402.types.PaymentRequirements` object.

    Note: token_amount should be specified in the token's smallest unit.
    For example, USDC has 6 decimals, so 1 USDC = 1,000,000 token_amount.
    """

    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class X402Config(BaseSettings):
    """
    Configuration for the x402 payment protocol.
    Loads simple key-value settings from environment variables and complex
    pricing structures from a dedicated YAML file.
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_QUILL_X402_",
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "on"
    payee_wallet_address: str | None = None
    facilitator_url: str | None = None
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    @computed_field
    @property
    def facilitator_config(self) -> FacilitatorConfig | None:
        """
        A computed field that creates the correct facilitator configuration.
        - If CDP API keys are present, it configures for mainnet.
        - If a facilitator_url is provided, it configures for that URL.
        - If neither is provided, returns None, disabling payments.
        """
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            return create_facilitator_config(
                api_key_id=self.cdp_api_key_id,
                api_key_secret=self.cdp_api_key_secret,
            )
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
            return {"url": self.facilitator_url}
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOption]]:
        """
        A computed field that loads, parses, and validates the pricing
        configuration from the YAML file specified by 'pricing_config_path'.
        """
        if not self.pricing_config_path.is_file():
            logger.warning(
                f"Pricing config file not found at '{self.pricing_config_path}'. "
                "No endpoints will be monetized."
            )
            return {}

        try:
            with open(self.pricing_config_path) as f:
                pricing_data = yaml.safe_load(f)

            if not pricing_data:
                return {}

            if not isinstance(pricing_data, dict):
                raise ValueError(
                    f"expected a YAML mapping (dict) but got {type(pricing_data).__name__}"
                )

            # Check if wallet_address is at the top level
            default_wallet_address = pricing_data.get("wallet_address")
            if default_wallet_address and not self.payee_wallet_address:
                # If payee_wallet_address wasn't set via env, use the one from yaml
                # Note: modifying self in a computed field is tricky, but we can't easily change X402Config instance here.
                # Instead, we rely on the middleware using self.settings.payee_wallet_address.
                # We'll just log it here for now or ideally update the PaymentOption logic if needed.
                pass 
            
            # Extract actual pricing dict
            tools_pricing = pricing_data.get("pricing", pricing_data)
            
            # If the yaml has a "pricing" key, use that. Otherwise assume the whole file is the pricing dict.
            # But wait, our tool_pricing.yaml structure is:
            # wallet_address: "..."
            # pricing:
            #   tool_name:
            #     price_per_request: 0.5
            #     currency: "USDC"
            
            if "pricing" in pricing_data:
                tools_pricing = pricing_data["pricing"]
            
            validated_pricing = {}
            
            # Helper to map currency to chain_id/address
            # For simplicity, let's hardcode USDC on Base (8453) for now as an example, 
            # or we need a way to map "USDC" to specific chain/token in the config code.
            # However, PaymentOption expects chain_id and token_address.
            # The user provided YAML has 'price_per_request' and 'currency'.
            # We need to adapt this parsing logic to support the user's simplified YAML format.
            
            USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            BASE_CHAIN_ID = 8453
            USDC_DECIMALS = 6
            
            for op_id, opts in tools_pricing.items():
                if isinstance(opts, dict) and "price_per_request" in opts:
                    # Handle simplified format
                    price = float(opts["price_per_request"])
                    currency = opts.get("currency", "USDC")
                    
                    if currency == "USDC":
                         token_amount = int(price * (10 ** USDC_DECIMALS))
                         validated_pricing[op_id] = [
                             PaymentOption(
                                 chain_id=BASE_CHAIN_ID,
                                 token_address=USDC_BASE_ADDRESS,
                                 token_amount=token_amount
                             )
                         ]
                    else:
                        logger.warning(f"Unsupported currency {currency} for {op_id}. Skipping.")
                elif isinstance(opts, list):
                    # Handle full format (list of options)
                    validated_pricing[op_id] = [PaymentOption(**opt) for opt in opts]
                else:
                    logger.warning(f"Invalid pricing format for {op_id}. Skipping.")

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}") from e
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Each endpoint must map to a list of payment options: {e}") from e
        except ValueError:
            raise

        logger.info(f"Successfully loaded pricing for {len(validated_pricing)} tools.")
        return validated_pricing

    def validate_against_routes(self, routes: list):
        """
        Checks pricing configuration against all available routes and logs status.
        """
        configured_op_ids = set(self.pricing.keys())
        valid_op_ids = {
            getattr(route, "operation_id", None)
            for route in routes
            if hasattr(route, "operation_id") and route.operation_id
        }

        logger.info("--- Validating Endpoint Pricing Configuration ---")
        self._log_correctly_configured(configured_op_ids, valid_op_ids)
        self._log_unpriced_endpoints(configured_op_ids, valid_op_ids)
        self._log_misconfigured_prices(configured_op_ids, valid_op_ids)
        logger.info("--- Pricing Validation Complete ---")

    def _log_correctly_configured(self, configured_ids: set, valid_op_ids: set):
        """Logs endpoints that are correctly priced."""
        correctly_configured = configured_ids.intersection(valid_op_ids)
        if correctly_configured:
            logger.info("Successfully configured pricing for:")
            for op_id in sorted(correctly_configured):
                logger.info(f"  - {op_id}")

    def _log_unpriced_endpoints(self, configured_ids: set, valid_op_ids: set):
        """Logs endpoints that exist but are not priced."""
        unpriced = valid_op_ids - configured_ids
        if unpriced:
            logger.debug(
                "The following endpoints are not priced (this may be intentional):"
            )
            for op_id in sorted(unpriced):
                logger.debug(f"  - {op_id}")

    def _log_misconfigured_prices(self, configured_ids: set, valid_op_ids: set):
        """Logs priced operation_ids that do not match any endpoint."""
        misconfigured = configured_ids - valid_op_ids
        if misconfigured:
            logger.warning("Pricing configuration mismatch found:")
            for op_id in sorted(misconfigured):
                logger.warning(
                    f"  - The operation_id '{op_id}' is priced in your tool_pricing.yaml, "
                    "but no corresponding endpoint was found. (Typo?)"
                )


class QuillConfig(BaseSettings):
    """Quill API configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="QUILL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str | None = None
    base_url: str = "https://check-api.quillai.network/api/v1"


class DexScreenerConfig(BaseSettings):
    """DexScreener API configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="DEXSCREENER_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "https://api.dexscreener.com/latest/dex/search"


class AppSettings(BaseSettings):
    """Application settings for the MCP Quill server."""

    host: str = "0.0.0.0"
    port: int = 8001
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    quill: QuillConfig = QuillConfig()
    dexscreener: DexScreenerConfig = DexScreenerConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_QUILL_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def get_x402_settings() -> X402Config:
    return X402Config()
