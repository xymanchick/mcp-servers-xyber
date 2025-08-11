# Hangman MCP Server

Play Hangman reliably via MCP tools. The server maintains per-player game state in memory and returns a `player_id` from `start_game` that the client must pass to `guess_letter`.

## Tools

- `start_game(secret_word: str, max_attempts: int = 6) -> GameState`
  - Starts or resets a game and returns a newly generated `player_id`.
- `guess_letter(player_id: str, letter: str) -> GameState`
  - Guesses a single character and returns updated state for that `player_id`.

`GameState` includes `player_id`, `masked_chars` (list of characters; unrevealed letters are `_`), `remaining_attempts`, `correct_letters`, `incorrect_letters`, and flag `won`.

## Running

```bash
uv run mcp-server-hangman -m mcp_server_hangman -- --host 0.0.0.0 --port 8015
```

No headers required. Persist and pass the returned `player_id` to subsequent `guess_letter` calls.

## Behavioral requirements and test cases

- **start_game generates session**
  - Returns a new `player_id` (UUID hex) per call.
  - Initializes `masked_chars` to underscores with length equal to the secret word.
  - `max_attempts` must be positive. If not, return ToolError.

- **Secret word validation**
  - Secret word must be a non-empty string of alphabetic characters only.
  - If it contains symbols, spaces, or digits, return ToolError and do not start a game.

- **Guess input validation**
  - Only one character is allowed per guess. If multiple characters (e.g., "ab"), return ToolError.
  - Only alphabetic characters are allowed. If non-letter (e.g., "@", "1"), return ToolError.
  - On validation error, game state must remain unchanged (no attempt consumed).

- **Case-insensitive guessing, original case preserved**
  - Letter matching is case-insensitive.
  - Revealed letters in `masked_chars` preserve the original case of the secret word.

- **Correct and incorrect guesses**
  - Correct guesses reveal all occurrences of the letter.
  - Incorrect guesses decrement `remaining_attempts` by 1.
  - Repeated guesses (already guessed correct or incorrect) do not decrement attempts and do not duplicate entries.

- **Win condition**
  - When all letters are revealed, `won` becomes `true`.
  - After a win, the game is terminated: the `player_id` becomes invalid and subsequent `guess_letter` calls return ToolError (no state changes).

- **Loss condition**
  - When `remaining_attempts` reaches 0 and the word is not fully revealed, the game is terminated.
  - After termination, the `player_id` becomes invalid and subsequent `guess_letter` calls return ToolError.

- **Stability and errors**
  - Any ToolError must not crash the server.
  - Valid ongoing games remain playable after unrelated errors.

- **Response shape for agents**
  - `masked_chars` is a list (e.g., `["_", "_", "_", "_"]`) to make spacing explicit for rendering like `_ _ _ _`.

These behaviors are covered by tests in `mcp-server-hangman/tests/`:
- Service tests validate initialization, validation errors, case-insensitive reveals, repeated guesses, win path, and termination on attempts=0.
- Server tool tests validate ToolError propagation, no-op on invalid inputs, loss termination, and win termination.


