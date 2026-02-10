from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing API is healthy

    """
    return {"status": "healthy"}
