import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_hangman.dependencies import get_hangman_service
from mcp_server_hangman.hangman.models import GameState
from mcp_server_hangman.hangman.module import (
    GameNotFoundError,
    HangmanError,
    HangmanService,
    InvalidGuessError,
)
from mcp_server_hangman.schemas import GuessLetterRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/guess-letter",
    tags=["Hangman"],
    operation_id="hangman_guess_letter",
    response_model=GameState,
)
async def guess_letter(
    request: GuessLetterRequest,
    service: HangmanService = Depends(get_hangman_service),
) -> GameState:
    """
    Submit a single-letter guess and return the updated state.

    Requires the player_id returned from start_game.

    Returns updated GameState showing:
    - Current state of the masked word
    - Remaining attempts
    - Lists of correct and incorrect guesses
    - Whether the game has been won

    If the game is already completed (won or lost), returns a 404 error
    indicating the player needs to start a new game.
    """
    try:
        return service.guess_letter(player_id=request.player_id, letter=request.letter)
    except GameNotFoundError as e:
        logger.warning("Game not found for player %s: %s", request.player_id, e)
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidGuessError as e:
        logger.warning("Invalid guess from player %s: %s", request.player_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except HangmanError as e:
        logger.warning("Guess error for player %s: %s", request.player_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during guess: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during guess")
