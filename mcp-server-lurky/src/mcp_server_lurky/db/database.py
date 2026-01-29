import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker, joinedload

from mcp_server_lurky.config import get_app_settings
from mcp_server_lurky.db.models import Base, LurkySpace, LurkyDiscussion

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for Lurky space caching."""

    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            settings = get_app_settings()
            database_url = settings.database.DATABASE_URL
        
        if not database_url:
            raise ValueError("DATABASE_URL is required.")
        
        try:
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
            )
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                expire_on_commit=False
            )
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise ValueError(f"Database connection failed: {e}") from e

        self._create_tables()

    def _create_tables(self):
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created/verified")
            # Run migrations to update existing tables
            self._migrate_tables()
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def _migrate_tables(self):
        """Migrate existing tables to match current model definitions."""
        try:
            with self.engine.begin() as conn:
                # Check if lurky_discussions table exists and if started_at is Integer
                result = conn.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'lurky_discussions' 
                    AND column_name = 'started_at'
                """))
                row = result.fetchone()
                
                if row and row[0] == 'integer':
                    logger.info("Migrating lurky_discussions.started_at from INTEGER to TIMESTAMP...")
                    # Convert integer timestamps to timestamps, handling NULL values
                    # Note: PostgreSQL to_timestamp expects seconds, but our data might be milliseconds
                    conn.execute(text("""
                        ALTER TABLE lurky_discussions 
                        ALTER COLUMN started_at TYPE TIMESTAMP USING 
                        CASE 
                            WHEN started_at IS NULL THEN NULL
                            ELSE to_timestamp(started_at / 1000.0)
                        END
                    """))
                    logger.info("Migration completed: started_at column updated to TIMESTAMP")
        except Exception as e:
            # If migration fails, log warning but don't fail startup
            # The column might not exist yet or might already be the correct type
            logger.debug(f"Migration check completed (or not needed): {e}")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def get_space(self, space_id: str) -> Optional[LurkySpace]:
        session = self.get_session()
        try:
            space = session.query(LurkySpace).options(
                joinedload(LurkySpace.discussions)
            ).filter_by(id=space_id).first()
            if space:
                logger.info(f"CACHE HIT: Found space {space_id} in database")
            else:
                logger.debug(f"CACHE MISS: Space {space_id} not found in database")
            return space
        except SQLAlchemyError as e:
            logger.error(f"Error getting space {space_id} from database: {e}")
            return None
        finally:
            session.close()

    def save_space(self, space_data: Dict[str, Any]) -> bool:
        session = self.get_session()
        try:
            space_id = space_data.get("id")
            if not space_id:
                return False

            ts_fields = ["created_at", "started_at", "scheduled_at", "ended_at", "analyzed_at"]
            for field in ts_fields:
                val = space_data.get(field)
                if isinstance(val, (int, float)):
                    space_data[field] = datetime.fromtimestamp(val / 1000, tz=timezone.utc)

            discussions_data = space_data.pop("discussions", [])

            existing_space = session.query(LurkySpace).filter_by(id=space_id).first()

            if existing_space:
                for key, value in space_data.items():
                    if hasattr(existing_space, key):
                        setattr(existing_space, key, value)
                logger.info(f"CACHE UPDATE: Updated space {space_id} in database")
            else:
                space = LurkySpace(**space_data)
                session.add(space)
                logger.info(f"CACHE SAVE: Saved new space {space_id} to database")

            # Always delete existing discussions to ensure consistency
            if existing_space:
                session.query(LurkyDiscussion).filter_by(space_id=space_id).delete()
            
            # Add new discussions (even if empty list, this clears stale data)
            if discussions_data:
                for d_data in discussions_data:
                    # Convert timestamp fields from epoch milliseconds to datetime
                    d_ts = d_data.get("timestamp")
                    if isinstance(d_ts, (int, float)):
                        d_data["timestamp"] = datetime.fromtimestamp(d_ts / 1000, tz=timezone.utc)
                    
                    # Convert started_at if present (should be epoch milliseconds)
                    d_started_at = d_data.get("started_at")
                    if isinstance(d_started_at, (int, float)):
                        d_data["started_at"] = datetime.fromtimestamp(d_started_at / 1000, tz=timezone.utc)
                    elif d_started_at is None:
                        # Ensure None is explicitly set
                        d_data["started_at"] = None
                    
                    d_data["space_id"] = space_id
                    # Remove keys that don't match model
                    valid_keys = {c.key for c in LurkyDiscussion.__table__.columns}
                    filtered_d_data = {k: v for k, v in d_data.items() if k in valid_keys}
                    discussion = LurkyDiscussion(**filtered_d_data)
                    session.add(discussion)

            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving space to database: {e}")
            return False
        finally:
            session.close()


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
