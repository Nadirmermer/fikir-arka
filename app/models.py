"""
Database models for Content Manager API v2.0.0
SQLAlchemy ORM models with modern typing
"""

import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, Integer, Float, Enum as PgEnum
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from typing import Optional
import enum

Base = declarative_base()

class Status(str, enum.Enum):
    PENDING = "pending"
    LIKED = "liked"
    DISLIKED = "disliked"

class AIContentStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class SourcePlatform(str, enum.Enum):
    RSS = "rss"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    WEBSITE = "website"

class SourceType(str, enum.Enum):
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    PROFILE = "profile"
    HASHTAG = "hashtag"
    RSS = "rss"

class Source(Base):
    """Content source model - Kazıma kaynakları"""
    __tablename__ = "sources"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source info
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    platform = Column(String(50), nullable=False)  # YouTube, Instagram, Twitter, RSS
    source_type = Column(String(50), nullable=False)  # channel, profile, feed, etc.
    
    # Settings
    is_active = Column(Boolean, default=True)
    scrape_frequency = Column(String(20), default="daily")  # daily, weekly, manual
    
    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # Metrics
    total_content_count = Column(Integer, default=0)
    last_content_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Source(id='{self.id}', name='{self.name}', platform='{self.platform}')>"

class Topic(Base):
    """Content topic model - Kazınan içerikler"""
    __tablename__ = "topics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Content info
    title = Column(String(500), nullable=False)
    description = Column(Text)
    content = Column(Text)
    platform = Column(String(50), nullable=False)  # YouTube, Instagram, Twitter, Blog
    source = Column(String(200), nullable=False)   # Source name
    link = Column(String(1000), nullable=False)
    
    # Dates
    publish_date = Column(DateTime)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Swipe status
    status = Column(String(20), default="pending")  # pending, liked, disliked
    liked_at = Column(DateTime)
    disliked_at = Column(DateTime)
    
    # Metrics
    popularity_score = Column(Float, default=0.0)
    content_length = Column(Integer, default=0)
    
    # Relationships
    ai_contents = relationship("AIContent", back_populates="topic")
    
    def __repr__(self):
        return f"<Topic(id='{self.id}', title='{self.title[:50]}...', status='{self.status}')>"

class AIContent(Base):
    """AI generated content model"""
    __tablename__ = "ai_contents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    generated_content = Column(Text, nullable=True)
    
    # AI settings
    ai_model = Column(String(100), default="gemini-2.0-flash-exp")
    prompt_used = Column(Text)
    temperature = Column(Float, default=0.7)
    
    # Status
    status = Column(String(20), default="pending")  # pending, generating, completed, failed
    
    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    topic_id = Column(String, ForeignKey("topics.id"))
    topic = relationship("Topic", back_populates="ai_contents")
    
    # Metrics
    generation_time_seconds = Column(Float)
    content_length = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<AIContent(id='{self.id}', title='{self.title[:50]}...', status='{self.status}')>"

# Pydantic models for API
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    platform: str
    source: str
    link: str
    publish_date: Optional[datetime] = None
    popularity_score: Optional[float] = 0.0

class TopicCreate(TopicBase):
    pass

class TopicUpdate(BaseModel):
    status: Optional[str] = None
    liked_at: Optional[datetime] = None
    disliked_at: Optional[datetime] = None

class TopicResponse(TopicBase):
    id: str
    status: str
    extracted_at: datetime
    liked_at: Optional[datetime] = None
    disliked_at: Optional[datetime] = None
    content_length: int
    
    class Config:
        from_attributes = True

class SourceBase(BaseModel):
    name: str
    url: str
    platform: str
    source_type: str
    is_active: Optional[bool] = True
    scrape_frequency: Optional[str] = "daily"

class SourceCreate(SourceBase):
    pass

class SourceResponse(SourceBase):
    id: str
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AIContentBase(BaseModel):
    title: str
    content: str
    ai_model: Optional[str] = "gemini-2.0-flash-exp"
    temperature: Optional[float] = 0.7

class AIContentCreate(AIContentBase):
    topic_id: str
    prompt_used: Optional[str] = None

class AIContentResponse(AIContentBase):
    id: str
    # İçerik henüz üretilmemişse None olabilir → Optional
    generated_content: Optional[str] = None
    status: str
    topic_id: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    generation_time_seconds: Optional[float] = None
    # Üretim tamamlanmadıysa content_length bilinmez → Optional
    content_length: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# Statistics models
class StatsResponse(BaseModel):
    total_topics: int
    pending_topics: int
    liked_topics: int
    disliked_topics: int
    total_sources: int
    active_sources: int
    total_ai_contents: int
    completed_ai_contents: int
    last_scrape_time: Optional[datetime] = None
    next_scrape_time: Optional[datetime] = None
    # New fields required by frontend
    today_topics: int = 0
    sources_count: int = 0
    last_update: datetime = datetime.utcnow()
    scraping_status: str = "idle"  # idle, running, failed 