from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiscussionSchema(BaseModel):
    id: str
    space_id: str
    title: str
    summary: str
    timestamp: Optional[int] = None
    coins: list[dict[str, Any]] = []
    categories: list[str] = []


class SpaceDetailsSchema(BaseModel):
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
    discussions: list[DiscussionSchema] = []


class SearchResponseSchema(BaseModel):
    discussions: list[DiscussionSchema]
    total: int
    page: int
    limit: int


class HealthResponse(BaseModel):
    status: str
    version: str
