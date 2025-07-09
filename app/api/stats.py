"""
Statistics API Endpoints
System statistics and metrics
"""

from fastapi import APIRouter
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Topic, Source, AIContent, StatsResponse
from app.services.scheduler_service import get_current_scraping_status

router = APIRouter()

@router.get("/", response_model=StatsResponse)
async def get_stats():
    """Get system statistics"""
    async with get_db() as db:
        # Topic stats
        total_topics = await db.scalar(select(func.count()).select_from(Topic))
        pending_topics = await db.scalar(select(func.count()).select_from(Topic).where(Topic.status == "pending"))
        liked_topics = await db.scalar(select(func.count()).select_from(Topic).where(Topic.status == "liked"))
        disliked_topics = await db.scalar(select(func.count()).select_from(Topic).where(Topic.status == "disliked"))
        
        # Today's topics (last 24 hours)
        today_start = datetime.utcnow() - timedelta(days=1)
        today_topics = await db.scalar(
            select(func.count()).select_from(Topic).where(Topic.extracted_at >= today_start)
        )
        
        # Source stats
        total_sources = await db.scalar(select(func.count()).select_from(Source))
        active_sources = await db.scalar(select(func.count()).select_from(Source).where(Source.is_active == True))
        
        # AI content stats
        total_ai_contents = await db.scalar(select(func.count()).select_from(AIContent))
        completed_ai_contents = await db.scalar(select(func.count()).select_from(AIContent).where(AIContent.status == "completed"))
        
        # Latest scrape time
        latest_source = await db.scalar(
            select(Source).where(Source.last_scraped_at.isnot(None)).order_by(Source.last_scraped_at.desc()).limit(1)
        )
        last_scrape_time = latest_source.last_scraped_at if latest_source else None
        
        # Get actual scraping status from scheduler service
        scraping_status_data = get_current_scraping_status()
        
        return StatsResponse(
            total_topics=total_topics or 0,
            pending_topics=pending_topics or 0,
            liked_topics=liked_topics or 0,
            disliked_topics=disliked_topics or 0,
            today_topics=today_topics or 0,
            total_sources=total_sources or 0,
            active_sources=active_sources or 0,
            sources_count=total_sources or 0,  # Alias for compatibility
            total_ai_contents=total_ai_contents or 0,
            completed_ai_contents=completed_ai_contents or 0,
            last_scrape_time=scraping_status_data.get('last_scrape_time') or last_scrape_time,
            next_scrape_time=scraping_status_data.get('next_scrape_time'),
            last_update=datetime.utcnow(),
            scraping_status=scraping_status_data.get('status', 'idle')
        ) 