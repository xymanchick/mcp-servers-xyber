from typing import Annotated

from fastapi import Depends

from mcp_server_quill.config import get_app_settings
from mcp_server_quill.quill.client import QuillAPI
from mcp_server_quill.quill.search import TokenSearchAPI


async def get_quill_client() -> QuillAPI:
    settings = get_app_settings()
    if not settings.quill.api_key:
        # Allow running without API key for search-only features, but warn/error if used
        pass
    return QuillAPI(api_key=settings.quill.api_key or "", base_url=settings.quill.base_url)


async def get_search_client() -> TokenSearchAPI:
    settings = get_app_settings()
    return TokenSearchAPI(config=settings.dexscreener)


QuillClientDep = Annotated[QuillAPI, Depends(get_quill_client)]
SearchClientDep = Annotated[TokenSearchAPI, Depends(get_search_client)]
