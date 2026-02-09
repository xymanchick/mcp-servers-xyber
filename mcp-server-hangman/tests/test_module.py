"""Test cases for HangmanService module."""

import pytest
from mcp_server_hangman.hangman.module import (GameNotFoundError,
                                               HangmanService,
                                               InvalidGuessError)


class TestHangmanService:
    def setup_method(self):
        self.service = HangmanService()
        self.player_id = "player-1"

    def test_start_game_initial_state(self):
        state = self.service.start_game(
            player_id=self.player_id, secret_word="Banana", max_attempts=6
        )
        assert state.player_id == self.player_id
        assert state.masked_chars == list("______")
        assert state.remaining_attempts == 6
        assert state.correct_letters == []
        assert state.incorrect_letters == []
        assert state.won is False

    def test_start_game_rejects_non_letters(self):
        with pytest.raises(Exception):
            self.service.start_game(
                player_id=self.player_id, secret_word="Ice-Cream!", max_attempts=5
            )
        with pytest.raises(Exception):
            self.service.start_game(
                player_id=self.player_id, secret_word="abc123", max_attempts=5
            )

    def test_guess_correct_letter_case_insensitive(self):
        self.service.start_game(self.player_id, secret_word="Kiwi", max_attempts=5)
        state = self.service.guess_letter(self.player_id, "i")
        # Reveal both i's preserving original case
        assert "i" in "".join(state.masked_chars).lower()
        assert state.remaining_attempts == 5
        assert "I" in state.correct_letters

    def test_guess_incorrect_letter_consumes_attempt(self):
        self.service.start_game(self.player_id, secret_word="Apple", max_attempts=3)
        state = self.service.guess_letter(self.player_id, "z")
        assert state.remaining_attempts == 2
        assert "Z" in state.incorrect_letters

    def test_repeated_guess_no_penalty(self):
        self.service.start_game(self.player_id, secret_word="Pear", max_attempts=3)
        self.service.guess_letter(self.player_id, "p")
        state = self.service.guess_letter(self.player_id, "p")
        assert state.remaining_attempts == 3
        assert state.correct_letters.count("P") == 1

    def test_win_condition(self):
        self.service.start_game(self.player_id, secret_word="Go", max_attempts=2)
        self.service.guess_letter(self.player_id, "g")
        state = self.service.guess_letter(self.player_id, "o")
        assert state.won is True
        assert "".join(state.masked_chars).lower() == "go"

    def test_guess_after_win_terminated(self):
        self.service.start_game(self.player_id, secret_word="Up", max_attempts=2)
        self.service.guess_letter(self.player_id, "u")
        self.service.guess_letter(self.player_id, "p")
        with pytest.raises(GameNotFoundError):
            self.service.guess_letter(self.player_id, "x")

    def test_loss_condition_and_no_negative_attempts(self):
        self.service.start_game(self.player_id, secret_word="No", max_attempts=1)
        self.service.guess_letter(self.player_id, "x")  # now 0 attempts
        # Game should be terminated after attempts hit 0
        with pytest.raises(GameNotFoundError):
            self.service.guess_letter(self.player_id, "y")

    def test_invalid_guess_non_alpha(self):
        self.service.start_game(self.player_id, secret_word="Test", max_attempts=2)
        with pytest.raises(InvalidGuessError):
            self.service.guess_letter(self.player_id, "1")

    def test_invalid_guess_length(self):
        self.service.start_game(self.player_id, secret_word="Test", max_attempts=2)
        with pytest.raises(InvalidGuessError):
            self.service.guess_letter(self.player_id, "ab")

    def test_guess_without_game(self):
        with pytest.raises(GameNotFoundError):
            self.service.guess_letter(self.player_id, "a")

    def test_win_scenario(self):
        self.service.start_game(self.player_id, secret_word="Go", max_attempts=2)
        state = self.service.guess_letter(self.player_id, "g")
        assert "".join(state.masked_chars).lower() == "g_" and state.won is False
        state = self.service.guess_letter(self.player_id, "o")
        assert state.won is True
        # After win, subsequent guesses should raise as game is terminated
        with pytest.raises(GameNotFoundError):
            self.service.guess_letter(self.player_id, "x")
