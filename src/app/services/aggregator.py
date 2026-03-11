"""
AI News Aggregator - Main Aggregator Service
Orchestrates fetchers, deduplication, and article processing
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Tuple
from urllib.parse import urlparse

from app.core.config import get_settings
from app.models.database import SessionLocal, Article, ArticleStatus, get_or_create_article
from app.services.fetcher import ArticleAggregator as FetcherAggregator
from app.services.summarizer import SummarizerService
from app.services.categorizer import CategorizerService


class NewsAggregator:
    """Main orchestrator for the AI News Aggregator"""
    
    def __init__(self):
        self.settings = get_settings()
        self.fetcher = FetcherAggregator()
        self.summarizer = SummarizerService()
        self.categorizer = CategorizerService()
        
    async def run_fetch_cycle(self, limit: int = 20) -> dict:
        """
        Run a complete fetch cycle:
        1. Fetch from all sources
        2. Deduplicate
        3. Categorize
        4. Summarize
        5. Store in DB
        """
        # Step 1: Fetch
        fetched = await self.fetcher.fetch_all(limit=limit)
        
        if not fetched:
            return {"total": 0, "new": 0, "duplicates": 0}
            
        db = SessionLocal()
        
        try:
            new_count = 0
            dup_count = 0
            
            for article in fetched:
                # Deduplication check
                article_id = self._generate_id(article.url)
                
                existing = db.query(Article).filter_by(id=article_id).first()
                if existing:
                    dup_count += 1
                    continue
                    
                # Step 2: Categorize
                try:
                    category = await self.categorizer.categorize(article.title, article.content or "")
                except Exception as e:
                    print(f"Categorization error: {e}")
                    category = article.category or "ai-general"
                
                # Step 3: Summarize (only if content exists or title is long enough)
                summary = article.summary
                if not summary:
                    try:
                        text_to_summarize = article.content if article.content and len(article.content) > 100 else article.title
                        summary = await self.summarizer.summarize(
                            text_to_summarize,
                            language=self.settings.DEFAULT_LANGUAGE
                        )
                    except Exception as e:
                        print(f"Summarization error: {e}")
                        summary = article.title
                
                # Step 4: Create DB record
                new_article = Article(
                    id=article_id,
                    url=article.url,
                    title=article.title,
                    summary=summary,
                    content_preview=(article.content or "")[:1000],
                    source=article.source,
                    category=category,
                    published_at=article.published_at,
                    language=self.settings.DEFAULT_LANGUAGE,
                    status=ArticleStatus.PENDING,
                    score=article.score
                )
                
                db.add(new_article)
                new_count += 1
                
                # Rate limiting for LLM calls
                if new_count % 5 == 0:
                    await asyncio.sleep(0.5)
                    
            db.commit()
            
            return {
                "total": len(fetched),
                "new": new_count,
                "duplicates": dup_count,
                "articles": fetched[:5]  # Preview first 5
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def _generate_id(self, url: str) -> str:
        """Generate unique ID from URL"""
        import hashlib
        return hashlib.sha256(url.encode()).hexdigest()[:32]
    
    def get_articles_for_delivery(
        self,
        status: ArticleStatus = ArticleStatus.APPROVED,
        limit: int = 5
    ) -> List[Article]:
        """Get articles ready for Telegram delivery"""
        db = SessionLocal()
        try:
            articles = db.query(Article).filter_by(
                status=status,
                language=self.settings.DEFAULT_LANGUAGE
            ).order_by(
                Article.fetched_at.desc()
            ).limit(limit).all()
            
            return articles
        finally:
            db.close()
    
    def approve_article(self, article_id: str) -> bool:
        """Mark article as approved for publishing"""
        db = SessionLocal()
        try:
            article = db.query(Article).filter_by(id=article_id).first()
            if article:
                article.status = ArticleStatus.APPROVED
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def reject_article(self, article_id: str) -> bool:
        """Mark article as rejected"""
        db = SessionLocal()
        try:
            article = db.query(Article).filter_by(id=article_id).first()
            if article:
                article.status = ArticleStatus.REJECTED
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def mark_delivered(self, article_id: str, telegram_msg_id: int) -> bool:
        """Mark article as delivered and store Telegram message ID"""
        db = SessionLocal()
        try:
            article = db.query(Article).filter_by(id=article_id).first()
            if article:
                article.status = ArticleStatus.DELIVERED
                article.telegram_message_id = telegram_msg_id
                article.delivered_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
