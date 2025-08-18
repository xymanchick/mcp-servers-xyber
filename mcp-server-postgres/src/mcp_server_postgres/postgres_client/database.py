"""
Database connection and session handling for PostgreSQL.
"""

# Use absolute import within the mcp_server_postgres.postgres_client package
from mcp_server_postgres.postgres_client.config import PostgresConfig
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Get database connection URL from configuration
DATABASE_URL = PostgresConfig().get_db_url()

# Create engine for database connection
engine = create_async_engine(
    url=DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_pre_ping=True,  # Check connection validity before using it
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Don't flush automatically
)
