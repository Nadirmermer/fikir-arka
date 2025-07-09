"""
Scheduler Service for automatic content scraping
APScheduler integration for daily morning scraping
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from app.core.config import get_settings
from app.services.scraper_service import scraper_service

logger = logging.getLogger(__name__)

# Global scraping status tracking
class ScrapingStatus:
    def __init__(self):
        self.status = "idle"  # idle, running, failed
        self.last_scrape_time = None
        self.next_scrape_time = None
        
    def set_running(self):
        self.status = "running"
        
    def set_idle(self):
        self.status = "idle"
        
    def set_failed(self):
        self.status = "failed"
        
    def update_last_scrape(self, timestamp: datetime):
        self.last_scrape_time = timestamp
        
    def update_next_scrape(self, timestamp: datetime):
        self.next_scrape_time = timestamp

# Global instance
scraping_status = ScrapingStatus()

class SchedulerService:
    """Automatic scheduling service for content scraping"""
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.settings.scheduler_timezone)
        self.scraper_service = None
        self._is_running = False
    
    async def start(self):
        """Start the scheduler"""
        try:
            # Use enhanced scraper service
            self.scraper_service = scraper_service
            
            # Add daily scraping job
            self.scheduler.add_job(
                self._scheduled_scrape,
                CronTrigger(
                    hour=self.settings.scrape_schedule_hour,
                    minute=self.settings.scrape_schedule_minute,
                    timezone=self.settings.scheduler_timezone
                ),
                id="daily_scrape",
                name="Daily Content Scraping",
                replace_existing=True,
                max_instances=1
            )
            
            # Start scheduler
            self.scheduler.start()
            self._is_running = True
            
            # Log next run time and update global status
            next_run = self.get_next_scrape_time()
            if next_run:
                scraping_status.update_next_scrape(next_run)
            logger.info(f"✅ Scheduler started - Next scrape: {next_run}")
            
        except Exception as e:
            logger.error(f"❌ Scheduler start failed: {e}")
            self._is_running = False
    
    async def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("📴 Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Scheduler stop failed: {e}")
    
    async def _scheduled_scrape(self):
        """Scheduled scraping task"""
        logger.info("🕘 Starting scheduled content scraping...")
        
        try:
            # Update status to running
            scraping_status.set_running()
            
            if not self.scraper_service:
                self.scraper_service = scraper_service
            
            # Run enhanced scraping
            result = await self.scraper_service.scrape_all_sources()
            
            if result.get("success"):
                logger.info(f"✅ Enhanced scheduled scraping completed: {result.get('total_new_content', 0)} new items from {result.get('sources_processed', 0)}/{result.get('total_sources', 0)} sources")
                
                # Log performance metrics
                if 'performance' in result:
                    perf = result['performance']
                    logger.info(f"📊 Performance: {perf['success_rate']}% success rate, {perf['avg_time_per_source']}s avg per source")
                
                # Update status to idle on success
                scraping_status.set_idle()
                scraping_status.update_last_scrape(datetime.utcnow())
            else:
                logger.error(f"❌ Enhanced scheduled scraping failed: {result.get('error', 'Unknown error')}")
                scraping_status.set_failed()
            
        except Exception as e:
            logger.error(f"❌ Scheduled scraping failed: {e}")
            scraping_status.set_failed()
    
    async def trigger_manual_scrape(self):
        """Manually trigger scraping outside schedule"""
        logger.info("🔄 Manual scraping triggered...")
        
        try:
            if not self.scraper_service:
                self.scraper_service = scraper_service
            
            # Run enhanced scraping in background
            asyncio.create_task(self.scraper_service.scrape_all_sources())
            
            return {
                "success": True,
                "message": "Manual scraping started",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Manual scraping failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_next_scrape_time(self) -> Optional[datetime]:
        """Get next scheduled scrape time"""
        try:
            job = self.scheduler.get_job("daily_scrape")
            if job and job.next_run_time:
                return job.next_run_time
            return None
        except:
            return None
    
    def get_last_scrape_time(self) -> Optional[datetime]:
        """Get last scrape time (from database or logs)"""
        # This would typically check database for last scrape time
        # For now, return None - can be implemented with database integration
        return None
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._is_running and self.scheduler.running
    
    def get_schedule_info(self) -> dict:
        """Get scheduler information"""
        next_run = self.get_next_scrape_time()
        last_run = self.get_last_scrape_time()
        
        return {
            "scheduler_running": self.is_running(),
            "next_scrape_time": next_run.isoformat() if next_run else None,
            "last_scrape_time": last_run.isoformat() if last_run else None,
            "schedule": f"Daily at {self.settings.scrape_schedule_hour:02d}:{self.settings.scrape_schedule_minute:02d}",
            "timezone": self.settings.scheduler_timezone,
            "jobs_count": len(self.scheduler.get_jobs())
        }
    
    async def update_schedule(self, hour: int, minute: int = 0):
        """Update scraping schedule"""
        try:
            # Remove existing job
            self.scheduler.remove_job("daily_scrape")
            
            # Add new job with updated time
            self.scheduler.add_job(
                self._scheduled_scrape,
                CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=self.settings.scheduler_timezone
                ),
                id="daily_scrape",
                name="Daily Content Scraping",
                replace_existing=True,
                max_instances=1
            )
            
            # Update settings
            self.settings.scrape_schedule_hour = hour
            self.settings.scrape_schedule_minute = minute
            
            next_run = self.get_next_scrape_time()
            if next_run:
                scraping_status.update_next_scrape(next_run)
            logger.info(f"✅ Schedule updated - Next scrape: {next_run}")
            
            return {
                "success": True,
                "message": f"Schedule updated to {hour:02d}:{minute:02d}",
                "next_run": next_run.isoformat() if next_run else None
            }
            
        except Exception as e:
            logger.error(f"❌ Schedule update failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def get_current_scraping_status() -> dict:
    """Get current scraping status for API responses"""
    return {
        "status": scraping_status.status,
        "last_scrape_time": scraping_status.last_scrape_time,
        "next_scrape_time": scraping_status.next_scrape_time
    } 