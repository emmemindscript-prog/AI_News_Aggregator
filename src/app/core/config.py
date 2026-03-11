"""
AI News Aggregator - Configuration
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )
    
    # App
    APP_NAME: str = "AI News Aggregator"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///data/ainews.db"
    
    # LLM (OpenRouter)
    LLM_API_KEY: str
    LLM_MODEL: str = "zhipu/glm-4-7"
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 500
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: str  # @channel or -1001234567890
    
    # Scheduler
    FETCH_SCHEDULE: str = "0 */3 * * *"  # Every 3 hours
    DELIVERY_SCHEDULE: str = "0 8,14,20 * * *"  # 8am, 2pm, 8pm
    
    # Features
    ENABLE_AUTOMATIC_DELIVERY: bool = False
    DEFAULT_LANGUAGE: str = "it"
    MAX_SUMMARY_LENGTH: int = 280
    
    # Content Sources
    ENABLE_HACKERNEWS: bool = True
    ENABLE_REDDIT: bool = True
    ENABLE_DEVTO: bool = False
    ENABLE_ARXIV: bool = False
    ENABLE_GITHUB: bool = False
    
    # Reddit credentials (optional)
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "AI-News-Aggregator/1.0"
    
    # Categories
    CATEGORIES: List[str] = [
        "ai-general",
        "robotics", 
        "vibecoding",
        "openclaw",
        "llm",
        "ethics",
        "research"
    ]
    
    # Subreddits to monitor
    SUBREDDITS: List[str] = [
        "artificial",
        "MachineLearning",
        "ChatGPT",
        "OpenAI",
        "robotics",
        "LocalLLaMA",
        "singularity"
    ]
    
    @property
    def telegram_channel_id_int(self) -> int:
        """Convert channel ID to int if it's numeric"""
        try:
            return int(self.TELEGRAM_CHANNEL_ID)
        except ValueError:
            return self.TELEGRAM_CHANNEL_ID


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
