"""
AI News Aggregator - Content Fetcher Service
Asynchronous scraping from multiple sources
"""

import asyncio
import aiohttp
import feedparser
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from app.core.config import get_settings


@dataclass
class FetchedArticle:
    """Raw article data from scraping"""
    url: str
    title: str
    content: Optional[str]
    published_at: Optional[datetime]
    source: str
    source_id: str
    category: str = "ai-general"
    language: str = "en"
    author: Optional[str] = None
    tags: List[str] = None
    score: Optional[float] = None  # popularity score from source
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BaseFetcher:
    """Base class for content fetchers"""
    
    def __init__(self, name: str):
        self.name = name
        self.settings = get_settings()
        
    async def fetch(self, limit: int = 10) -> List[FetchedArticle]:
        """Fetch articles from this source"""
        raise NotImplementedError
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats"""
        if not timestamp_str:
            return None
        
        try:
            # Parse ISO format first
            if "T" in timestamp_str and "." in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            elif "T" in timestamp_str:
                # Handle +0000 timezone
                if "+" in timestamp_str or "-" in timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
                else:
                    # Assume UTC
                    return datetime.fromisoformat(timestamp_str + "+00:00")
            else:
                # Try feedparser format
                return datetime.fromtimestamp(feedparser._parse_date(timestamp_str))
        except Exception:
            # Fallback: convert string timestamp if numeric
            try:
                return datetime.fromtimestamp(float(timestamp_str))
            except:
                return datetime.now(timezone.utc)


class HackerNewsFetcher(BaseFetcher):
    """Fetcher for HackerNews using Algolia API"""
    
    BASE_URL = "https://hn.algolia.com/api/v1"
    
    async def fetch(self, limit: int = 10) -> List[FetchedArticle]:
        """Fetch recent AI-related stories"""
        if not self.settings.ENABLE_HACKERNEWS:
            return []
            
        url = f"{self.BASE_URL}/search"
        params = {
            "query": "AI OR artificial intelligence OR LLM OR ChatGPT OR agent",
            "tags": "story",
            "numericFilters": "created_at_i>" + str(int((datetime.now() - timedelta(days=7)).timestamp())),
            "constrainsDigests": "true",
            "limit": limit
        }
        
        articles = []
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"HN API error: {response.status}")
                        return []
                        
                    data = await response.json()
                    
                    for item in data.get("hits", [])[:limit]:
                        url = item.get("url") or f"https://news.ycombinator.com/item?id={item['objectID']}"
                        if not url:
                            continue
                            
                        # Score calculation
                        score = item.get("points", 0) + (item.get("num_comments", 0) * 2)
                        if item.get("created_at_i"):
                            age_hours = (datetime.now().timestamp() - item["created_at_i"]) / 3600
                            score = score / max(age_hours, 1)  # Recency bonus
                        
                        articles.append(FetchedArticle(
                            url=url,
                            title=item.get("title", "[No title]"),
                            content=None,
                            published_at=self._parse_timestamp(str(item.get("created_at_i", ""))),
                            source="hackernews",
                            source_id=item["objectID"],
                            category="ai-general",
                            author=str(item.get("author", "")),
                            score=score
                        ))
                        
            except Exception as e:
                print(f"HN fetch error: {e}")
                
        return sorted(articles, key=lambda x: x.score or 0, reverse=True)


class RedditFetcher(BaseFetcher):
    """Reddit subreddits aggregator using PRAW (async)"""
    
    def __init__(self, name: str = "reddit"):
        super().__init__(name)
        self.subreddits = self.settings.SUBREDDITS
        self.time_filter = "week"  # week/month/year/all
        self.limit = 10
        
    async def fetch(self, limit: int = 10) -> List[FetchedArticle]:
        """Fetch top posts from configured subreddits"""
        if not self.settings.ENABLE_REDDIT or not self.subreddits:
            return []
            
        articles = []
        total_limit = limit // len(self.subreddits) if len(self.subreddits) > 0 else limit
        
        for subreddit_name in self.subreddits[:3]:  # Limit to 3 to reduce API calls
            try:
                from asyncpraw import Reddit
                from asyncprawcore import NotFound, RequestException
                
                reddit = Reddit(
                    client_id=self.settings.REDDIT_CLIENT_ID,
                    client_secret=self.settings.REDDIT_CLIENT_SECRET,
                    user_agent=self.settings.REDDIT_USER_AGENT,
                    username=None,  # Read-only
                    password=None,
                    username_uri="https://oauth.reddit.com"
                )
                
                subreddit = await reddit.subreddit(subreddit_name)
                
                # Get top posts from week
                posts = []
                async for submission in subreddit.top(time_filter=self.time_filter, limit=total_limit):
                    if submission.url and len(posts) < total_limit:
                        posts.append(submission)
                        
                await reddit.close()
                
                for post in posts:
                    # Calculate score with subreddit and upvotes
                    base_score = (post.score / 10) if post.score else 0
                    
                    articles.append(FetchedArticle(
                        url=post.url,
                        title=post.title,
                        content=post.selftext if hasattr(post, 'selftext') else None,
                        published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc) if post.created_utc else None,
                        source="reddit",
                        source_id=post.id,
                        category="ai-general",
                        author=str(post.author) if post.author else None,
                        score=base_score,
                        tags=[subreddit_name]
                    ))
                    
            except ImportError:
                print("Reddit client not installed. Skipping Reddit fetcher.")
                break
            except Exception as e:
                print(f"Reddit fetch error for r/{subreddit_name}: {e}")
                continue
            
        return articles


class ArticleAggregator:
    """Main aggregator that combines all fetchers"""
    
    def __init__(self, *args, **kwargs):
        self.fetchers: list[BaseFetcher] = []
        
    def add_fetcher(self, fetcher: BaseFetcher):
        self.fetchers.append(fetcher)
        
    async def fetch_all(self, limit: int = 30) -> List[FetchedArticle]:
        """Fetch from all registered fetchers"""
        if not self.fetchers:
            return []
            
        tasks = [f.fetch(limit // len(self.fetchers) if self.fetchers else limit) for f in self.fetchers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
            elif isinstance(result, Exception):
                print(f"Fetcher error: {result}")
                
        # Deduplicate by normalized URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            normalized = self._normalize_url(article.url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_articles.append(article)
                
        return sorted(unique_articles, key=lambda x: x.score or 0, reverse=True)[:limit]
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        parsed = urlparse(url.lower())
        path = parsed.path.rstrip('/')
        return f"{parsed.hostname}{path}"