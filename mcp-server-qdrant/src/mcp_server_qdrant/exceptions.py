from fastapi import status
from fastmcp.exceptions import ToolError
from pydantic import ValidationError as PydanticValidationError


class ValidationError(ToolError):
    """Custom exception for input validation failures."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, error: PydanticValidationError, code: str = "VALIDATION_ERROR"):
        error_details = "; ".join(
            f"{err['loc'][0]}: {err['msg']}" for err in error.errors()
        )
        self.message = f"Invalid parameters: {error_details}"
        self.code = code

        super().__init__(self.message)
