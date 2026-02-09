from pydantic import BaseModel, Field


class StartGameRequest(BaseModel):
    """Input schema for starting a new hangman game."""

    secret_word: str = Field(description="Secret word to guess (letters only)")
    max_attempts: int = Field(
        ge=1, default=6, description="Maximum wrong attempts allowed"
    )


class GuessLetterRequest(BaseModel):
    """Input schema for making a letter guess."""

    player_id: str = Field(description="Player/session id returned by start_game")
    letter: str = Field(description="A single alphabetic character")
