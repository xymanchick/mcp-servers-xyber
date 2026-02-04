from mcp_server_hangman.hybrid_routers.guess_letter import router as guess_letter_router
from mcp_server_hangman.hybrid_routers.pricing import router as pricing_router
from mcp_server_hangman.hybrid_routers.start_game import router as start_game_router

routers = [start_game_router, guess_letter_router, pricing_router]
