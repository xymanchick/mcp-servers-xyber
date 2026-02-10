from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Discussion(BaseModel):
    id: str
    space_id: str
    title: str
    summary: str
    timestamp: int | None = None
    coins: list[dict[str, Any]] = []
    categories: list[str] = []


class SpaceDetails(BaseModel):
    id: str
    creator_id: str | None = None
    creator_handle: str | None = None
    title: str | None = None
    summary: str | None = None
    minimized_summary: str | None = None
    state: str | None = None
    language: str | None = None
    overall_sentiment: str | None = None
    participant_count: int = 0
    subscriber_count: int = 0
    likes: int = 0
    categories: list[str] = []
    created_at: int | None = None
    started_at: int | None = None
    scheduled_at: int | None = None
    ended_at: int | None = None
    analyzed_at: int | None = None
    discussions: list[Discussion] = []


class MindMapNode(BaseModel):
    id: str
    parent_id: str | None = None
    title: str
    summary: str | None = None


class MindMap(BaseModel):
    nodes: list[MindMapNode]


class SearchResponse(BaseModel):
    discussions: list[Discussion]
    total: int
    page: int
    limit: int
