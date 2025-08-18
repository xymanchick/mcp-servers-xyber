from __future__ import annotations

from pydantic import BaseModel, Field


class GameState(BaseModel):
    player_id: str = Field(..., description="Identifier for the current player/session")
    masked_chars: list[str] = Field(
        ...,
        description="Secret word rendered as list of characters with unrevealed letters as '_'",
    )
    remaining_attempts: int = Field(
        ..., ge=0, description="Attempts left before losing"
    )
    correct_letters: list[str] = Field(
        default_factory=list, description="Correctly guessed letters"
    )
    incorrect_letters: list[str] = Field(
        default_factory=list, description="Incorrectly guessed letters"
    )
    won: bool = Field(False, description="True if the word has been fully revealed")
