from pydantic import BaseModel, Field


class DeepResearchRequest(BaseModel):
    """Input schema for the deep_research tool."""

    research_topic: str = Field(..., description="The research topic to investigate")
    max_web_research_loops: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of web research loops to perform (1-10)"
    )
