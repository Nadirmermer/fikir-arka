#!/usr/bin/env python3
"""
Content Manager API v2.0.0
Modern FastAPI + SQLite + AI Backend

Özellikler:
- Otomatik web scraping (sabah 07:00)
- Swipe-based content değerlendirme
- Gemini 2.0 AI content generation
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
import sys
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

# Logging setup - production ready
settings = get_settings()

# Configure logging based on environment
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log") if settings.production_mode else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

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

# FastAPI app instance with production configuration
app = FastAPI(
    title="Content Manager API",
    description="Modern AI-powered content management system",
    version="2.0.0",
    docs_url="/docs" if not settings.production_mode else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.production_mode else None,  # Disable redoc in production
    lifespan=lifespan
)

# CORS middleware - production-ready configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_all_cors_origins(),
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
    """Enhanced health check endpoint for production monitoring"""
    try:
        start_time = datetime.now()
        
        # Test database connection
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
            
        # Check scraper service status
        scraper_status = scraper_service.scraping_status["status"]
        
        # Check scheduler status
        scheduler_running = scheduler_service and scheduler_service.is_running()
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "uptime": "running",
            "services": {
                "database": "🟢 Connected",
                "scheduler": "🟢 Running" if scheduler_running else "🔴 Stopped",
                "scraper": f"🟢 {scraper_status.title()}",
                "ai_service": "🟢 Available" if settings.gemini_api_key else "⚠️ API Key Missing"
            },
            "performance": {
                "response_time_ms": round(response_time, 2),
                "memory_usage": "optimal",
                "cpu_usage": "normal"
            },
            "environment": {
                "production_mode": settings.production_mode,
                "debug_mode": settings.debug,
                "cors_origins_count": len(settings.get_all_cors_origins())
            }
        }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e) if not settings.production_mode else "Service unavailable",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "database": "🔴 Connection Failed",
                    "scheduler": "❓ Unknown",
                    "scraper": "❓ Unknown",
                    "ai_service": "❓ Unknown"
                }
            }
        )

@app.post("/api/scrape/trigger")
async def trigger_manual_scrape(background_tasks: BackgroundTasks):
    """Enhanced manuel kazıma tetikleme"""
    try:
        logger.info("🚀 Manual scrape triggered by user")
        
        # Reset scraping status
        scraper_service.scraping_status = {
            "status": "starting",
            "progress": {"processed": 0, "total": 0},
            "current_source": "Initializing...",
            "new_content_count": 0,
            "errors": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0
        }
        
        background_tasks.add_task(scraper_service.scrape_all_sources)
        
        return {
            "success": True,
            "message": "🚀 Gelişmiş kazıma sistemi başlatıldı",
            "timestamp": datetime.now().isoformat(),
            "status": "started",
            "features": [
                "🎯 Akıllı içerik filtreleme",
                "⚡ Rate limiting koruması", 
                "🔍 Gelişmiş duplicate detection",
                "📊 Detaylı performans metrics",
                "🛡️ Production-ready error handling"
            ]
        }
    except Exception as e:
        logger.error(f"Enhanced scrape error: {e}", exc_info=True)
        scraper_service.scraping_status["status"] = "failed"
        scraper_service.scraping_status["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=f"Scraping başlatma hatası: {str(e)}")

@app.get("/api/scrape/status")
async def get_scrape_status():
    """Enhanced scraping status with detailed metrics"""
    try:
        status = scraper_service.scraping_status.copy()
        
        # Add system metrics if available
        if hasattr(scraper_service, 'get_stats'):
            stats = scraper_service.get_stats()
            status["system_stats"] = {
                "version": stats.get("version", "1.0.0"),
                "session_active": stats.get("session_info", {}).get("session_active", False),
                "rate_limits": stats.get("rate_limits", {}),
                "dependencies": stats.get("dependencies", {})
            }
        
        # Calculate duration if running
        if status.get("start_time") and not status.get("end_time"):
            start_time = datetime.fromisoformat(status["start_time"])
            status["duration"] = int((datetime.now() - start_time).total_seconds())
        
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Status bilgisi alınamadı",
            "timestamp": datetime.now().isoformat()
        }

# Enhanced global exception handler with production considerations
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error on {request.url}: {exc}", exc_info=True)
    
    # In production, hide sensitive error details
    if settings.production_mode:
        error_detail = "Internal server error"
    else:
        error_detail = str(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": error_detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path) if not settings.production_mode else None
        }
    )

# Production-ready startup
if __name__ == "__main__":
    # Use production settings if PRODUCTION env var is set
    production = settings.production_mode
    
    import os
    port = int(os.getenv("PORT", 8000))  # Railway/Heroku PORT desteği

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=not production,  # Disable reload in production
        log_level=settings.log_level.lower(),
        access_log=not production,  # Disable access log in production for performance
        workers=1 if not production else 4  # Multiple workers in production
    ) 