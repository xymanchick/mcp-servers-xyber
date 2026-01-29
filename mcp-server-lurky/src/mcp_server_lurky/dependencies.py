from typing import AsyncGenerator

from mcp_server_lurky.db.database import get_db_manager
from mcp_server_lurky.lurky.config import get_lurky_config
from mcp_server_lurky.lurky.module import LurkyClient


async def get_lurky_client() -> AsyncGenerator[LurkyClient, None]:
    config = get_lurky_config()
    client = LurkyClient(config)
    yield client


def get_db():
    return get_db_manager()
