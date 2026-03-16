"""
AI News Aggregator - Telegram Delivery Service
Improved HTML formatting for beautiful Telegram messages
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from telegram import Bot, constants
from telegram.constants import ParseMode
from app.models.database import Article
from app.core.config import get_settings
import re
import asyncio


@dataclass
class TelegramMessage:
    """Structured message for Telegram"""
    text: str
    category_emoji: str
    article_id: str
    url: str


# Alias will be set after class definition


class TelegramService:
    """Telegram delivery service with beautiful HTML formatting"""
    
    CATEGORY_EMOJIS = {
        "ai-general": "🤖",
        "robotics": "🦾",
        "llm": "🧠",
        "vibecoding": "💻",
        "openclaw": "🔧",
        "ethics": "⚖️",
        "research": "🔬",
        "devops": "🚀",
        "other": "📱"
    }
    
    CATEGORY_NAMES_IT = {
        "ai-general": "Intelligenza Artificiale",
        "robotics": "Robotica",
        "llm": "Language Models",
        "vibecoding": "Vibe Coding",
        "openclaw": "OpenClaw",
        "ethics": "Etica AI",
        "research": "Ricerca",
        "devops": "DevOps",
        "other": "Tech"
    }
    
    CATEGORY_NAMES_EN = {
        "ai-general": "Artificial Intelligence",
        "robotics": "Robotics",
        "llm": "Language Models",
        "vibecoding": "Vibe Coding",
        "openclaw": "OpenClaw",
        "ethics": "AI Ethics",
        "research": "Research",
        "devops": "DevOps",
        "other": "Tech"
    }
    
    def __init__(self, bot_token: Optional[str] = None):
        self.settings = get_settings()
        self.bot_token = bot_token or self.settings.TELEGRAM_BOT_TOKEN
        self.bot = Bot(token=self.bot_token)
        self.channel_id = self.settings.TELEGRAM_CHANNEL_ID
    
    def format_message(self, article: Article, language: str = "it") -> TelegramMessage:
        """Format article for Telegram with beautiful HTML"""
        emoji = self.CATEGORY_EMOJIS.get(article.category, "🔍")
        category_name = self.CATEGORY_NAMES_IT.get(article.category, "Tech")
        
        if language == "it":
            text = self._format_italian(article, emoji, category_name)
        else:
            category_name = self.CATEGORY_NAMES_EN.get(article.category, "Tech")
            text = self._format_english(article, emoji, category_name)
        
        return TelegramMessage(
            text=text,
            category_emoji=emoji,
            article_id=article.id,
            url=article.url
        )
    
    def _format_italian(self, article: Article, emoji: str, category: str) -> str:
        """Format message in Italian - Beautiful HTML layout"""
        from html import escape
        
        title = escape(article.title)
        summary = escape(article.summary or "Leggi l'articolo completo per i dettagli...")
        
        # Truncate summary if too long
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        # Beautiful HTML formatting
        return f"""{emoji} <b>{escape(category.upper())}</b>

🎯 <b>{title}</b>

{summary}

<a href="{article.url}">🔗 Leggi originale</a>

<blockquote>👤 {article.source} • {article.fetched_at.strftime('%d/%m/%Y')}</blockquote>"""
    
    def _format_english(self, article: Article, emoji: str, category: str) -> str:
        """Format message in English - Beautiful HTML layout"""
        from html import escape
        
        title = escape(article.title)
        summary = escape(article.summary or "Read the full article for details...")
        
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return f"""{emoji} <b>{escape(category.upper())}</b>

🎯 <b>{title}</b>

{summary}

<a href="{article.url}">🔗 Read article</a>

<blockquote>👤 {article.source} • {article.fetched_at.strftime('%Y-%m-%d')}</blockquote>"""
    
    async def send_article(
        self,
        article: Article,
        language: str = "it",
        disable_notification: bool = False
    ) -> Optional[int]:
        """Send article to Telegram channel with HTML formatting"""
        try:
            message = self.format_message(article, language)
            
            sent_message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=message.text,
                parse_mode=ParseMode.HTML,
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
        delay_seconds: float = 0.5,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """Deliver multiple articles with rate limiting"""
        results = {
            "sent": 0,
            "failed": 0,
            "message_ids": [],
            "errors": []
        }
        
        for article in articles:
            if article.status == "delivered":
                continue
            
            try:
                msg_id = await self.send_article(article)
                if msg_id:
                    results["sent"] += 1
                    results["message_ids"].append(msg_id)
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
            
            await asyncio.sleep(delay_seconds)
        
        return results

    async def send_test_message(
        self,
        text: str = "🤖 AI News Aggregator test!",
        target_channel: Optional[str] = None
    ) -> bool:
        """Send a test message to verify configuration"""
        try:
            target = target_channel or self.channel_id
            await self.bot.send_message(
                chat_id=target,
                text=f"<b>🧪 Test</b>\n\n{text}",
                parse_mode=ParseMode.HTML
            )
            return True
        except Exception as e:
            print(f"Test message failed: {e}")
            return False


# Backward compatibility alias
TelegramDeliveryService = TelegramService
