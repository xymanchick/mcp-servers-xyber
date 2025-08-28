from pydantic import BaseModel, Field


class TavilySearchRequest(BaseModel):
    """Input schema for Tavily search tool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="The search query string for Tavily",
    )
    max_results: int | None = Field(
        None,
        ge=1,
        le=50,
        description="Optional override for the maximum number of search results (min 1, max 50)",
    )
