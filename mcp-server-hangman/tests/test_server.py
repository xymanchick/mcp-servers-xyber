"""Test cases for hangman MCP server tools."""

from unittest.mock import MagicMock

import pytest
from fastmcp import Context
from fastmcp.exceptions import ToolError
from mcp_server_hangman.hangman.module import HangmanService
from mcp_server_hangman.server import mcp_server


def _tool(name: str):
    return mcp_server._tool_manager._tools[name].fn


@pytest.fixture
def mock_context() -> Context:
    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = {"hangman_service": HangmanService()}
    return ctx


@pytest.mark.asyncio
async def test_start_and_guess_happy_path(mock_context):
    start = _tool("start_game")
    guess = _tool("guess_letter")

    # Start
    state = await start(ctx=mock_context, secret_word="Go", max_attempts=3)
    assert state.player_id
    assert state.masked_chars == list("__")
    assert state.remaining_attempts == 3

    # Guess correctly and win
    state = await guess(ctx=mock_context, player_id=state.player_id, letter="g")
    assert "".join(state.masked_chars).lower() == "g_"
    state = await guess(ctx=mock_context, player_id=state.player_id, letter="o")
    assert state.won is True
    assert "".join(state.masked_chars).lower() == "go"


@pytest.mark.asyncio
async def test_guess_invalid_then_repeat_no_penalty(mock_context):
    start = _tool("start_game")
    guess = _tool("guess_letter")

    state = await start(ctx=mock_context, secret_word="Hi", max_attempts=2)
    pid = state.player_id

    # Invalid guess -> ToolError
    with pytest.raises(ToolError):
        await guess(ctx=mock_context, player_id=pid, letter="12")

    # Incorrect then repeat
    state = await guess(ctx=mock_context, player_id=pid, letter="x")
    assert state.remaining_attempts == 1
    state = await guess(ctx=mock_context, player_id=pid, letter="x")
    assert state.remaining_attempts == 1


@pytest.mark.asyncio
async def test_start_game_rejects_non_letters_toolerror(mock_context):
    start = _tool("start_game")
    with pytest.raises(ToolError):
        await start(ctx=mock_context, secret_word="Abc123", max_attempts=6)
    with pytest.raises(ToolError):
        await start(ctx=mock_context, secret_word="Ice-Cream!", max_attempts=6)


@pytest.mark.asyncio
async def test_loose_game_sequence(mock_context):
    start = _tool("start_game")
    guess = _tool("guess_letter")

    state = await start(ctx=mock_context, secret_word="No", max_attempts=2)
    pid = state.player_id
    # Wrong twice -> attempts 0, not won; game becomes invalid
    state = await guess(ctx=mock_context, player_id=pid, letter="x")
    assert state.remaining_attempts == 1 and state.won is False
    state = await guess(ctx=mock_context, player_id=pid, letter="y")
    assert state.remaining_attempts == 0 and state.won is False
    # Further guesses should now raise ToolError due to invalidated game
    with pytest.raises(ToolError):
        await guess(ctx=mock_context, player_id=pid, letter="z")


@pytest.mark.asyncio
async def test_win_scenario_server(mock_context):
    start = _tool("start_game")
    guess = _tool("guess_letter")

    state = await start(ctx=mock_context, secret_word="Go", max_attempts=3)
    pid = state.player_id
    state = await guess(ctx=mock_context, player_id=pid, letter="g")
    assert "".join(state.masked_chars).lower() == "g_" and state.won is False
    state = await guess(ctx=mock_context, player_id=pid, letter="o")
    assert state.won is True
    # After win, guesses should error (game terminated)
    with pytest.raises(ToolError):
        await guess(ctx=mock_context, player_id=pid, letter="x")


@pytest.mark.asyncio
async def test_start_game_invalid_secret_raises_toolerror(mock_context):
    start = _tool("start_game")
    with pytest.raises(ToolError):
        await start(ctx=mock_context, secret_word="", max_attempts=3)


@pytest.mark.asyncio
async def test_guess_without_game_toolerror(mock_context):
    guess = _tool("guess_letter")
    with pytest.raises(ToolError):
        await guess(ctx=mock_context, player_id="nonexistent", letter="a")
