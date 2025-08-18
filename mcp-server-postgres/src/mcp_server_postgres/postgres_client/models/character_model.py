from mcp_server_postgres.postgres_client.models.base_model import Base
from sqlalchemy import JSON, UUID, String
from sqlalchemy.orm import Mapped, mapped_column


class Agent(Base):
    """Character model representing an agent with all its attributes"""

    __tablename__ = "agent"

    user_id: Mapped[int]
    uuid: Mapped[str] = mapped_column(
        UUID, nullable=False, unique=True, server_default="uuid_generate_v4()"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[dict] = mapped_column(JSON, nullable=False)
    image_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    solana_address: Mapped[str | None]
    base_address: Mapped[str | None]
    ticker: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
