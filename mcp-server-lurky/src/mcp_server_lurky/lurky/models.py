from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Discussion(BaseModel):
    id: str
    space_id: str
    title: str
    summary: str
    timestamp: Optional[int] = None
    coins: list[Dict[str, Any]] = []
    categories: list[str] = []


class SpaceDetails(BaseModel):
    id: str
    creator_id: Optional[str] = None
    creator_handle: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    minimized_summary: Optional[str] = None
    state: Optional[str] = None
    language: Optional[str] = None
    overall_sentiment: Optional[str] = None
    participant_count: int = 0
    subscriber_count: int = 0
    likes: int = 0
    categories: list[str] = []
    created_at: Optional[int] = None
    started_at: Optional[int] = None
    scheduled_at: Optional[int] = None
    ended_at: Optional[int] = None
    analyzed_at: Optional[int] = None
    discussions: list[Discussion] = []


class MindMapNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    title: str
    summary: Optional[str] = None


class MindMap(BaseModel):
    nodes: list[MindMapNode]


class SearchResponse(BaseModel):
    discussions: list[Discussion]
    total: int
    page: int
    limit: int
