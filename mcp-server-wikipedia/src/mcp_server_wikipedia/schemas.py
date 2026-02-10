from typing import Any

from pydantic import BaseModel, Field


class SearchWikipediaRequest(BaseModel):
    """Input schema for searching Wikipedia articles by query."""

    query: str = Field(
        ..., max_length=300, description="Search query string for Wikipedia articles"
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of search results to return (1-50)",
    )


class GetArticleRequest(BaseModel):
    """Input schema for retrieving a Wikipedia article by its exact title."""

    title: str = Field(
        ..., description="Exact title of the Wikipedia article to retrieve"
    )


class ArticleResponse(BaseModel):
    """Output schema representing a Wikipedia article with content and metadata."""

    title: str = Field(..., description="Title of the Wikipedia article")
    content: str = Field(..., description="Full content of the Wikipedia article")
    metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata about the article"
    )


class GetSummaryRequest(BaseModel):
    """Input schema for retrieving the summary of a Wikipedia article."""

    title: str = Field(..., description="Title of the Wikipedia article to summarize")


class GetSectionsRequest(BaseModel):
    """Input schema for retrieving section titles of a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get section titles from"
    )


class GetLinksRequest(BaseModel):
    """Input schema for retrieving links within a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get links from"
    )


class GetRelatedTopicsRequest(BaseModel):
    """Input schema for retrieving topics related to a Wikipedia article."""

    title: str = Field(
        ..., description="Title of the Wikipedia article to get related topics for"
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of related topics to return",
    )


class RelatedTopicsResponse(BaseModel):
    """Output schema listing topics related to a Wikipedia article."""

    topics: list[str] = Field(..., description="List of related topic titles")
