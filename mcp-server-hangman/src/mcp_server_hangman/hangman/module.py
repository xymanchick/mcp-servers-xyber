from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

from mcp_server_hangman.hangman.models import GameState

logger = logging.getLogger(__name__)


class HangmanError(Exception):
    """Base class for hangman errors."""


class GameNotFoundError(HangmanError):
    """Raised when a game for a given player is not found."""


class InvalidGuessError(HangmanError):
    """Raised when a guess is invalid (e.g., not a single alphabetic character)."""


@dataclass
class _HangmanGame:
    secret_word: str
    max_attempts: int
    guessed_letters: set[str] = field(default_factory=set)
    incorrect_letters: set[str] = field(default_factory=set)

    @property
    def remaining_attempts(self) -> int:
        return self.max_attempts - len(self.incorrect_letters)

    def is_won(self) -> bool:
        normalized_secret = self.secret_word.upper()
        return all(
            (c.upper() in self.guessed_letters) if c.isalpha() else True
            for c in normalized_secret
        )

    def is_lost(self) -> bool:
        return self.remaining_attempts <= 0 and not self.is_won()

    def masked_chars(self) -> list[str]:
        # Reveal letters and keep non-letters as-is
        chars: list[str] = []
        for c in self.secret_word:
            if c.isalpha():
                chars.append(c if c.upper() in self.guessed_letters else "_")
            else:
                chars.append(c)
        return chars


class HangmanService:
    def __init__(self) -> None:
        self._games: dict[str, _HangmanGame] = {}

    def start_game(
        self, player_id: str, secret_word: str, max_attempts: int = 6
    ) -> GameState:
        if not secret_word or not isinstance(secret_word, str):
            raise HangmanError("Secret word must be a non-empty string")
        if not all(c.isalpha() for c in secret_word):
            raise HangmanError("Secret word must contain letters only")
        if max_attempts <= 0:
            raise HangmanError("max_attempts must be positive")

        game = _HangmanGame(secret_word=secret_word, max_attempts=max_attempts)
        self._games[player_id] = game
        logger.info(
            "New game started for player %s with length %d and %d attempts",
            player_id,
            len(secret_word),
            max_attempts,
        )
        return self._to_state(player_id, game)

    def guess_letter(self, player_id: str, letter: str) -> GameState:
        game = self._games.get(player_id)
        if not game:
            raise GameNotFoundError(
                "No active game for this player. Start a new game first."
            )

        # If game is already over by attempts, consider it terminated
        if game.remaining_attempts <= 0 or game.is_won():
            # Ensure cleanup
            self._games.pop(player_id, None)
            raise GameNotFoundError(
                "No active game for this player. Start a new game first."
            )

        if not isinstance(letter, str) or len(letter) != 1 or not letter.isalpha():
            raise InvalidGuessError("Letter must be a single alphabetic character")

        normalized = letter.upper()

        # If already guessed, do not penalize further
        if normalized in game.guessed_letters or normalized in game.incorrect_letters:
            logger.debug("Player %s repeated guess '%s'", player_id, normalized)
            return self._to_state(player_id, game)

        if normalized in (c.upper() for c in game.secret_word if c.isalpha()):
            game.guessed_letters.add(normalized)
        else:
            # Only record incorrect guess if attempts remain
            if game.remaining_attempts > 0:
                game.incorrect_letters.add(normalized)

        state = self._to_state(player_id, game)

        # If attempts are exhausted and not won, terminate the game (invalidate player_id)
        if state.remaining_attempts == 0 and not state.won:
            self._games.pop(player_id, None)
        return state

    def _to_state(self, player_id: str, game: _HangmanGame) -> GameState:
        state = GameState(
            player_id=player_id,
            masked_chars=game.masked_chars(),
            remaining_attempts=game.remaining_attempts,
            correct_letters=sorted(list(game.guessed_letters)),
            incorrect_letters=sorted(list(game.incorrect_letters)),
            won=game.is_won(),
        )
        return state


@lru_cache(maxsize=1)
def get_hangman_service() -> HangmanService:
    return HangmanService()
