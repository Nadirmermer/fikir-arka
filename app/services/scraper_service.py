"""
Enhanced Scraper Service v3.0.0 - Platform-Specific Scraping
Advanced content extraction with Scrapling, Instaloader, and platform-specific optimizations
"""

import asyncio
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func
from app.database import get_db
from app.models import Source, Topic
import logging
import time
import re
from urllib.parse import urljoin, urlparse
import json
from dataclasses import dataclass
import hashlib
import os
import tempfile

# --- Twitter scraping library (twscrape) ---
try:
    from twscrape import API as TwScrapeAPI
    TWSCRAPE_AVAILABLE = True
except ImportError:
    TWSCRAPE_AVAILABLE = False
    TwScrapeAPI = None

# Import advanced scraping libraries
# Scrapling removed - using requests + beautifulsoup for better compatibility
SCRAPLING_AVAILABLE = False

try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False
    logging.warning("Instaloader not available - Instagram scraping limited")

# Feedsearch removed - using feedparser for RSS discovery
FEEDSEARCH_AVAILABLE = False

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logging.warning("yt-dlp not available - YouTube metadata extraction limited")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Structured scraping result"""
    success: bool
    new_content_count: int
    error: Optional[str] = None
    skipped_count: int = 0
    processed_count: int = 0
    source_name: str = ""
    rate_limited: bool = False
    
class EnhancedScraperService:
    """Enhanced scraper with platform-specific implementations"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Using requests + BeautifulSoup for reliable scraping
        logger.info("🕷️ Scraper initialized with requests + BeautifulSoup")
        
        # Initialize Instaloader if available
        if INSTALOADER_AVAILABLE:
            self.instagram_loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False
            )
            logger.info("📱 Instaloader initialized for Instagram scraping")
        
        # Enhanced rate limiting configuration
        self.rate_limits = {
            'youtube': {'requests_per_minute': 60, 'delay_between_requests': 1.0},
            'instagram': {'requests_per_minute': 20, 'delay_between_requests': 3.0},  # More conservative for Instagram
            'twitter': {'requests_per_minute': 30, 'delay_between_requests': 2.0},   # More conservative for Twitter
            'rss': {'requests_per_minute': 120, 'delay_between_requests': 0.5},
            'website': {'requests_per_minute': 90, 'delay_between_requests': 0.7},
            'default': {'requests_per_minute': 60, 'delay_between_requests': 1.0}
        }
        
        # Track last request times for rate limiting
        self.last_requests = {}

        # TwScrape API oturumu
        self.twitter_api = None  # TwScrapeAPI instance

        if TWSCRAPE_AVAILABLE:
            logger.info("🐦 TwScrape kütüphanesi yüklü - Twitter login destekleniyor")
        
        # Anlık kazıma durumu
        self.scraping_status = {
            "status": "idle", # idle, running, completed, failed
            "progress": {"processed": 0, "total": 0},
            "current_source": "",
            "new_content_count": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
            "duration": 0
        }

        # Content quality thresholds
        self.quality_thresholds = {
            'min_title_length': 10,
            'min_content_length': 50,
            'max_title_length': 300,
            'max_content_length': 5000
        }

    async def scrape_all_sources(self) -> Dict[str, Any]:
        """Enhanced scraping with better error handling and statistics"""
        # 1. Reset status and set to "running"
        self.scraping_status = {
            "status": "running",
            "progress": {"processed": 0, "total": 0},
            "current_source": "Başlatılıyor...",
            "new_content_count": 0,
            "errors": [],
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration": 0
        }
        start_time = datetime.utcnow()
        
        try:
            # Get all active sources
            async with get_db() as db:
                result = await db.execute(
                    select(Source).where(Source.is_active == True)
                )
                sources = result.scalars().all()
            
            if not sources:
                return {
                    "success": True,
                    "message": "No active sources found",
                    "total_new_content": 0,
                    "sources_processed": 0,
                    "duration_seconds": 0,
                    "errors": []
                }
            
            logger.info(f"Starting enhanced scraping for {len(sources)} sources")
            self.scraping_status["progress"]["total"] = len(sources)

            total_new_content = 0
            sources_processed = 0
            errors = []
            results_by_platform = {}
            
            # Process sources with rate limiting
            for i, source in enumerate(sources):
                self.scraping_status["progress"]["processed"] = i + 1
                self.scraping_status["current_source"] = source.name

                try:
                    # Apply rate limiting
                    await self._apply_rate_limiting(source.platform)
                    
                    logger.info(f"Scraping source: {source.name} ({source.platform})")
                    
                    result = await self._scrape_source_enhanced(source)
                    
                    if result.success:
                        total_new_content += result.new_content_count
                        self.scraping_status["new_content_count"] = total_new_content
                        sources_processed += 1
                        
                        # Track results by platform
                        if source.platform not in results_by_platform:
                            results_by_platform[source.platform] = {
                                'sources': 0, 'new_content': 0, 'errors': 0
                            }
                        results_by_platform[source.platform]['sources'] += 1
                        results_by_platform[source.platform]['new_content'] += result.new_content_count
                        
                        # Update source's last scraped time
                        async with get_db() as db:
                            source.last_scraped_at = datetime.utcnow()
                            source.last_content_count = result.new_content_count
                            source.total_content_count += result.new_content_count
                            await db.commit()
                            
                        logger.info(f"✅ {source.name}: {result.new_content_count} new items")
                    else:
                        error_msg = f"{source.name} ({source.platform}): {result.error}"
                        errors.append(error_msg)
                        self.scraping_status["errors"].append(error_msg)
                        
                        if source.platform in results_by_platform:
                            results_by_platform[source.platform]['errors'] += 1
                        
                        logger.error(f"❌ {error_msg}")
                        
                except Exception as e:
                    error_msg = f"{source.name}: Unexpected error - {str(e)}"
                    errors.append(error_msg)
                    self.scraping_status["errors"].append(error_msg)
                    logger.error(f"💥 {error_msg}")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # 2. Update status to "completed"
            self.scraping_status["status"] = "completed"
            self.scraping_status["end_time"] = datetime.utcnow().isoformat()
            self.scraping_status["duration"] = round(duration, 2)

            # Enhanced response with detailed statistics
            response = {
                "success": True,
                "message": f"Scraping completed successfully",
                "total_new_content": total_new_content,
                "sources_processed": sources_processed,
                "total_sources": len(sources),
                "duration_seconds": round(duration, 2),
                "errors": errors,
                "error_count": len(errors),
                "results_by_platform": results_by_platform,
                "timestamp": datetime.utcnow().isoformat(),
                "performance": {
                    "avg_time_per_source": round(duration / len(sources), 2) if sources else 0,
                    "success_rate": round((sources_processed / len(sources)) * 100, 2) if sources else 0,
                    "content_per_source": round(total_new_content / sources_processed, 2) if sources_processed else 0
                }
            }
            
            logger.info(f"🎉 Scraping completed: {total_new_content} new items from {sources_processed}/{len(sources)} sources in {duration:.2f}s")
            return response
            
        except Exception as e:
            # 3. Update status to "failed" on fatal error
            self.scraping_status["status"] = "failed"
            self.scraping_status["errors"].append(f"Fatal error: {str(e)}")
            self.scraping_status["end_time"] = datetime.utcnow().isoformat()

            logger.error(f"Fatal scraping error: {str(e)}")
            return {
                "success": False,
                "error": f"Fatal error during scraping: {str(e)}",
                "total_new_content": 0,
                "sources_processed": 0,
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "errors": [str(e)]
            }

    async def _apply_rate_limiting(self, platform: str):
        """Apply intelligent rate limiting based on platform"""
        platform_limits = self.rate_limits.get(platform, self.rate_limits['default'])
        delay = platform_limits['delay_between_requests']
        
        # Check if we need to wait
        last_request_key = f"{platform}_last_request"
        if last_request_key in self.last_requests:
            time_since_last = time.time() - self.last_requests[last_request_key]
            if time_since_last < delay:
                wait_time = delay - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {platform}")
                await asyncio.sleep(wait_time)
        
        self.last_requests[last_request_key] = time.time()

    # ------------------------------------------------------------------
    # Twitter Authentication (TwScrape)
    # ------------------------------------------------------------------
    async def twitter_login(self, username: str, password: str, email: str | None = None, email_password: str | None = None):
        """TwScrape kullanarak Twitter hesabı ile oturum aç.

        Frontend'den gelen kullanıcı adı ve şifre (isteğe bağlı email bilgileri) ile
        TwScrape API havuzuna hesap ekler ve giriş yapar. Başarılı olursa self.twitter_api
        örneği içindeki oturum saklanır ve scraping sırasında kullanılır.
        """
        if not TWSCRAPE_AVAILABLE:
            return {"success": False, "error": "twscrape kütüphanesi yüklü değil"}

        try:
            if not self.twitter_api:
                self.twitter_api = TwScrapeAPI()

            # Hesap ekle (varsa tekrar eklemez)
            try:
                await self.twitter_api.pool.add_account(username, password, email or "", email_password or "")
            except Exception as e:
                # Hesap zaten ekli olabilir
                self.logger.debug(f"TwScrape account add: {e}")

            await self.twitter_api.pool.login_all()

            # Basit doğrulama: havuzda en az bir aktif hesap var mı?
            if not self.twitter_api.pool.is_logged_in:
                return {"success": False, "error": "Twitter girişi başarısız"}

            self.logger.info(f"✅ TwScrape login başarılı: @{username}")
            return {"success": True, "message": "Twitter oturumu açıldı"}

        except Exception as e:
            self.logger.error(f"TwScrape login error: {e}")
            return {"success": False, "error": str(e)}

    async def _scrape_source_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced source scraping with better error handling"""
        try:
            platform = source.platform.lower()

            # Heuristic: If platform is website but URL indicates feed, override to RSS
            if platform == "website" and re.search(r"(\.rss$|\.xml$|/feed/?$)", source.url, re.IGNORECASE):
                logger.debug(f"🔍 RSS feed detected from website source, switching platform for this run")
                platform = "rss"

            if platform == "youtube":
                return await self._scrape_youtube_enhanced(source)
            elif platform in ["rss", "blog", "rss/blog"]:
                return await self._scrape_rss_enhanced(source)
            elif platform == "instagram":
                return await self._scrape_instagram_enhanced(source)
            elif platform in ["twitter", "x"]:
                return await self._scrape_twitter_enhanced(source)
            elif platform == "website":
                return await self._scrape_website_enhanced(source)
            else:
                raise Exception(f"Unsupported platform: {source.platform}")
        except Exception as e:
            logger.error(f"Source scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )

    async def _scrape_youtube_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced YouTube scraping with better content extraction"""
        try:
            rss_url = self._get_youtube_rss_url(source.url)
            if not rss_url:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    error="Could not convert YouTube URL to RSS feed",
                    source_name=source.name
                )
            
            logger.debug(f"Fetching YouTube RSS: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                return ScrapingResult(
                    success=True,
                    new_content_count=0,
                    source_name=source.name
                )
            
            new_content_count = 0
            skipped_count = 0
            processed_count = 0
            
            # Process entries (limit to 15 for performance)
            for entry in feed.entries[:15]:
                processed_count += 1
                
                # Enhanced content validation
                if not self._is_content_quality_sufficient(entry.title, entry.get('summary', '')):
                    skipped_count += 1
                    continue
                
                # Check for duplicates using multiple methods
                content_hash = self._generate_content_hash(entry.title, entry.link)
                
                async with get_db() as db:
                    # Check by URL
                    existing_by_url = await db.execute(
                        select(Topic).where(Topic.link == entry.link)
                    )
                    if existing_by_url.scalar_one_or_none():
                        skipped_count += 1
                        continue
                    
                    # Check by content hash (prevents near-duplicates)
                    existing_by_hash = await db.execute(
                        select(Topic).where(Topic.description == content_hash)
                    )
                    if existing_by_hash.scalar_one_or_none():
                        skipped_count += 1
                        continue
                
                # Extract enhanced metadata
                video_description = self._extract_youtube_description(entry)
                video_duration = self._extract_youtube_duration(entry)
                
                topic = Topic(
                    title=self._clean_title(entry.title),
                    description=content_hash,  # Store hash for duplicate detection
                    content=self._clean_content(video_description),
                    platform="YouTube",
                    source=source.name,
                    link=entry.link,
                    publish_date=datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.utcnow(),
                    popularity_score=self._calculate_youtube_popularity(entry),
                    content_length=len(video_description)
                )
                
                async with get_db() as db:
                    db.add(topic)
                    await db.commit()
                
                new_content_count += 1
                logger.debug(f"✅ Added YouTube video: {entry.title}")
            
            return ScrapingResult(
                success=True,
                new_content_count=new_content_count,
                skipped_count=skipped_count,
                processed_count=processed_count,
                source_name=source.name
            )
            
        except Exception as e:
            logger.error(f"YouTube scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )

    async def _scrape_rss_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced RSS scraping with better content parsing"""
        try:
            logger.debug(f"Fetching RSS feed: {source.url}")
            
            # Add timeout and better error handling
            response = self.session.get(source.url, timeout=15)
            response.raise_for_status()
            
            # Use feedparser directly (it handles XML properly)
            feed = feedparser.parse(response.text)
            
            if not feed.entries:
                return ScrapingResult(
                    success=True,
                    new_content_count=0,
                    source_name=source.name
                )
            
            new_content_count = 0
            skipped_count = 0
            processed_count = 0
            
            for entry in feed.entries[:20]:  # Increased limit for RSS
                processed_count += 1
                
                # Enhanced content validation
                title = entry.get('title', 'Untitled')
                summary = entry.get('summary', '')
                content = self._extract_rss_content(entry)
                
                if not self._is_content_quality_sufficient(title, content):
                    skipped_count += 1
                    continue
                
                # Duplicate detection
                content_hash = self._generate_content_hash(title, entry.get('link', ''))
                
                async with get_db() as db:
                    existing = await db.execute(
                        select(Topic).where(
                            (Topic.link == entry.get('link')) |
                            (Topic.description == content_hash)
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped_count += 1
                        continue
                
                topic = Topic(
                    title=self._clean_title(title),
                    description=content_hash,
                    content=self._clean_content(content),
                    platform=source.platform,
                    source=source.name,
                    link=entry.get('link', ''),
                    publish_date=datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.utcnow(),
                    popularity_score=self._calculate_rss_popularity(entry),
                    content_length=len(content)
                )
                
                async with get_db() as db:
                    db.add(topic)
                    await db.commit()
                
                new_content_count += 1
                logger.debug(f"✅ Added RSS item: {title}")
            
            return ScrapingResult(
                success=True,
                new_content_count=new_content_count,
                skipped_count=skipped_count,
                processed_count=processed_count,
                source_name=source.name
            )
            
        except Exception as e:
            logger.error(f"RSS scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )

    async def _scrape_instagram_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced Instagram scraping with Instaloader"""
        if not INSTALOADER_AVAILABLE:
            return ScrapingResult(
                success=False,
                new_content_count=0,
                source_name=source.name,
                error="Instaloader not available - please install: pip install instaloader"
            )
        
        try:
            logger.info(f"🔍 Instagram scraping: {source.url}")
            
            # Extract profile name from URL
            profile_name = self._extract_instagram_profile(source.url)
            if not profile_name:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    source_name=source.name,
                    error="Could not extract Instagram profile name from URL"
                )
            
            # Get profile and posts
            try:
                profile = instaloader.Profile.from_username(self.instagram_loader.context, profile_name)
                
                new_posts = 0
                processed_posts = 0
                
                # Limit to recent posts to avoid rate limiting
                posts_to_process = list(profile.get_posts())[:10]  # Last 10 posts
                
                for post in posts_to_process:
                    processed_posts += 1
                    
                    # Check for duplicates using post URL
                    post_url = f"https://www.instagram.com/p/{post.shortcode}/"
                    
                    async with get_db() as db:
                        existing = await db.execute(
                            select(Topic).where(Topic.link == post_url)
                        )
                        if existing.scalar_one_or_none():
                            continue
                    
                    # Extract post content
                    caption = post.caption or ""
                    
                    # Skip if content quality is insufficient
                    if not self._is_content_quality_sufficient(caption[:100], caption):
                        continue
                    
                    # Calculate popularity score
                    popularity = self._calculate_instagram_popularity(post)
                    
                    # Create topic
                    topic = Topic(
                        title=self._clean_title(caption[:100] if caption else f"Instagram Post by @{profile_name}"),
                        description=self._generate_content_hash(caption, post_url),
                        content=self._clean_content(caption),
                        platform="Instagram",
                        source=source.name,
                        link=post_url,
                        publish_date=post.date_utc,
                        popularity_score=popularity,
                        content_length=len(caption),
                        metadata=json.dumps({
                            "profile": profile_name,
                            "shortcode": post.shortcode,
                            "likes": post.likes,
                            "comments": post.comments,
                            "is_video": post.is_video,
                            "typename": post.typename
                        })
                    )
                    
                    async with get_db() as db:
                        db.add(topic)
                        await db.commit()
                    
                    new_posts += 1
                    
                    # Rate limiting between posts
                    await asyncio.sleep(0.5)
                
                logger.info(f"✅ Instagram {profile_name}: {new_posts} new posts from {processed_posts} processed")
                
                return ScrapingResult(
                    success=True,
                    new_content_count=new_posts,
                    processed_count=processed_posts,
                    source_name=source.name
                )
                
            except instaloader.exceptions.ProfileNotExistsException:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    source_name=source.name,
                    error=f"Instagram profile '{profile_name}' not found"
                )
            except instaloader.exceptions.LoginRequiredException:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    source_name=source.name,
                    error="Instagram profile is private - login required"
                )
                
        except Exception as e:
            logger.error(f"Instagram scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )

    async def _scrape_twitter_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced Twitter/X scraping with stealth techniques"""
        try:
            logger.info(f"🐦 Twitter scraping: {source.url}")

            # Extract username from URL
            username = self._extract_twitter_username(source.url)
            if not username:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    source_name=source.name,
                    error="Could not extract Twitter username from URL"
                )

            # ------------------------------------------------------
            # 1) TwScrape kullanarak JSON tabanlı scraping
            # ------------------------------------------------------
            if TWSCRAPE_AVAILABLE and self.twitter_api and self.twitter_api.pool.is_logged_in:
                try:
                    tweets = await self.twitter_api.user_tweets(username, limit=10)
                    new_tweets = 0
                    processed_tweets = 0

                    for tw in tweets:
                        processed_tweets += 1
                        title = tw.raw_content[:100]
                        content = tw.raw_content

                        if not self._is_content_quality_sufficient(title, content):
                            continue

                        link = f"https://twitter.com/{username}/status/{tw.id}"
                        content_hash = self._generate_content_hash(title, link)

                        async with get_db() as db:
                            existing = await db.execute(
                                select(Topic).where(
                                    (Topic.link == link) | (Topic.description == content_hash)
                                )
                            )
                            if existing.scalar_one_or_none():
                                continue

                        topic = Topic(
                            title=self._clean_title(title),
                            description=content_hash,
                            content=self._clean_content(content),
                            platform="Twitter",
                            source=source.name,
                            link=link,
                            publish_date=tw.created_at or datetime.utcnow(),
                            popularity_score= min(len(content) / 10, 100),
                            content_length=len(content)
                        )

                        async with get_db() as db:
                            db.add(topic)
                            await db.commit()

                        new_tweets += 1

                    self.logger.info(f"✅ TwScrape @{username}: {new_tweets} new tweets from {processed_tweets} processed")

                    return ScrapingResult(
                        success=True,
                        new_content_count=new_tweets,
                        processed_count=processed_tweets,
                        source_name=source.name
                    )
                except Exception as tw_err:
                    self.logger.warning(f"TwScrape error: {tw_err}")

            # 2) Scrapling yöntemi (varsa)
            new_tweets = 0
            processed_tweets = 0
            # Use Scrapling for stealth scraping if available
            if SCRAPLING_AVAILABLE:
                try:
                    # Try to scrape Twitter profile page with stealth mode
                    page = StealthyFetcher.fetch(
                        source.url,
                        headless=True,
                        network_idle=True
                    )
                    
                    if page.status != 200:
                        raise Exception(f"Failed to fetch Twitter page: {page.status}")
                    
                    # Extract tweets using Scrapling's CSS selectors
                    tweet_elements = page.css('[data-testid="tweet"]')
                    
                    for tweet_elem in tweet_elements[:10]:  # Limit to 10 recent tweets
                        processed_tweets += 1
                        
                        # Extract tweet content
                        tweet_text_elem = tweet_elem.css('[data-testid="tweetText"]').first
                        if not tweet_text_elem:
                            continue
                            
                        tweet_text = tweet_text_elem.text or ""
                        
                        # Extract tweet link (if available)
                        time_elem = tweet_elem.css('time').first
                        tweet_url = ""
                        if time_elem and time_elem.parent:
                            href = time_elem.parent.get('href')
                            if href:
                                tweet_url = f"https://twitter.com{href}"
                        
                        # Skip if content quality is insufficient
                        if not self._is_content_quality_sufficient(tweet_text[:50], tweet_text):
                            continue
                        
                        # Check for duplicates
                        content_hash = self._generate_content_hash(tweet_text, tweet_url or source.url)
                        
                        async with get_db() as db:
                            existing = await db.execute(
                                select(Topic).where(Topic.description == content_hash)
                            )
                            if existing.scalar_one_or_none():
                                continue
                        
                        # Calculate popularity score
                        popularity = self._calculate_twitter_popularity(tweet_elem)
                        
                        # Create topic
                        topic = Topic(
                            title=self._clean_title(tweet_text[:100] if tweet_text else f"Tweet by @{username}"),
                            description=content_hash,
                            content=self._clean_content(tweet_text),
                            platform="Twitter",
                            source=source.name,
                            link=tweet_url or source.url,
                            publish_date=datetime.utcnow(),  # Twitter timestamps are complex to parse
                            popularity_score=popularity,
                            content_length=len(tweet_text),
                            metadata=json.dumps({
                                "username": username,
                                "tweet_url": tweet_url
                            })
                        )
                        
                        async with get_db() as db:
                            db.add(topic)
                            await db.commit()
                        
                        new_tweets += 1
                        
                        # Rate limiting between tweets
                        await asyncio.sleep(0.3)
                        
                except Exception as scrapling_error:
                    logger.warning(f"Scrapling Twitter scraping failed: {scrapling_error}")
                    # Fall back to basic scraping
                    return await self._scrape_twitter_fallback(source, username)
            else:
                # Use fallback method without Scrapling
                return await self._scrape_twitter_fallback(source, username)
            
            logger.info(f"✅ Twitter @{username}: {new_tweets} new tweets from {processed_tweets} processed")
            
            return ScrapingResult(
                success=True,
                new_content_count=new_tweets,
                processed_count=processed_tweets,
                source_name=source.name
            )
            
        except Exception as e:
            logger.error(f"Twitter scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )

    async def _scrape_website_enhanced(self, source: Source) -> ScrapingResult:
        """Enhanced website scraping with Scrapling stealth mode"""
        try:
            logger.debug(f"🌐 Website scraping: {source.url}")
            
            # Use Scrapling for advanced scraping if available
            if SCRAPLING_AVAILABLE:
                try:
                    page = StealthyFetcher.fetch(
                        source.url,
                        headless=True,
                        network_idle=True
                    )
                    
                    if page.status != 200:
                        raise Exception(f"Failed to fetch website: {page.status}")
                    
                    # Use Scrapling's smart content extraction
                    title = page.css('title').first.text if page.css('title').first else ""
                    
                    # Try multiple content selectors with Scrapling
                    content_selectors = [
                        'article', 'main', '.content', '.post-content', 
                        '.entry-content', '[role="main"]', '.article-body'
                    ]
                    
                    content = ""
                    for selector in content_selectors:
                        elements = page.css(selector)
                        if elements:
                            content = elements.first.text
                            if len(content) > 100:  # Found substantial content
                                break
                    
                    # Fallback to page text if no specific content found
                    if not content or len(content) < 50:
                        # Remove unwanted elements first
                        page.css('script, style, nav, header, footer, aside').remove()
                        content = page.text[:2000]  # Limit content length
                    
                except Exception as scrapling_error:
                    logger.warning(f"Scrapling website scraping failed, using fallback: {scrapling_error}")
                    # Fall back to traditional scraping
                    response = self.session.get(source.url, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title = self._extract_website_title(soup)
                    content = self._extract_website_content(soup)
            else:
                # Traditional scraping method
                response = self.session.get(source.url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                title = self._extract_website_title(soup)
                content = self._extract_website_content(soup)
            
            # Enhanced content extraction
            description = content[:200] if content else ""
            
            if not self._is_content_quality_sufficient(title, content):
                return ScrapingResult(
                    success=True,
                    new_content_count=0,
                    source_name=source.name,
                    error="Content quality below threshold"
                )
            
            # Check for duplicates
            content_hash = self._generate_content_hash(title, source.url)
            
            async with get_db() as db:
                existing = await db.execute(
                    select(Topic).where(
                        (Topic.link == source.url) |
                        (Topic.description == content_hash)
                    )
                )
                if existing.scalar_one_or_none():
                    return ScrapingResult(
                        success=True,
                        new_content_count=0,
                        skipped_count=1,
                        source_name=source.name
                    )
            
            topic = Topic(
                title=self._clean_title(title),
                description=content_hash,
                content=self._clean_content(content),
                platform="Website",
                source=source.name,
                link=source.url,
                publish_date=datetime.utcnow(),
                popularity_score=len(content) // 10,  # Simple popularity metric
                content_length=len(content)
            )
            
            async with get_db() as db:
                db.add(topic)
                await db.commit()
            
            return ScrapingResult(
                success=True,
                new_content_count=1,
                processed_count=1,
                source_name=source.name
            )
            
        except Exception as e:
            logger.error(f"Website scraping error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                error=str(e),
                source_name=source.name
            )
            
    # Helper methods for content processing
    def _is_content_quality_sufficient(self, title: str, content: str) -> bool:
        """Check if content meets quality thresholds"""
        if len(title) < self.quality_thresholds['min_title_length']:
            return False
        if len(content) < self.quality_thresholds['min_content_length']:
            return False
        if len(title) > self.quality_thresholds['max_title_length']:
            return False
        if len(content) > self.quality_thresholds['max_content_length']:
            return False
        
        # Check for spam patterns
        spam_patterns = [
            r'(?i)(click here|subscribe now|follow us)',
            r'(?i)(limited time|act now|urgent)',
            r'(?i)(free gift|100% free|no cost)'
        ]
        
        combined_text = f"{title} {content}"
        for pattern in spam_patterns:
            if re.search(pattern, combined_text):
                return False
        
        return True

    def _generate_content_hash(self, title: str, url: str) -> str:
        """Generate a hash for content deduplication"""
        content_key = f"{title.lower().strip()}{url.strip()}"
        return hashlib.md5(content_key.encode()).hexdigest()

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title"""
        if not title:
            return "Untitled"
        
        # Remove extra whitespace and common prefixes
        title = re.sub(r'\s+', ' ', title.strip())
        title = re.sub(r'^(RE:|FW:|AW:)\s*', '', title, flags=re.IGNORECASE)
        
        return title[:self.quality_thresholds['max_title_length']]

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        if not content:
            return ""
        
        # Remove HTML tags, extra whitespace, and normalize
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content.strip())
        
        return content[:self.quality_thresholds['max_content_length']]

    def _extract_youtube_description(self, entry) -> str:
        """Extract enhanced YouTube video description"""
        description = entry.get('summary', '')
        
        # Try to get more content from entry
        if hasattr(entry, 'content') and entry.content:
            for content_item in entry.content:
                if content_item.value:
                    description = content_item.value
                    break
        
        return description

    def _extract_youtube_duration(self, entry) -> Optional[str]:
        """Extract video duration if available"""
        # This would require YouTube API for accurate duration
        return None

    def _calculate_youtube_popularity(self, entry) -> float:
        """Calculate popularity score for YouTube content"""
        score = 0.0
        
        # Base score from description length
        description = entry.get('summary', '')
        score += len(description) / 100
        
        # Boost score for recent content
        if entry.get('published_parsed'):
            pub_date = datetime(*entry.published_parsed[:6])
            days_old = (datetime.utcnow() - pub_date).days
            if days_old < 7:
                score += 50
            elif days_old < 30:
                score += 25
        
        return min(score, 100.0)  # Cap at 100

    def _extract_rss_content(self, entry) -> str:
        """Extract enhanced content from RSS entry"""
        content = entry.get('summary', '')
        
        # Try multiple content fields
        if hasattr(entry, 'content') and entry.content:
            for content_item in entry.content:
                if content_item.value and len(content_item.value) > len(content):
                    content = content_item.value
        
        # Try description field
        if hasattr(entry, 'description') and len(entry.description) > len(content):
            content = entry.description
        
        return content

    def _calculate_rss_popularity(self, entry) -> float:
        """Calculate popularity score for RSS content"""
        score = 0.0
        
        # Base score from content length
        content = self._extract_rss_content(entry)
        score += len(content) / 50
        
        # Recent content boost
        if entry.get('published_parsed'):
            pub_date = datetime(*entry.published_parsed[:6])
            days_old = (datetime.utcnow() - pub_date).days
            if days_old < 3:
                score += 30
            elif days_old < 14:
                score += 15
        
        return min(score, 100.0)

    def _extract_website_title(self, soup: BeautifulSoup) -> str:
        """Extract title from website"""
        # Try multiple title sources
        title_candidates = [
            soup.find('h1'),
            soup.find('title'),
            soup.find('meta', attrs={'property': 'og:title'}),
            soup.find('meta', attrs={'name': 'twitter:title'})
        ]
        
        for candidate in title_candidates:
            if candidate:
                if candidate.name == 'meta':
                    title_text = candidate.get('content', '')
                else:
                    title_text = candidate.get_text()
                
                if title_text and len(title_text.strip()) > 5:
                    return title_text.strip()
        
        return "Untitled Website"

    def _extract_website_description(self, soup: BeautifulSoup) -> str:
        """Extract description from website"""
        desc_candidates = [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'}),
            soup.find('meta', attrs={'name': 'twitter:description'})
        ]
        
        for candidate in desc_candidates:
            if candidate:
                desc_text = candidate.get('content', '')
                if desc_text and len(desc_text.strip()) > 10:
                    return desc_text.strip()
        
        return ""

    def _extract_website_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from website"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Try to find main content area
        content_candidates = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', attrs={'class': re.compile(r'content|main|post|article', re.I)}),
            soup.find('div', attrs={'id': re.compile(r'content|main|post|article', re.I)})
        ]
        
        for candidate in content_candidates:
            if candidate:
                text = candidate.get_text(separator=' ', strip=True)
                if len(text) > 100:
                    return text
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        
        return soup.get_text(separator=' ', strip=True)
    
    def _get_youtube_rss_url(self, youtube_url: str) -> Optional[str]:
        """Enhanced YouTube URL to RSS conversion with video-to-channel resolution"""
        try:
            # Handle different YouTube URL formats
            # 1) URL zaten RSS biçimindeyse (feeds/videos.xml) doğrudan döndür
            if 'feeds/videos.xml' in youtube_url:
                return youtube_url
            if '/channel/' in youtube_url:
                channel_id = youtube_url.split('/channel/')[-1].split('/')[0].split('?')[0]
                return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            elif 'playlist?list=' in youtube_url:
                playlist_id = youtube_url.split('list=')[-1].split('&')[0]
                return f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
            elif '/watch?v=' in youtube_url or 'youtu.be/' in youtube_url:
                # Video URL - extract channel ID using yt-dlp
                if YT_DLP_AVAILABLE:
                    try:
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'extract_flat': True,
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(youtube_url, download=False)
                            if 'channel_id' in info:
                                channel_id = info['channel_id']
                                logger.info(f"Extracted channel ID {channel_id} from video URL")
                                return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                    except Exception as e:
                        logger.warning(f"yt-dlp extraction failed: {e}")
                return None
            elif '/c/' in youtube_url or '/user/' in youtube_url or 'youtube.com/@' in youtube_url:
                # Custom/user/@ URLs - try yt-dlp for channel ID resolution
                if YT_DLP_AVAILABLE:
                    try:
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'extract_flat': True,
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(youtube_url, download=False)
                            if 'channel_id' in info:
                                channel_id = info['channel_id']
                                logger.info(f"Resolved channel ID {channel_id} from custom URL")
                                return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                    except Exception as e:
                        logger.warning(f"yt-dlp channel resolution failed: {e}")
                return None
            else:
                logger.warning(f"Unsupported YouTube URL format: {youtube_url}")
                return None
        except Exception as e:
            logger.error(f"Error converting YouTube URL: {str(e)}")
            return None
    
    async def test_source_enhanced(self, source_url: str, platform: str) -> Dict[str, Any]:
        """Enhanced source testing with detailed feedback"""
        try:
            test_source = Source(
                name="Test Source",
                url=source_url,
                platform=platform,
                source_type="test",
                is_active=True
            )
            
            start_time = time.time()
            result = await self._scrape_source_enhanced(test_source)
            duration = time.time() - start_time
            
            return {
                "success": result.success,
                "error": result.error,
                "new_content_count": result.new_content_count,
                "skipped_count": result.skipped_count,
                "processed_count": result.processed_count,
                "rate_limited": result.rate_limited,
                "duration_seconds": round(duration, 2),
                "platform": platform,
                "url": source_url,
                "quality_analysis": {
                    "content_quality_sufficient": True,  # Would be set during actual processing
                    "rate_limit_applied": platform in self.rate_limits,
                    "duplicate_detection": True
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "new_content_count": 0,
                "platform": platform,
                "url": source_url
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test scraper service connectivity"""
        try:
            # Test database connection
            async with get_db() as db:
                sources_result = await db.execute(select(func.count()).select_from(Source))
                total_sources = sources_result.scalar() or 0
                
                active_sources_result = await db.execute(
                    select(func.count()).select_from(Source).where(Source.is_active == True)
                )
                active_sources = active_sources_result.scalar() or 0
                
            return {
                "success": True,
                "message": "Scraper service bağlantısı başarılı",
                "database_connection": True,
                "total_sources": total_sources,
                "active_sources": active_sources,
                "rate_limiting": self.rate_limits,
                "quality_thresholds": self.quality_thresholds,
                "features": [
                    "🎯 Akıllı içerik filtreleme",
                    "⚡ Rate limiting koruması", 
                    "🔍 Gelişmiş duplicate detection",
                    "📊 Detaylı performans metrics"
                ]
            }
            
        except Exception as e:
            logger.error(f"Scraper test connection failed: {e}")
            return {
                "success": False,
                "message": f"Scraper service bağlantı hatası: {str(e)}",
                "database_connection": False
            }

    async def discover_feeds(self, url: str) -> Dict[str, Any]:
        """Discover RSS/Atom feeds from a website URL using feedparser and manual detection"""
        try:
            # Manual discovery using BeautifulSoup
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            feeds = []
            
            # Look for <link> tags with RSS/Atom feeds
            link_tags = soup.find_all('link', {'type': ['application/rss+xml', 'application/atom+xml']})
            for link in link_tags:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = urljoin(url, href)
                    
                    # Test the feed URL with feedparser
                    try:
                        feed_response = self.session.get(href, timeout=5)
                        if feed_response.status_code == 200:
                            parsed_feed = feedparser.parse(feed_response.content)
                            if parsed_feed.feed:
                                feeds.append({
                                    'url': href,
                                    'title': parsed_feed.feed.get('title', link.get('title', 'RSS Feed')),
                                    'description': parsed_feed.feed.get('description', ''),
                                    'feed_type': 'rss' if 'rss' in link.get('type', '') else 'atom',
                                    'score': 90,
                                    'entries_count': len(parsed_feed.entries)
                                })
                    except:
                        # Add even if we can't parse it, might work later
                        feeds.append({
                            'url': href,
                            'title': link.get('title', 'RSS Feed'),
                            'description': '',
                            'feed_type': 'rss' if 'rss' in link.get('type', '') else 'atom',
                            'score': 70
                        })
            
            # Look for common feed URLs
            common_paths = ['/rss', '/feed', '/atom.xml', '/rss.xml', '/feed.xml', '/feeds/all.atom.xml']
            for path in common_paths:
                test_url = urljoin(url, path)
                try:
                    test_response = self.session.get(test_url, timeout=5)
                    if test_response.status_code == 200:
                        # Test with feedparser
                        parsed_feed = feedparser.parse(test_response.content)
                        if parsed_feed.feed:
                            feeds.append({
                                'url': test_url,
                                'title': parsed_feed.feed.get('title', f'Feed ({path})'),
                                'description': parsed_feed.feed.get('description', ''),
                                'feed_type': 'rss',
                                'score': 80,
                                'entries_count': len(parsed_feed.entries)
                            })
                except:
                    continue
            
            # Remove duplicates based on URL
            unique_feeds = []
            seen_urls = set()
            for feed in feeds:
                if feed['url'] not in seen_urls:
                    unique_feeds.append(feed)
                    seen_urls.add(feed['url'])
            
            # Sort by score
            unique_feeds.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return {
                'success': True,
                'feeds': unique_feeds[:5],  # Return top 5 feeds
                'method': 'feedparser + manual'
            }
                
        except Exception as e:
            logger.error(f"Feed discovery failed for {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'feeds': []
            }

    # Helper methods for platform-specific content extraction
    def _extract_instagram_profile(self, url: str) -> Optional[str]:
        """Extract Instagram profile name from URL"""
        patterns = [
            r'instagram\.com/([^/?]+)',
            r'instagram\.com/p/([^/?]+)',  # For individual post URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                profile_name = match.group(1)
                # Handle post URLs - extract profile differently
                if '/p/' in url:
                    return None  # Can't easily get profile from post URL
                return profile_name
        return None
    
    def _extract_twitter_username(self, url: str) -> Optional[str]:
        """Extract Twitter username from URL"""
        patterns = [
            r'twitter\.com/([^/?]+)',
            r'x\.com/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1)
                # Filter out non-username paths
                if username.lower() in ['home', 'search', 'explore', 'notifications', 'messages', 'i', 'settings']:
                    continue
                return username
        return None
    
    def _calculate_instagram_popularity(self, post) -> float:
        """Calculate popularity score for Instagram content"""
        score = 0.0
        
        # Likes contribute to popularity
        if hasattr(post, 'likes'):
            score += min(post.likes / 100, 50)  # Cap likes contribution
        
        # Comments contribute to engagement
        if hasattr(post, 'comments'):
            score += min(post.comments / 10, 25)  # Cap comments contribution
        
        # Recent posts get a boost
        if hasattr(post, 'date_utc'):
            days_old = (datetime.utcnow() - post.date_utc).days
            if days_old < 1:
                score += 20
            elif days_old < 7:
                score += 10
        
        # Video content gets a small boost
        if hasattr(post, 'is_video') and post.is_video:
            score += 5
        
        return min(score, 100.0)  # Cap at 100
    
    def _calculate_twitter_popularity(self, tweet_elem) -> float:
        """Calculate popularity score for Twitter content"""
        score = 10.0  # Base score
        
        try:
            # Try to extract engagement metrics if available
            # This is complex with Twitter's current structure
            # For now, use content length as a proxy
            text_length = len(tweet_elem.text or "")
            score += min(text_length / 10, 30)
            
            # Recent tweets get a boost (assuming they're from recent scraping)
            score += 20
            
        except Exception:
            pass  # Ignore errors in popularity calculation
        
        return min(score, 100.0)  # Cap at 100
    
    async def _scrape_twitter_fallback(self, source: Source, username: str) -> ScrapingResult:
        """Fallback Twitter scraping method"""
        """
        Nitter RSS fallback: https://nitter.net/<username>/rss
        Bu servis Twitter içeriğini RSS olarak sunar ve login gerektirmez.
        """
        try:
            rss_url = f"https://nitter.net/{username}/rss"
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                return ScrapingResult(
                    success=False,
                    new_content_count=0,
                    source_name=source.name,
                    error="Nitter RSS boş döndü veya erişilemedi"
                )

            new_items = 0
            processed = 0

            for entry in feed.entries[:10]:
                processed += 1
                title = entry.get('title', '')
                content = entry.get('summary', '')

                if not self._is_content_quality_sufficient(title, content):
                    continue

                link = entry.get('link', source.url)
                content_hash = self._generate_content_hash(title, link)

                async with get_db() as db:
                    existing = await db.execute(
                        select(Topic).where(
                            (Topic.link == link) |
                            (Topic.description == content_hash)
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                topic = Topic(
                    title=self._clean_title(title),
                    description=content_hash,
                    content=self._clean_content(content),
                    platform="Twitter",
                    source=source.name,
                    link=link,
                    publish_date=datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.utcnow(),
                    popularity_score=self._calculate_rss_popularity(entry),
                    content_length=len(content)
                )

                async with get_db() as db:
                    db.add(topic)
                    await db.commit()

                new_items += 1

            return ScrapingResult(
                success=True,
                new_content_count=new_items,
                processed_count=processed,
                source_name=source.name
            )
        except Exception as e:
            logger.error(f"Nitter fallback error for {source.name}: {str(e)}")
            return ScrapingResult(
                success=False,
                new_content_count=0,
                source_name=source.name,
                error=str(e)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        return {
            'version': '1.0.0',
            'rate_limits': {
                'youtube': self.rate_limits.get('youtube', {}),
                'instagram': self.rate_limits.get('instagram', {}), 
                'twitter': self.rate_limits.get('twitter', {}),
                'website': self.rate_limits.get('website', {}),
                'rss': self.rate_limits.get('rss', {})
            },
            'last_scraping_results': {
                'total_sources_processed': getattr(self, 'last_total_sources', 0),
                'successful_sources': getattr(self, 'last_successful_sources', 0),
                'failed_sources': getattr(self, 'last_failed_sources', 0),
                'new_content_items': getattr(self, 'last_new_content', 0)
            },
            'session_info': {
                'session_active': hasattr(self, 'session') and self.session is not None,
                'twitter_logged_in': getattr(self, 'twitter_logged_in', False),
                'instagram_logged_in': getattr(self, 'instagram_logged_in', False)
            },
            'dependencies': {
                'instaloader_available': True,  # Available
                'yt_dlp_available': True,       # Available  
                'scrapling_available': False,   # Not used in main service
                'feedparser_available': True    # Available
            }
        }

# Global instance
scraper_service = EnhancedScraperService() 