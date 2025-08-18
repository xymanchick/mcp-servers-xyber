from pydantic import BaseModel, Field


class GetCharacterByNameRequest(BaseModel):
    """Input schema for the get_character_by_name tool."""

    name: str = Field(
        ..., 
        min_length=1,
        description="The unique name of the character to retrieve."
    )
