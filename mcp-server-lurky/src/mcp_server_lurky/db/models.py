from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    JSON,
    func,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class LurkySpace(Base):
    """
    Stores full details and summaries of Twitter Spaces fetched from Lurky API.
    """

    __tablename__ = "lurky_spaces"

    id = Column(String(50), primary_key=True)
    creator_id = Column(String(100), nullable=True)
    creator_handle = Column(String(100), nullable=True)
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    minimized_summary = Column(Text, nullable=True)
    state = Column(String(50), nullable=True)
    language = Column(String(10), nullable=True)
    overall_sentiment = Column(String(50), nullable=True)
    participant_count = Column(Integer, nullable=True)
    subscriber_count = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    discussions = relationship("LurkyDiscussion", back_populates="space", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LurkySpace(id='{self.id}', title='{self.title}', state='{self.state}')>"


class LurkyDiscussion(Base):
    """
    Stores individual discussion segments for a space.
    """

    __tablename__ = "lurky_discussions"

    id = Column(String(100), primary_key=True)
    space_id = Column(String(50), ForeignKey("lurky_spaces.id"), nullable=False)
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    started_at = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    coins = Column(JSON, nullable=True)
    speaker_ids = Column(JSON, nullable=True)
    categories = Column(JSON, nullable=True)

    space = relationship("LurkySpace", back_populates="discussions")

    def __repr__(self):
        return f"<LurkyDiscussion(id='{self.id}', space_id='{self.space_id}', title='{self.title}')>"
