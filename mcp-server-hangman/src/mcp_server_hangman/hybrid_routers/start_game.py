import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from mcp_server_hangman.dependencies import get_hangman_service
from mcp_server_hangman.hangman.models import GameState
from mcp_server_hangman.hangman.module import HangmanError, HangmanService
from mcp_server_hangman.schemas import StartGameRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/start-game",
    tags=["Hangman"],
    operation_id="hangman_start_game",
    response_model=GameState,
)
async def start_game(
    request: StartGameRequest,
    service: HangmanService = Depends(get_hangman_service),
) -> GameState:
    """
    Start or reset a Hangman game and return a new player_id for subsequent guesses.

    Returns a GameState with:
    - player_id: Unique identifier for this game session
    - masked_chars: The secret word with unrevealed letters shown as '_'
    - remaining_attempts: Number of attempts left before losing
    - correct_letters: List of correctly guessed letters
    - incorrect_letters: List of incorrectly guessed letters
    - won: Whether the word has been fully revealed
    """
    player_id = uuid.uuid4().hex
    try:
        return service.start_game(
            player_id=player_id,
            secret_word=request.secret_word,
            max_attempts=request.max_attempts,
        )
    except HangmanError as e:
        logger.error("Failed to start game: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error starting game: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error starting game")
