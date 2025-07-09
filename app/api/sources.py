"""
Sources API Endpoints  
CRUD operations for content sources
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from app.database import get_db
from app.models import Source, SourceResponse
from app.services.scraper_service import scraper_service

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateSourceURL(BaseModel):
    url: HttpUrl

async def analyze_and_fetch_source_details(url: str) -> dict:
    """Analyzes a URL to determine its platform and fetches its title with intelligent feed discovery."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        platform = "website"
        source_type = "rss"
        title = "Unknown Source"
        final_url = url
        
        # YouTube detection and handling
        if "youtube.com" in url or "youtu.be" in url:
            platform = "youtube"
            if "/c/" in url or "/channel/" in url or "/user/" in url or "/@" in url:
                source_type = "channel"
            elif "/playlist" in url:
                source_type = "playlist"
            elif "/watch?v=" in url or "youtu.be/" in url:
                source_type = "channel"  # Video URL will be converted to channel feed
            else:
                source_type = "channel"
            
            # Try to get RSS URL using scraper service
            rss_url = scraper_service._get_youtube_rss_url(url)
            if rss_url:
                final_url = rss_url
                # Get title from the original URL
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        # Clean YouTube title
                        title = title.replace(' - YouTube', '').strip()
                except:
                    title = f"YouTube Channel/Playlist"
            else:
                title = f"YouTube: {url.split('/')[-1]}"
        
        # Instagram detection
        elif "instagram.com" in url:
            platform = "instagram"
            source_type = "profile"
            try:
                username = url.split("instagram.com/")[1].split("/")[0]
                title = f"Instagram: @{username}"
            except:
                title = "Instagram Profile"
        
        # Twitter/X detection
        elif "twitter.com" in url or "x.com" in url:
            platform = "twitter"
            source_type = "profile"
            try:
                username = url.split("/")[-1].split("?")[0]
                title = f"Twitter: @{username}"
            except:
                title = "Twitter Profile"
        
        # Generic website - try feed discovery
        else:
            # First get the page title
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                
                # Try automatic feed discovery
                feed_discovery = await scraper_service.discover_feeds(url)
                if feed_discovery['success'] and feed_discovery['feeds']:
                    # Use the best feed found
                    best_feed = feed_discovery['feeds'][0]  # Highest scored feed
                    final_url = best_feed['url']
                    platform = "rss"
                    source_type = "rss"
                    if best_feed['title'] and best_feed['title'] != 'Unknown Feed':
                        title = best_feed['title']
                    logger.info(f"Found RSS feed for {url}: {final_url}")
                else:
                    # No feeds found, treat as generic website
                    platform = "website"
                    source_type = "website"
                    
            except Exception as e:
                logger.warning(f"Failed to analyze website {url}: {e}")
                title = f"Website: {url}"

        return {
            "name": title,
            "platform": platform,
            "source_type": source_type,
            "url": final_url  # May be different from input URL (e.g., RSS feed URL)
        }

    except requests.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        raise HTTPException(status_code=400, detail=f"URL alınamadı veya geçersiz: {e}")


@router.post("/", response_model=SourceResponse)
async def create_source(source_data: CreateSourceURL):
    async with get_db() as db:
        original_url = str(source_data.url)
        try:
            # Analyze the URL and get optimized details
            details = await analyze_and_fetch_source_details(original_url)
            final_url = details["url"]  # This might be different (e.g., RSS feed URL)
            
            # Check if source with this final URL already exists
            result = await db.execute(select(Source).where(Source.url == final_url))
            existing_source = result.scalar_one_or_none()
            if existing_source:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Bu URL ile bir kaynak zaten mevcut: '{existing_source.name}'"
                )

            new_source = Source(
                url=final_url,  # Use the optimized URL (e.g., RSS feed instead of website)
                name=details["name"],
                platform=details["platform"],
                source_type=details["source_type"]
            )
            db.add(new_source)
            await db.commit()
            await db.refresh(new_source)
            return new_source
        except HTTPException as e:
            raise e # Re-raise client-side errors
        except Exception as e:
            logger.error(f"Error creating source for URL {original_url}: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Kaynak oluşturulurken beklenmedik bir sunucu hatası oluştu.")

@router.get("/", response_model=List[SourceResponse])
async def get_sources():
    async with get_db() as db:
        result = await db.execute(select(Source).order_by(Source.created_at.desc()))
        sources = result.scalars().all()
        return sources

@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: str):
    async with get_db() as db:
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
        
        await db.delete(source)
        await db.commit()
        return None 