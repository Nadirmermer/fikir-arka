"""
Topics API Endpoints
CRUD operations and swipe functionality for topics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func

from app.database import get_db
from app.models import Topic, TopicResponse, TopicUpdate, TopicCreate

router = APIRouter()

@router.get("/", response_model=List[TopicResponse])
async def get_topics(
    status: Optional[str] = Query(None, description="Filter by status: pending, liked, disliked"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get topics with optional filtering"""
    async with get_db() as db:
        query = select(Topic)
        
        if status:
            query = query.where(Topic.status == status)
        if platform:
            query = query.where(Topic.platform == platform)
        
        query = query.order_by(Topic.extracted_at.desc())
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        topics = result.scalars().all()
        
        return topics

@router.get("/pending", response_model=List[TopicResponse])
async def get_pending_topics(limit: int = Query(10, ge=1, le=100)):
    """Get pending topics for swipe interface"""
    async with get_db() as db:
        query = select(Topic).where(Topic.status == "pending")
        query = query.order_by(Topic.extracted_at.desc()).limit(limit)
        
        result = await db.execute(query)
        topics = result.scalars().all()
        
        return topics

@router.post("/{topic_id}/like")
async def like_topic(topic_id: str):
    """Like a topic (swipe right)"""
    async with get_db() as db:
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic.status = "liked"
        topic.liked_at = datetime.utcnow()
        if topic.disliked_at:
            topic.disliked_at = None
        
        db.add(topic)
        await db.commit()
        
        return {"success": True, "message": "Topic liked"}

@router.post("/{topic_id}/dislike") 
async def dislike_topic(topic_id: str):
    """Dislike a topic (swipe left)"""
    async with get_db() as db:
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic.status = "disliked"
        topic.disliked_at = datetime.utcnow()
        if topic.liked_at:
            topic.liked_at = None
        
        db.add(topic)
        await db.commit()
        
        return {"success": True, "message": "Topic disliked"}

@router.post("/{topic_id}/reset")
async def reset_topic(topic_id: str):
    """Reset topic status to pending"""
    async with get_db() as db:
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic.status = "pending"
        topic.liked_at = None
        topic.disliked_at = None
        
        db.add(topic)
        await db.commit()
        
        return {"success": True, "message": "Topic reset to pending"}

@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: str):
    """Get single topic by ID"""
    async with get_db() as db:
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        return topic

@router.post("/", response_model=TopicResponse)
async def create_manual_topic(topic_data: TopicCreate):
    """Create manual topic (user-added idea)"""
    async with get_db() as db:
        # Create new topic
        topic = Topic(
            title=topic_data.title,
            description=topic_data.description,
            content=topic_data.content,
            platform=topic_data.platform,
            source=topic_data.source,
            link=topic_data.link,
            publish_date=topic_data.publish_date,
            popularity_score=topic_data.popularity_score,
            content_length=len(topic_data.content or ""),
            status="liked"  # Manual topics are automatically liked
        )
        
        db.add(topic)
        await db.commit()
        await db.refresh(topic)
        
        return topic 