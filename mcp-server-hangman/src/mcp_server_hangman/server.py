from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp_server_hangman.hangman.models import GameState
from mcp_server_hangman.hangman.module import (
    GameNotFoundError,
    HangmanError,
    HangmanService,
    InvalidGuessError,
    get_hangman_service,
)
from mcp_server_hangman.schemas import StartGameRequest, GuessLetterRequest

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    logger.info("Lifespan: Initializing Hangman service...")
    service: HangmanService = get_hangman_service()
    yield {"hangman_service": service}
    logger.info("Lifespan: Shutdown cleanup completed")


mcp_server = FastMCP(name="hangman", lifespan=app_lifespan)


@mcp_server.tool()
async def start_game(
    ctx: Context,
    request: StartGameRequest,
) -> GameState:
    """Start or reset a Hangman game and return a new player_id for subsequent guesses."""
    # Generate a unique player/session id
    player_id = uuid.uuid4().hex
    try:
        service: HangmanService = ctx.request_context.lifespan_context[
            "hangman_service"
        ]
        return service.start_game(
            player_id=player_id, secret_word=request.secret_word, max_attempts=request.max_attempts
        )
    except HangmanError as e:
        logger.error("Failed to start game: %s", e)
        raise ToolError(str(e)) from e
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Unexpected error starting game: %s", e, exc_info=True)
        raise ToolError("Unexpected error starting game") from e


@mcp_server.tool()
async def guess_letter(
    ctx: Context,
    request: GuessLetterRequest,
) -> GameState:
    """Submit a single-letter guess and return the updated state. Requires the player_id returned from start_game."""
    try:
        service: HangmanService = ctx.request_context.lifespan_context[
            "hangman_service"
        ]
        return service.guess_letter(player_id=request.player_id, letter=request.letter)
    except (GameNotFoundError, InvalidGuessError, HangmanError) as e:
        logger.warning("Guess error for player %s: %s", request.player_id, e)
        raise ToolError(str(e)) from e
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Unexpected error during guess: %s", e, exc_info=True)
        raise ToolError("Unexpected error during guess") from e
