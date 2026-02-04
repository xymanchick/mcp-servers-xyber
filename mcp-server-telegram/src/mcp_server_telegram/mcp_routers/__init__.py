"""
This module collects MCP-only FastAPI routers into a single list for inclusion in the MCP source application.

Main responsibility: Aggregate all MCP tool routers for the Telegram server.
"""

from fastapi import APIRouter

from .post_to_telegram import router as post_to_telegram_router

routers: list[APIRouter] = [
    post_to_telegram_router,
]
