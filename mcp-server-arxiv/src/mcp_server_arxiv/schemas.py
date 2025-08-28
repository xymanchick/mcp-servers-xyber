from pydantic import BaseModel, Field


class ArxivSearchRequest(BaseModel):
    """Input schema for the arxiv_search tool."""
    
    query: str = Field(
        ..., max_length=512, description="The search query string for ArXiv"
    )
    max_results: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Optional override for the maximum number of results to fetch and process (1-50)",
    )
    max_text_length: int | None = Field(
        default=None,
        ge=100,
        description="Optional max characters of full text per paper (minimum 100 characters)",
    )
