"""
AI News Aggregator - FastAPI Main Application
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings, Settings
from app.models.database import init_database, get_db, Article
from app.services.aggregator import NewsAggregator
from app.services.telegram import TelegramDeliveryService
from sqlalchemy.orm import Session


# Pydantic models for API
class ArticleResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    source: str
    category: Optional[str]
    status: str
    fetched_at: str
    url: str
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_articles: int
    pending: int
    approved: int
    delivered: int
    rejected: int


class FetchRequest(BaseModel):
    limit: int = 20
    auto_approve: bool = False


class DeliverRequest(BaseModel):
    limit: int = 5
    dry_run: bool = False


class ArticleAction(BaseModel):
    article_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    settings = get_settings()
    
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    init_database()
    print("Database initialized")
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="AI News Aggregator",
    description="Automated AI news collection and delivery system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

aggregator = NewsAggregator()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI News Aggregator",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "ai-news-aggregator"}


@app.get("/config")
async def get_config():
    """Get current configuration (safe)"""
    settings = get_settings()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "default_language": settings.DEFAULT_LANGUAGE,
        "sources_enabled": {
            "hackernews": settings.ENABLE_HACKERNEWS,
            "reddit": settings.ENABLE_REDDIT,
            "devto": settings.ENABLE_DEVTO,
        },
        "auto_delivery": settings.ENABLE_AUTOMATIC_DELIVERY
    }


@app.post("/fetch/trigger")
async def trigger_fetch(request: FetchRequest):
    """Manually trigger a fetch cycle"""
    try:
        result = await aggregator.run_fetch_cycle(limit=request.limit)
        
        return {
            "status": "success",
            "fetched": result["total"],
            "new": result["new"],
            "duplicates": result["duplicates"],
            "message": f"Fetched {result['total']} articles, {result['new']} new"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles")
async def list_articles(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
    """List articles with optional filtering"""
    db = next(get_db())
    try:
        query = db.query(Article)
        
        if status:
            query = query.filter_by(status=status)
        if category:
            query = query.filter_by(category=category)
            
        articles = query.order_by(Article.fetched_at.desc()).limit(limit).all()
        
        return [{
            "id": a.id,
            "title": a.title,
            "summary": a.summary,
            "source": a.source,
            "category": a.category,
            "status": a.status,
            "url": a.url,
            "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None
        } for a in articles]
    finally:
        db.close()


@app.post("/articles/{article_id}/approve")
async def approve_article(article_id: str):
    """Approve an article for publishing"""
    success = aggregator.approve_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "approved", "article_id": article_id}


@app.post("/articles/{article_id}/reject")
async def reject_article(article_id: str):
    """Reject an article"""
    success = aggregator.reject_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "rejected", "article_id": article_id}


@app.post("/deliver/batch")
async def deliver_batch(request: DeliverRequest):
    """Deliver approved articles to Telegram"""
    try:
        # Get approved articles
        articles = aggregator.get_articles_for_delivery(limit=request.limit)
        
        if not articles:
            return {"status": "no_articles", "message": "No approved articles to deliver"}
        
        if request.dry_run:
            return {
                "status": "dry_run",
                "would_deliver": len(articles),
                "articles": [{"id": a.id, "title": a.title} for a in articles]
            }
        
        # Deliver
        telegram = TelegramDeliveryService()
        results = await telegram.batch_deliver(articles)
        
        return {
            "status": "delivered",
            "sent": results["sent"],
            "failed": results["failed"],
            "message_ids": results["message_ids"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/test")
async def test_telegram():
    """Send a test message to Telegram channel"""
    try:
        telegram = TelegramDeliveryService()
        success = await telegram.send_test_message("🤖 AI News Aggregator test!")
        
        if success:
            return {"status": "success", "message": "Test message sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test message")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    db = next(get_db())
    try:
        from sqlalchemy import func
        
        total = db.query(Article).count()
        pending = db.query(Article).filter_by(status="pending").count()
        approved = db.query(Article).filter_by(status="approved").count()
        delivered = db.query(Article).filter_by(status="delivered").count()
        rejected = db.query(Article).filter_by(status="rejected").count()
        
        return {
            "total_articles": total,
            "pending": pending,
            "approved": approved,
            "delivered": delivered,
            "rejected": rejected
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
