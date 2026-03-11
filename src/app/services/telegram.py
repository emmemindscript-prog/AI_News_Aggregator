"""
AI News Aggregator - Telegram Delivery Service
Handles message formatting and sending to Telegram channel
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import random

from telegram import Bot
from telegram.constants import ParseMode

from app.core.config import get_settings
from app.models.database import Article, ArticleStatus, get_db


@dataclass
class TelegramMessage:
    """Formatted message ready for Telegram"""
    text: str
    category_emoji: str
    article_id: str = ""
    url: str = ""


class TelegramDeliveryService:
    """Service for delivering articles to Telegram"""
    
    CATEGORY_EMOJIS = {
        "ai-general": "🤖",
        "robotics": "⚙️",
        "llm": "💬",
        "vibecoding": "🎨",
        "openclaw": "🦀",
        "ethics": "⚖️",
        "research": "📄",
        "other": "🔍"
    }
    
    CATEGORY_NAMES_IT = {
        "ai-general": "Intelligenza Artificiale",
        "robotics": "Robotica",
        "llm": "Language Models",
        "vibecoding": "Vibe Coding",
        "openclaw": "OpenClaw",
        "ethics": "Etica AI",
        "research": "Ricerca",
        "other": "Tech"
    }
    
    def __init__(self, bot_token: Optional[str] = None):
        self.settings = get_settings()
        self.bot_token = bot_token or self.settings.TELEGRAM_BOT_TOKEN
        self.bot = Bot(token=self.bot_token)
        self.channel_id = self.settings.TELEGRAM_CHANNEL_ID
        
    def format_message(self, article: Article, language: str = "it") -> TelegramMessage:
        """Format article for Telegram"""
        emoji = self.CATEGORY_EMOJIS.get(article.category, "🔍")
        category_name = self.CATEGORY_NAMES_IT.get(article.category, "Tech")
        
        if language == "it":
            text = self._format_italian(article, emoji, category_name)
        else:
            text = self._format_english(article, emoji, category_name)
            
        return TelegramMessage(
            text=text,
            category_emoji=emoji,
            article_id=article.id,
            url=article.url
        )
    
    def _format_italian(self, article: Article, emoji: str, category: str) -> str:
        """Format message in Italian"""
        # Escape special chars for Markdown
        title = self._escape_markdown(article.title)
        summary = self._escape_markdown(article.summary or article.title)
        
        # Build message
        lines = [
            f"{emoji} *{category}*",
            "",
            f"*{title}*",
            "",
            summary,
            "",
            f"🔗 [Leggi originale]({article.url})",
            f"👤 {article.source} • {article.fetched_at.strftime('%d/%m/%Y')}"
        ]
        
        return "\n".join(lines)
    
    def _format_english(self, article: Article, emoji: str, category: str) -> str:
        """Format message in English"""
        title = self._escape_markdown(article.title)
        summary = self._escape_markdown(article.summary or article.title)
        
        lines = [
            f"{emoji} *{category}*",
            "",
            f"*{title}*",
            "",
            summary,
            "",
            f"🔗 [Read article]({article.url})",
            f"👤 {article.source} • {article.fetched_at.strftime('%Y-%m-%d')}"
        ]
        
        return "\n".join(lines)
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for Telegram MarkdownV2"""
        # For simplicity, use HTML escape instead
        import html
        return html.escape(text) if text else ""
    
    async def send_article(
        self,
        article: Article,
        language: str = "it",
        disable_notification: bool = False
    ) -> Optional[int]:
        """
        Send article to Telegram channel
        
        Returns:
            Telegram message ID or None on failure
        """
        try:
            message = self.format_message(article, language)
            
            # Use HTML parse mode for better compatibility
            sent_message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=message.text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=False,
                disable_notification=disable_notification
            )
            
            return sent_message.message_id
            
        except Exception as e:
            print(f"Telegram send error: {e}")
            return None
    
    async def batch_deliver(
        self,
        articles: List[Article],
        delay_seconds: float = 2.0,
        auto_approve: bool = False
    ) -> Dict[str, any]:
        """
        Deliver multiple articles with rate limiting
        
        Args:
            articles: List of articles to send
            delay_seconds: Delay between messages
            auto_approve: If True, mark as approved before sending
        """
        import asyncio
        
        results = {
            "sent": 0,
            "failed": 0,
            "message_ids": [],
            "errors": []
        }
        
        for article in articles:
            # Skip if already delivered
            if article.status == ArticleStatus.DELIVERED:
                continue
                
            try:
                msg_id = await self.send_article(article)
                
                if msg_id:
                    # Update article in DB
                    from sqlalchemy.orm import Session
                    db = next(get_db())
                    try:
                        article.telegram_message_id = msg_id
                        article.status = ArticleStatus.DELIVERED
                        db.commit()
                    finally:
                        db.close()
                    
                    results["sent"] += 1
                    results["message_ids"].append(msg_id)
                else:
                    results["failed"] += 1
                    
                # Rate limiting between API calls
                await asyncio.sleep(delay_seconds)
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
                
        return results
    
    async def send_test_message(self, text: str = "🤖 AI News Aggregator test message!") -> bool:
        """Send a test message to verify configuration"""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            return True
        except Exception as e:
            print(f"Test message failed: {e}")
            return False
