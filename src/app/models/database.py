"""
AI News Aggregator - Database Models
"""

import hashlib
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import create_engine, String, DateTime, Integer, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Mapped, mapped_column

# SQLite setup
Base = declarative_base()


class ArticleStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELIVERED = "delivered"
    ERROR = "error"


class Article(Base):
    """News article model"""
    
    __tablename__ = "articles"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    content_preview: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # hackernews|reddit|etc
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ArticleStatus.PENDING, index=True)
    language: Mapped[str] = mapped_column(String(2), default="it")
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[float] = mapped_column(Integer, default=0)  # 0-100 scale
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_status_fetched', 'status', 'fetched_at'),
        Index('idx_source_category', 'source', 'category'),
    )
    
    @staticmethod
    def generate_id(url: str) -> str:
        """Generate unique ID from URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:32]
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize title for deduplication"""
        return " ".join(title.lower().split())
    
    def __repr__(self):
        return f"<Article(id={self.id[:8]}, source={self.source}, status={self.status})>"


class Stats(Base):
    """Daily statistics"""
    
    __tablename__ = "stats"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, unique=True)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_processing_time: Mapped[float] = mapped_column(Integer, default=0)


class Settings(Base):
    """Application settings storage"""
    
    __tablename__ = "settings"
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database setup
engine = None
SessionLocal = None


def init_database(database_url: str = "sqlite:///data/ainews.db"):
    """Initialize database connection"""
    global engine, SessionLocal
    
    engine = create_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    return engine


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_article(db: Session, url: str, title: str) -> tuple[Article, bool]:
    """Get existing article or create new one. Returns (article, is_new)"""
    article_id = Article.generate_id(url)
    
    existing = db.query(Article).filter(
        (Article.id == article_id) | (Article.url == url)
    ).first()
    
    if existing:
        return existing, False
    
    return Article(id=article_id, url=url, title=title), True
