"""
Configuration module for the MCP Lurky server.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from cdp.x402 import create_facilitator_config
from dotenv import load_dotenv
from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.facilitator import FacilitatorConfig

logger = logging.getLogger(__name__)

# Load environment variables from the repo-root .env file (if present).
_project_root = Path(__file__).resolve().parents[2]
_env_file = _project_root / ".env"
load_dotenv(dotenv_path=_env_file)


class LurkyConfig(BaseModel):
    """Lurky API configuration."""

    api_key: str | None = os.getenv("LURKY_API_KEY") or os.getenv(
        "MCP_LURKY__LURKY__API_KEY"
    )
    base_url: str = os.getenv("LURKY_BASE_URL") or os.getenv(
        "MCP_LURKY__LURKY__BASE_URL", "https://api.lurky.app"
    )


class DatabaseConfig(BaseModel):
    """Database configuration for Postgres cache."""

    DB_NAME: str = os.getenv("DB_NAME", "lurky_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT_RAW: str = os.getenv("DB_PORT", "5432")
    
    @property
    def DB_PORT(self) -> str:
        return self.DB_PORT_RAW.split(":")[0] if ":" in self.DB_PORT_RAW else self.DB_PORT_RAW

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cache TTL defaults (in seconds)
    cache_ttl_search: int = int(os.getenv("CACHE_TTL_SEARCH", "3600"))  # 1 hour
    cache_ttl_details: int = int(os.getenv("CACHE_TTL_DETAILS", "86400"))  # 24 hours


class PaymentOption(BaseModel):
    """
    Defines a single payment option for a protected resource.
    """

    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class X402Config(BaseSettings):
    """
    Configuration for the x402 payment protocol.
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_LURKY_X402_",
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
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            return create_facilitator_config(
                api_key_id=self.cdp_api_key_id,
                api_key_secret=self.cdp_api_key_secret,
            )
        if self.facilitator_url:
            return {"url": self.facilitator_url}
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOption]]:
        if not self.pricing_config_path.is_file():
            return {}

        try:
            with open(self.pricing_config_path) as f:
                pricing_data = yaml.safe_load(f)
                if not pricing_data:
                    return {}
                return {
                    op_id: [PaymentOption(**opt) for opt in opts]
                    for op_id, opts in pricing_data.items()
                }
        except Exception as e:
            logger.error(f"Failed to parse pricing config: {e}")
            return {}

    def validate_against_routes(self, routes: list):
        configured_op_ids = set(self.pricing.keys())
        valid_op_ids = {
            getattr(route, "operation_id", None)
            for route in routes
            if hasattr(route, "operation_id") and route.operation_id
        }
        logger.info(f"Priced: {configured_op_ids}, Routes: {valid_op_ids}")


class AppSettings(BaseSettings):
    """Application settings for the MCP Lurky server."""

    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hot_reload: bool = False

    lurky: LurkyConfig = LurkyConfig()
    database: DatabaseConfig = DatabaseConfig()

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_prefix="MCP_LURKY_",
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
