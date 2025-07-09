#!/usr/bin/env python3
"""
Content Manager API v2.0.0
Modern FastAPI + SQLite + AI Backend

Özellikler:
- Otomatik web scraping (sabah 07:00)
- Swipe-based content değerlendirme
- Gemini 2.5 AI content generation
- Modern REST API
- Otomatik OpenAPI documentation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import uvicorn
from datetime import datetime
import logging
from contextlib import asynccontextmanager

# Local imports
from app.database import init_database, get_db
from app.models import Topic, Source, AIContent
from app.services.scraper_service import scraper_service
from app.services.ai_service import AIService
from app.services.scheduler_service import SchedulerService
from app.api import topics, sources, ai_content, stats, settings as settings_api
from app.api import twitter_auth
from app.core.config import get_settings

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Scheduler instance
scheduler_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global scheduler_service
    
    # Startup
    logger.info("🚀 Content Manager API v2.0.0 başlatılıyor...")
    
    # Initialize database
    await init_database()
    logger.info("✅ Database başlatıldı")
    
    # Start scheduler
    scheduler_service = SchedulerService()
    await scheduler_service.start()
    logger.info("✅ Scheduler başlatıldı (Sabah 07:00 otomatik kazıma)")
    
    yield
    
    # Shutdown
    if scheduler_service:
        await scheduler_service.stop()
    logger.info("📴 Content Manager API kapandı")

# FastAPI app instance
app = FastAPI(
    title="Content Manager API",
    description="Modern AI-powered content management system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3000", "http://localhost:5175", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(ai_content.router, prefix="/api/ai", tags=["AI Content"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(twitter_auth.router, prefix="/api/twitter", tags=["Twitter"])

@app.get("/")
async def root():
    """API Root - Health check ve sistem bilgileri"""
    return {
        "name": "Content Manager API",
        "version": "2.0.0",
        "status": "🟢 Active",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "🕘 Otomatik sabah kazıma (07:00)",
            "👆 Swipe-based content değerlendirme", 
            "🤖 Gemini 2.5 AI content generation",
            "📊 Real-time istatistikler",
            "🔄 Multi-platform web scraping"
        ],
        "docs": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "frontend": "http://localhost:5174"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "🟢 Connected",
            "scheduler": "🟢 Running" if scheduler_service and scheduler_service.is_running() else "🔴 Stopped"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.post("/api/scrape/trigger")
async def trigger_manual_scrape(background_tasks: BackgroundTasks):
    """Enhanced manuel kazıma tetikleme"""
    try:
        background_tasks.add_task(scraper_service.scrape_all_sources)
        
        return {
            "success": True,
            "message": "🚀 Gelişmiş kazıma sistemi başlatıldı",
            "timestamp": datetime.now().isoformat(),
            "features": [
                "🎯 Akıllı içerik filtreleme",
                "⚡ Rate limiting koruması", 
                "🔍 Gelişmiş duplicate detection",
                "📊 Detaylı performans metrics"
            ]
        }
    except Exception as e:
        logger.error(f"Enhanced scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape/status")
async def get_scrape_status():
    """Anlık kazıma durumunu döndürür."""
    return scraper_service.scraping_status

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 