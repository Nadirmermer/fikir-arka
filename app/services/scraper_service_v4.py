"""
Enhanced Content Scraper Service v4.0.0
Fixes all major scraping issues:
- Instagram: Multiple fallback methods
- Twitter: Async compatibility fixes  
- Website: BeautifulSoup conflict resolution
- Scrapling: Parameter fixes
"""

import asyncio
import logging
import re
import time
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse, urljoin
import hashlib

import requests
from bs4 import BeautifulSoup, Tag
import feedparser

# Conditional imports with availability flags
try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False
    instaloader = None

try:
    from scrapling import Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    Fetcher = None


class ScraperServiceV4:
    """Enhanced scraper service with comprehensive error handling and fallbacks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.version = "4.0.0"
        
        # Rate limiting settings
        self.rate_limits = {
            'instagram': 3.0,  # seconds between requests
            'twitter': 2.5,    # seconds between requests
            'website': 1.0,    # seconds between requests
            'default': 1.5     # seconds between requests
        }
        
        # User agents for different platforms
        self.user_agents = {
            'default': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'instagram': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'twitter': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Last request timestamps for rate limiting
        self.last_requests = {}
        
        # Error tracking
        self.error_counts = {}
        
        self.logger.info(f"ScraperServiceV4 {self.version} initialized")
        self.logger.info(f"Instaloader available: {INSTALOADER_AVAILABLE}")
        self.logger.info(f"Scrapling available: {SCRAPLING_AVAILABLE}")
    
    async def scrape_content(self, url: str, max_items: int = 10) -> List[Dict[str, Any]]:
        """
        Main scraping method with platform detection and error handling
        """
        start_time = time.time()
        platform = self._detect_platform(url)
        
        self.logger.info(f"Scraping {platform} content from: {url}")
        
        try:
            # Apply rate limiting
            await self._rate_limit(platform)
            
            # Route to appropriate scraper
            if platform == 'instagram':
                posts = await self._scrape_instagram(url, max_items)
            elif platform == 'twitter':
                posts = await self._scrape_twitter(url, max_items)
            elif platform == 'rss':
                posts = await self._scrape_rss(url, max_items)
            else:  # website
                posts = await self._scrape_website(url, max_items)
            
            # Post-process and validate
            validated_posts = self._validate_posts(posts)
            
            duration = time.time() - start_time
            self.logger.info(f"Scraped {len(validated_posts)} posts from {platform} in {duration:.2f}s")
            
            return validated_posts
            
        except Exception as e:
            self._track_error(platform, str(e))
            self.logger.error(f"Scraping failed for {url}: {e}")
            return []
    
    def _detect_platform(self, url: str) -> str:
        """Detect the platform type from URL"""
        url_lower = url.lower()
        
        if 'instagram.com' in url_lower:
            return 'instagram'
        elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
            return 'twitter'
        elif url_lower.endswith(('.xml', '.rss')) or 'feed' in url_lower:
            return 'rss'
        else:
            return 'website'
    
    async def _rate_limit(self, platform: str):
        """Apply rate limiting based on platform"""
        current_time = time.time()
        last_request = self.last_requests.get(platform, 0)
        rate_limit = self.rate_limits.get(platform, self.rate_limits['default'])
        
        time_since_last = current_time - last_request
        if time_since_last < rate_limit:
            sleep_time = rate_limit - time_since_last
            self.logger.debug(f"Rate limiting {platform}: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_requests[platform] = time.time()
    
    async def _scrape_instagram(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """
        Enhanced Instagram scraping with multiple fallback methods
        """
        posts = []
        
        # Method 1: Try public JSON endpoints
        try:
            posts = await self._scrape_instagram_public(url, max_items)
            if posts:
                self.logger.info(f"Instagram public API success: {len(posts)} posts")
                return posts
        except Exception as e:
            self.logger.warning(f"Instagram public API failed: {e}")
        
        # Method 2: Try Instaloader (if available)
        if INSTALOADER_AVAILABLE:
            try:
                posts = await self._scrape_instagram_instaloader(url, max_items)
                if posts:
                    self.logger.info(f"Instaloader success: {len(posts)} posts")
                    return posts
            except Exception as e:
                self.logger.warning(f"Instaloader failed: {e}")
        
        # Method 3: Fallback to basic profile info
        try:
            posts = await self._scrape_instagram_fallback(url)
            self.logger.info(f"Instagram fallback: {len(posts)} posts")
            return posts
        except Exception as e:
            self.logger.error(f"All Instagram methods failed: {e}")
            return []
    
    async def _scrape_instagram_public(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape Instagram using public endpoints"""
        posts = []
        
        profile_name = self._extract_instagram_username(url)
        if not profile_name:
            return posts
        
        headers = {
            'User-Agent': self.user_agents['instagram'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            # Try main profile page
            profile_url = f"https://www.instagram.com/{profile_name}/"
            response = requests.get(profile_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Extract JSON data from page
                content = response.text
                
                # Look for window._sharedData
                json_start = content.find('window._sharedData = ')
                if json_start != -1:
                    json_start += len('window._sharedData = ')
                    json_end = content.find(';</script>', json_start)
                    if json_end != -1:
                        json_str = content[json_start:json_end]
                        try:
                            data = json.loads(json_str)
                            posts = self._parse_instagram_json(data, profile_name, max_items)
                        except json.JSONDecodeError:
                            pass
                
                # If no JSON found, create basic profile post
                if not posts:
                    posts.append({
                        'title': f'Instagram Profile: @{profile_name}',
                        'link': profile_url,
                        'description': f'Instagram content from @{profile_name}',
                        'published': datetime.now().isoformat(),
                        'author': profile_name,
                        'content_type': 'instagram_profile',
                        'popularity_score': 50,
                        'platform': 'instagram'
                    })
        
        except Exception as e:
            self.logger.error(f"Instagram public scraping error: {e}")
        
        return posts[:max_items]
    
    async def _scrape_instagram_instaloader(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape Instagram using Instaloader library"""
        if not INSTALOADER_AVAILABLE:
            return []
        
        posts = []
        profile_name = self._extract_instagram_username(url)
        
        if not profile_name:
            return posts
        
        try:
            loader = instaloader.Instaloader()
            
            try:
                profile = instaloader.Profile.from_username(loader.context, profile_name)
            except (instaloader.exceptions.ProfileNotExistsException, 
                    instaloader.exceptions.LoginRequiredException):
                return posts
            
            post_count = 0
            for post in profile.get_posts():
                if post_count >= max_items:
                    break
                
                post_data = {
                    'title': (post.caption or '')[:100],
                    'link': f"https://www.instagram.com/p/{post.shortcode}/",
                    'description': post.caption or '',
                    'published': post.date_utc.isoformat() if post.date_utc else None,
                    'author': profile_name,
                    'content_type': 'video' if post.is_video else 'photo',
                    'popularity_score': self._calculate_popularity_score(post.likes, post.comments),
                    'platform': 'instagram',
                    'media_url': post.url if hasattr(post, 'url') else None,
                    'likes': post.likes,
                    'comments': post.comments
                }
                
                posts.append(post_data)
                post_count += 1
                
                # Rate limiting
                await asyncio.sleep(1)
        
        except Exception as e:
            self.logger.error(f"Instaloader error: {e}")
        
        return posts
    
    async def _scrape_instagram_fallback(self, url: str) -> List[Dict[str, Any]]:
        """Fallback Instagram scraping method"""
        profile_name = self._extract_instagram_username(url)
        
        return [{
            'title': f'Instagram: @{profile_name}',
            'link': url,
            'description': f'Instagram profile content from @{profile_name}',
            'published': datetime.now().isoformat(),
            'author': profile_name,
            'content_type': 'instagram_profile',
            'popularity_score': 40,
            'platform': 'instagram'
        }] if profile_name else []
    
    async def _scrape_twitter(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """
        Enhanced Twitter scraping with async compatibility fixes
        """
        posts = []
        
        try:
            # Method 1: Try Scrapling with proper async handling
            if SCRAPLING_AVAILABLE:
                posts = await self._scrape_twitter_scrapling(url, max_items)
                if posts:
                    self.logger.info(f"Twitter Scrapling success: {len(posts)} posts")
                    return posts
        except Exception as e:
            self.logger.warning(f"Twitter Scrapling failed: {e}")
        
        # Method 2: Fallback to requests-based scraping
        try:
            posts = await self._scrape_twitter_requests(url, max_items)
            if posts:
                self.logger.info(f"Twitter requests success: {len(posts)} posts")
                return posts
        except Exception as e:
            self.logger.warning(f"Twitter requests failed: {e}")
        
        # Method 3: Basic fallback
        posts = await self._scrape_twitter_fallback(url)
        self.logger.info(f"Twitter fallback: {len(posts)} posts")
        return posts
    
    async def _scrape_twitter_scrapling(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape Twitter using Scrapling with async fixes"""
        if not SCRAPLING_AVAILABLE:
            return []
        
        posts = []
        
        try:
            # Run Scrapling in thread pool to avoid async conflicts
            import concurrent.futures
            
            def scrape_sync():
                try:
                    # Initialize Scrapling with fixed parameters
                    fetcher = Fetcher(
                        stealth=True,
                        block_images=True,
                        block_trackers=True
                    )
                    
                    # Get page content
                    response = fetcher.get(url)
                    
                    if response and hasattr(response, 'content'):
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for tweets using CSS selectors
                        tweet_selectors = [
                            '[data-testid="tweet"]',
                            'article[data-testid="tweet"]',
                            '.tweet',
                            '[role="article"]'
                        ]
                        
                        tweets = []
                        for selector in tweet_selectors:
                            try:
                                tweets = soup.select(selector)
                                if tweets:
                                    break
                            except Exception:
                                continue
                        
                        return self._parse_twitter_elements(tweets, max_items)
                        
                except Exception as e:
                    self.logger.error(f"Scrapling sync error: {e}")
                    return []
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                posts = await loop.run_in_executor(executor, scrape_sync)
                
        except Exception as e:
            self.logger.error(f"Twitter Scrapling async error: {e}")
        
        return posts
    
    async def _scrape_twitter_requests(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape Twitter using requests library"""
        posts = []
        
        headers = {
            'User-Agent': self.user_agents['twitter'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to find tweets
                tweet_elements = soup.find_all(['article', 'div'], {'data-testid': 'tweet'})
                
                if not tweet_elements:
                    # Fallback selectors
                    tweet_elements = soup.find_all('div', class_=re.compile(r'tweet|status'))
                
                posts = self._parse_twitter_elements(tweet_elements, max_items)
                
        except Exception as e:
            self.logger.error(f"Twitter requests error: {e}")
        
        return posts
    
    async def _scrape_twitter_fallback(self, url: str) -> List[Dict[str, Any]]:
        """Fallback Twitter scraping method"""
        username = self._extract_twitter_username(url)
        
        return [{
            'title': f'Twitter: @{username}' if username else 'Twitter Content',
            'link': url,
            'description': f'Twitter content from @{username}' if username else 'Twitter content',
            'published': datetime.now().isoformat(),
            'author': username or 'Unknown',
            'content_type': 'twitter_profile',
            'popularity_score': 40,
            'platform': 'twitter'
        }]
    
    async def _scrape_website(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """
        Enhanced website scraping with BeautifulSoup conflict resolution
        """
        posts = []
        
        try:
            # Method 1: Try Scrapling if available
            if SCRAPLING_AVAILABLE:
                posts = await self._scrape_website_scrapling(url, max_items)
                if posts:
                    self.logger.info(f"Website Scrapling success: {len(posts)} posts")
                    return posts
        except Exception as e:
            self.logger.warning(f"Website Scrapling failed: {e}")
        
        # Method 2: Standard requests + BeautifulSoup
        try:
            posts = await self._scrape_website_requests(url, max_items)
            if posts:
                self.logger.info(f"Website requests success: {len(posts)} posts")
                return posts
        except Exception as e:
            self.logger.warning(f"Website requests failed: {e}")
        
        return posts
    
    async def _scrape_website_scrapling(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape website using Scrapling with fixed parameters"""
        if not SCRAPLING_AVAILABLE:
            return []
        
        posts = []
        
        try:
            import concurrent.futures
            
            def scrape_sync():
                try:
                    # Initialize with corrected parameters
                    fetcher = Fetcher(
                        stealth=True,
                        block_images=True,
                        block_trackers=True,
                        # Remove unsupported parameters
                        # auto_match=True,  # REMOVED
                        # auto_save=True    # REMOVED
                    )
                    
                    response = fetcher.get(url)
                    
                    if response and hasattr(response, 'content'):
                        soup = BeautifulSoup(response.content, 'html.parser')
                        return self._parse_website_content(soup, url, max_items)
                        
                except Exception as e:
                    self.logger.error(f"Website Scrapling sync error: {e}")
                    return []
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                posts = await loop.run_in_executor(executor, scrape_sync)
                
        except Exception as e:
            self.logger.error(f"Website Scrapling async error: {e}")
        
        return posts
    
    async def _scrape_website_requests(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape website using requests library with fixed BeautifulSoup usage"""
        posts = []
        
        headers = {
            'User-Agent': self.user_agents['default'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                posts = self._parse_website_content(soup, url, max_items)
                
        except Exception as e:
            self.logger.error(f"Website requests error: {e}")
        
        return posts
    
    async def _scrape_rss(self, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Scrape RSS/Atom feeds"""
        posts = []
        
        try:
            feed = feedparser.parse(url)
            
            if feed.entries:
                for entry in feed.entries[:max_items]:
                    post_data = {
                        'title': getattr(entry, 'title', 'No Title'),
                        'link': getattr(entry, 'link', url),
                        'description': getattr(entry, 'summary', ''),
                        'published': self._parse_feed_date(getattr(entry, 'published', '')),
                        'author': getattr(entry, 'author', 'Unknown'),
                        'content_type': 'rss',
                        'popularity_score': 60,
                        'platform': 'rss'
                    }
                    
                    posts.append(post_data)
                    
        except Exception as e:
            self.logger.error(f"RSS scraping error: {e}")
        
        return posts
    
    def _parse_website_content(self, soup: BeautifulSoup, url: str, max_items: int) -> List[Dict[str, Any]]:
        """Parse website content with fixed BeautifulSoup usage"""
        posts = []
        
        try:
            # Content selectors with proper BeautifulSoup usage
            article_selectors = [
                'article',
                '.post',
                '.entry',
                '.content',
                '.blog-post',
                '.news-item',
                'main'
            ]
            
            articles = []
            for selector in article_selectors:
                try:
                    # Use CSS selector properly
                    found_articles = soup.select(selector)
                    if found_articles:
                        articles.extend(found_articles[:max_items])
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no articles found, try headings
            if not articles:
                articles = soup.find_all(['h1', 'h2', 'h3'], limit=max_items)
            
            for i, article in enumerate(articles[:max_items]):
                if isinstance(article, Tag):  # Ensure it's a Tag object
                    try:
                        # Safe text extraction
                        title = self._safe_get_text(article, ['h1', 'h2', 'h3', 'title'])
                        description = self._safe_get_text(article, ['p', 'div', 'span'])
                        
                        # Get link safely
                        link = self._safe_get_link(article, url)
                        
                        post_data = {
                            'title': title or f'Content {i+1}',
                            'link': link,
                            'description': description[:500] if description else '',
                            'published': datetime.now().isoformat(),
                            'author': 'Website',
                            'content_type': 'website',
                            'popularity_score': 50,
                            'platform': 'website'
                        }
                        
                        posts.append(post_data)
                        
                    except Exception as e:
                        self.logger.debug(f"Article parsing error: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Website content parsing error: {e}")
        
        return posts
    
    def _safe_get_text(self, element: Tag, selectors: List[str]) -> str:
        """Safely extract text from element using selectors"""
        try:
            for selector in selectors:
                try:
                    # Use find instead of select to avoid conflicts
                    found = element.find(selector)
                    if found and hasattr(found, 'get_text'):
                        text = found.get_text(strip=True)
                        if text:
                            return text
                except Exception:
                    continue
            
            # Fallback to element's own text
            if hasattr(element, 'get_text'):
                return element.get_text(strip=True)
                
        except Exception as e:
            self.logger.debug(f"Safe text extraction error: {e}")
        
        return ''
    
    def _safe_get_link(self, element: Tag, base_url: str) -> str:
        """Safely extract link from element"""
        try:
            # Try to find 'a' tag
            link_element = element.find('a')
            if link_element and link_element.get('href'):
                href = link_element.get('href')
                return urljoin(base_url, href)
                
        except Exception as e:
            self.logger.debug(f"Safe link extraction error: {e}")
        
        return base_url
    
    def _parse_twitter_elements(self, elements: List, max_items: int) -> List[Dict[str, Any]]:
        """Parse Twitter elements safely"""
        posts = []
        
        for i, element in enumerate(elements[:max_items]):
            try:
                if hasattr(element, 'get_text'):
                    text = element.get_text(strip=True)
                    
                    post_data = {
                        'title': text[:100] if text else f'Tweet {i+1}',
                        'link': 'https://x.com',
                        'description': text[:500] if text else '',
                        'published': datetime.now().isoformat(),
                        'author': 'Twitter User',
                        'content_type': 'tweet',
                        'popularity_score': 45,
                        'platform': 'twitter'
                    }
                    
                    posts.append(post_data)
                    
            except Exception as e:
                self.logger.debug(f"Twitter element parsing error: {e}")
                continue
        
        return posts
    
    def _parse_instagram_json(self, data: Dict, profile_name: str, max_items: int) -> List[Dict[str, Any]]:
        """Parse Instagram JSON data safely"""
        posts = []
        
        try:
            # Navigate through Instagram's JSON structure
            if 'entry_data' in data:
                profile_page = data['entry_data'].get('ProfilePage', [])
                if profile_page:
                    user_data = profile_page[0].get('graphql', {}).get('user', {})
                    media_data = user_data.get('edge_owner_to_timeline_media', {})
                    edges = media_data.get('edges', [])
                    
                    for edge in edges[:max_items]:
                        node = edge.get('node', {})
                        
                        post_data = {
                            'title': (node.get('accessibility_caption', '') or 
                                    node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''))[:100],
                            'link': f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                            'description': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                            'published': datetime.fromtimestamp(node.get('taken_at_timestamp', 0)).isoformat() if node.get('taken_at_timestamp') else None,
                            'author': profile_name,
                            'content_type': 'video' if node.get('is_video') else 'photo',
                            'popularity_score': self._calculate_popularity_score(
                                node.get('edge_liked_by', {}).get('count', 0),
                                node.get('edge_media_to_comment', {}).get('count', 0)
                            ),
                            'platform': 'instagram',
                            'media_url': node.get('display_url'),
                            'likes': node.get('edge_liked_by', {}).get('count', 0),
                            'comments': node.get('edge_media_to_comment', {}).get('count', 0)
                        }
                        
                        posts.append(post_data)
                        
        except Exception as e:
            self.logger.error(f"Instagram JSON parsing error: {e}")
        
        return posts
    
    def _calculate_popularity_score(self, likes: int, comments: int) -> int:
        """Calculate popularity score based on engagement"""
        try:
            # Simple engagement-based scoring
            total_engagement = likes + (comments * 3)  # Comments worth more
            
            if total_engagement > 10000:
                return 90
            elif total_engagement > 1000:
                return 80
            elif total_engagement > 100:
                return 70
            elif total_engagement > 10:
                return 60
            else:
                return 50
                
        except Exception:
            return 50
    
    def _extract_instagram_username(self, url: str) -> Optional[str]:
        """Extract Instagram username from URL"""
        try:
            patterns = [
                r'instagram\.com/([^/?]+)',
                r'instagram\.com/p/([^/?]+)',
                r'ig\.me/([^/?]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    username = match.group(1)
                    # Clean username
                    if username not in ['p', 'stories', 'tv', 'reel']:
                        return username.strip('/')
                        
        except Exception as e:
            self.logger.error(f"Instagram username extraction error: {e}")
        
        return None
    
    def _extract_twitter_username(self, url: str) -> Optional[str]:
        """Extract Twitter username from URL"""
        try:
            patterns = [
                r'(?:twitter\.com|x\.com)/([^/?]+)',
                r'(?:twitter\.com|x\.com)/#!/([^/?]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    username = match.group(1)
                    # Clean username
                    if username not in ['home', 'search', 'notifications', 'messages']:
                        return username.strip('/')
                        
        except Exception as e:
            self.logger.error(f"Twitter username extraction error: {e}")
        
        return None
    
    def _parse_feed_date(self, date_str: str) -> str:
        """Parse feed date safely"""
        try:
            if date_str:
                # feedparser usually handles this, but add safety
                return date_str
        except Exception:
            pass
        
        return datetime.now().isoformat()
    
    def _validate_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean posts"""
        validated = []
        
        for post in posts:
            try:
                # Ensure required fields
                if not post.get('title'):
                    post['title'] = 'Untitled'
                
                if not post.get('link'):
                    post['link'] = 'https://example.com'
                
                if not post.get('published'):
                    post['published'] = datetime.now().isoformat()
                
                # Add unique ID
                post['id'] = hashlib.md5(
                    f"{post['title']}{post['link']}{post.get('published', '')}".encode()
                ).hexdigest()
                
                # Add scraping metadata
                post['scraped_at'] = datetime.now().isoformat()
                post['scraper_version'] = self.version
                
                validated.append(post)
                
            except Exception as e:
                self.logger.error(f"Post validation error: {e}")
                continue
        
        return validated
    
    def _track_error(self, platform: str, error: str):
        """Track errors for monitoring"""
        if platform not in self.error_counts:
            self.error_counts[platform] = {}
        
        error_key = error[:50]  # Truncate error for grouping
        self.error_counts[platform][error_key] = self.error_counts[platform].get(error_key, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        return {
            'version': self.version,
            'instaloader_available': INSTALOADER_AVAILABLE,
            'scrapling_available': SCRAPLING_AVAILABLE,
            'rate_limits': self.rate_limits,
            'error_counts': self.error_counts,
            'last_requests': self.last_requests
        } 