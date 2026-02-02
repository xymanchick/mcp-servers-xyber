"""
Main responsibility: Collect MCP-only FastAPI routers into a single list for inclusion in the MCP source application.
"""

from fastapi import APIRouter

# MCP-only routers (currently empty - all endpoints are exposed via hybrid_routers)
routers: list[APIRouter] = []
