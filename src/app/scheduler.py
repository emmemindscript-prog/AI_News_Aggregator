"""
AI News Aggregator - Background Scheduler
Handles automatic fetch cycles and delivery
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import signal
import sys

from app.core.config import get_settings
from app.services.aggregator import NewsAggregator
from app.services.telegram import TelegramDeliveryService
from app.models.database import init_database
from app.models.database import get_db, Article, ArticleStatus
from sqlalchemy.orm import Session


class FetchScheduler:
    """Automated scheduler for fetching and delivering AI news"""
    
    def __init__(self):
        self.settings = get_settings()
        self.aggregator = NewsAggregator()
        self.telegram = TelegramDeliveryService()
        self.running = False
        self.last_fetch: Optional[datetime] = None
        self.last_deliver: Optional[datetime] = None
        
    async def start(self):
        """Start the scheduler loop"""
        print(f"🚀 Starting AI News Aggregator Scheduler")
        print(f"Fetch interval: {self.settings.FETCH_INTERVAL_MINUTES} minutes")
        print(f"Auto delivery: {self.settings.ENABLE_AUTOMATIC_DELIVERY}")
        
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Initial fetch on startup
        await self._run_fetch_cycle()
        
        # Main loop
        while self.running:
            await asyncio.sleep(60)  # Check every minute
            
            if not self.running:
                break
                
            # Check if it's time to fetch
            if self._should_fetch():
                await self._run_fetch_cycle()
                
        print("⏹️ Scheduler stopped")
        
    def _should_fetch(self) -> bool:
        """Check if it's time to fetch based on interval"""
        if not self.last_fetch:
            return True
        elapsed = datetime.utcnow() - self.last_fetch
        return elapsed >= timedelta(minutes=self.settings.FETCH_INTERVAL_MINUTES)
    
    def _should_deliver(self) -> bool:
        """Check if it's time to deliver"""
        if not self.settings.ENABLE_AUTOMATIC_DELIVERY:
            return False
        if not self.last_deliver:
            return True
        elapsed = datetime.utcnow() - self.last_deliver
        return elapsed >= timedelta(minutes=self.settings.DELIVERY_INTERVAL_MINUTES)
        
    async def _run_fetch_cycle(self):
        """Run a complete fetch cycle"""
        print(f"\n[{datetime.utcnow().isoformat()}] Starting fetch cycle...")
        
        try:
            result = await self.aggregator.run_fetch_cycle(
                limit=self.settings.FETCH_LIMIT
            )
            
            self.last_fetch = datetime.utcnow()
            
            print(f"  ✓ Fetched: {result['total']}")
            print(f"  ✓ New articles: {result['new']}")
            print(f"  ✓ Duplicates: {result['duplicates']}")
            
            # Auto-approve good articles (score > threshold)
            if result['new'] > 0:
                await self._auto_approve_high_quality()
                
            # Auto-deliver if enabled
            if self._should_deliver():
                await self._run_delivery_cycle()
                
        except Exception as e:
            print(f"  ✗ Fetch cycle error: {e}")
            
    async def _auto_approve_high_quality(self):
        """Auto-approve articles with high score"""
        db = next(get_db())
        try:
            # Auto-approve articles with score > 7.0
            high_score = db.query(Article).filter(
                Article.status == ArticleStatus.PENDING,
                Article.score >= 7.0
            ).all()
            
            for article in high_score:
                self.aggregator.approve_article(article.id)
                
            if high_score:
                print(f"  → Auto-approved {len(high_score)} high-quality articles")
                
        finally:
            db.close()
            
    async def _run_delivery_cycle(self):
        """Run a delivery cycle"""
        print(f"[{datetime.utcnow().isoformat()}] Starting delivery cycle...")
        
        try:
            articles = self.aggregator.get_articles_for_delivery(
                limit=self.settings.DELIVERY_LIMIT
            )
            
            if not articles:
                print("  → No articles to deliver")
                return
                
            results = await self.telegram.batch_deliver(
                articles,
                delay_seconds=2.0
            )
            
            self.last_deliver = datetime.utcnow()
            
            print(f"  ✓ Delivered: {results['sent']}/{len(articles)}")
            if results['failed'] > 0:
                print(f"  ✗ Failed: {results['failed']}")
                
        except Exception as e:
            print(f"  ✗ Delivery cycle error: {e}")
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
        
    def stop(self):
        """Stop the scheduler"""
        self.running = False


class ManualRunner:
    """Single-run mode for cron/manual execution"""

    @staticmethod
    def _ensure_db():
        """Ensure database is initialized"""
        from app.models.database import init_database, engine
        if engine is None:
            init_database()

    
    @staticmethod
    async def fetch_only(limit: int = 20):
        """Run fetch cycle only"""
        ManualRunner._ensure_db()
        print("🤖 AI News Aggregator - Fetch Mode")
        
        aggregator = NewsAggregator()
        result = await aggregator.run_fetch_cycle(limit=limit)
        
        print(f"✓ Fetched: {result['total']} articles")
        print(f"New: {result['new']}")
        print(f"Duplicates: {result['duplicates']}")
        
        return result
        
    @staticmethod
    async def deliver_only(limit: int = 5):
        """Run delivery cycle only"""
        ManualRunner._ensure_db()
        print("📤 AI News Aggregator - Deliver Mode")
        
        aggregator = NewsAggregator()
        telegram = TelegramDeliveryService()
        
        articles = aggregator.get_articles_for_delivery(limit=limit)
        print(f"Found {len(articles)} approved articles to deliver")
        
        if not articles:
            return "No articles to deliver"
            
        results = await telegram.batch_deliver(articles)
        
        print(f"Delivered: {results['sent']}")
        print(f"Failed: {results['failed']}")
        
        return results
        
    @staticmethod
    async def full_cycle(fetch_limit: int = 20, deliver_limit: int = 5):
        """Run full cycle: fetch + auto-approve + deliver"""
        ManualRunner._ensure_db()
        print("🤖 AI News Aggregator - Full Cycle Mode")
        
        # Step 1: Fetch
        fetch_result = await ManualRunner.fetch_only(limit=fetch_limit)
        
        if fetch_result['new'] == 0:
            print("No new articles, skipping delivery")
            return {"fetched": fetch_result, "delivered": 0}
        
        # Step 2: Auto-approve
        aggregator = NewsAggregator()
        await FetchScheduler()._auto_approve_high_quality()
        
        # Step 3: Deliver
        deliver_result = await ManualRunner.deliver_only(limit=deliver_limit)
        
        return {
            "fetched": fetch_result,
            "delivered": deliver_result
        }


if __name__ == "__main__":
    import sys
    
    init_database()
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduler"
    
    if mode == "scheduler":
        # Background scheduler mode
        scheduler = FetchScheduler()
        try:
            asyncio.run(scheduler.start())
        except KeyboardInterrupt:
            scheduler.stop()
    elif mode == "fetch":
        # Single fetch run
        asyncio.run(ManualRunner.fetch_only())
    elif mode == "deliver":
        # Single delivery run
        asyncio.run(ManualRunner.deliver_only())
    elif mode == "full":
        # Full cycle
        asyncio.run(ManualRunner.full_cycle())
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python -m app.scheduler [scheduler|fetch|deliver|full]")