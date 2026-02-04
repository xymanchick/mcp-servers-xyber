from fastapi import Request

from mcp_server_hangman.hangman.module import HangmanService


def get_hangman_service(request: Request) -> HangmanService:
    return request.app.state.hangman_service
