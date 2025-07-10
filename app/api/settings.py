"""
Settings API Endpoints
Get and update application settings
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
import os
from app.core.config import get_settings

router = APIRouter()

SETTINGS_FILE = "settings.json"

@router.get("/")
async def get_settings() -> Dict[str, Any]:
    """Get current application settings"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
        else:
            # Default settings if file doesn't exist
            settings_data = {
                "scrape_schedule_hour": 7,
                "scrape_schedule_minute": 0,
                "auto_scrape_enabled": True,
                "ai_temperature": 0.7,
                "ai_max_tokens": 2000,
                "default_ai_model": "gemini-2.0-flash-exp",
                "rate_limiting_enabled": True,
                "content_quality_threshold": 50,
                "gemini_api_key": "",
                "ai_prompt": "Content konusunu analiz et ve çekici bir post oluştur."
            }

        # Add current system settings
        sys_settings = get_settings()
        settings_data.update({
            "gemini_api_key_configured": bool(sys_settings.gemini_api_key),
            "database_url": sys_settings.database_url,
            "debug_mode": sys_settings.debug
        })

        return settings_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Settings okuma hatası: {str(e)}")

@router.put("/")
async def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update application settings"""
    try:
        # Read current settings
        current_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)

        # Update with new values
        current_settings.update(settings)

        # Save to file
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "message": "Ayarlar başarıyla güncellendi",
            "settings": current_settings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Settings güncelleme hatası: {str(e)}")

@router.get("/ai-models")
async def get_available_ai_models():
    """Get list of available AI models"""
    return {
        "models": [
            {
                "id": "gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash (Experimental)",
                "description": "En hızlı ve gelişmiş model",
                "recommended": True
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "description": "Dengeli performans",
                "recommended": False
            },
            {
                "id": "gemini-1.5-flash",
                "name": "Gemini 1.5 Flash",
                "description": "Hızlı işlem",
                "recommended": False
            }
        ]
    }

@router.put("/api-key")
async def update_api_key(api_key_data: Dict[str, str]) -> Dict[str, Any]:
    """Update API key (Gemini API Key)"""
    try:
        api_key = api_key_data.get("api_key", "")
        
        # Read current settings
        current_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        
        # Update API key
        current_settings["gemini_api_key"] = api_key
        
        # Save to file
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)
        
        # Also update environment variable
        os.environ["GEMINI_API_KEY"] = api_key
        
        return {
            "success": True,
            "message": "API key başarıyla güncellendi",
            "api_key_configured": bool(api_key)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API key güncelleme hatası: {str(e)}")

@router.get("/api-key")
async def get_api_key_status() -> Dict[str, Any]:
    """Get API key configuration status"""
    try:
        settings_data = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
        
        api_key = settings_data.get("gemini_api_key", "")
        
        return {
            "api_key_configured": bool(api_key and len(api_key) > 10),
            "api_key_preview": f"{api_key[:8]}..." if api_key and len(api_key) > 8 else ""
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API key status hatası: {str(e)}")

@router.put("/prompt")
async def update_ai_prompt(prompt_data: Dict[str, str]) -> Dict[str, Any]:
    """Update AI prompt"""
    try:
        prompt = prompt_data.get("prompt", "")
        
        # Read current settings
        current_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        
        # Update prompt
        current_settings["ai_prompt"] = prompt
        
        # Save to file
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": "AI prompt başarıyla güncellendi",
            "prompt": prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt güncelleme hatası: {str(e)}")

@router.get("/prompt")
async def get_ai_prompt() -> Dict[str, Any]:
    """Get current AI prompt"""
    try:
        settings_data = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
        
        prompt = settings_data.get("ai_prompt", "Content konusunu analiz et ve çekici bir post oluştur.")
        
        return {
            "prompt": prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt okuma hatası: {str(e)}")

@router.put("/schedule")
async def update_scrape_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update scraping schedule"""
    try:
        hour = schedule_data.get("hour", 7)
        minute = schedule_data.get("minute", 0)
        enabled = schedule_data.get("enabled", True)
        
        # Read current settings
        current_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        
        # Update schedule
        current_settings["scrape_schedule_hour"] = hour
        current_settings["scrape_schedule_minute"] = minute
        current_settings["auto_scrape_enabled"] = enabled
        
        # Save to file
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": "Tarama programı başarıyla güncellendi",
            "schedule": {
                "hour": hour,
                "minute": minute,
                "enabled": enabled
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule güncelleme hatası: {str(e)}")

@router.get("/schedule")
async def get_scrape_schedule() -> Dict[str, Any]:
    """Get current scraping schedule"""
    try:
        settings_data = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
        
        return {
            "hour": settings_data.get("scrape_schedule_hour", 7),
            "minute": settings_data.get("scrape_schedule_minute", 0),
            "enabled": settings_data.get("auto_scrape_enabled", True)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule okuma hatası: {str(e)}")

@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Get system statistics and scraper info"""
    try:
        # Import scraper service to get stats
        from app.services.scraper_service import scraper_service
        
        scraper_stats = scraper_service.get_stats()
        
        return {
            "scraper_stats": scraper_stats,
            "system_info": {
                "settings_file_exists": os.path.exists(SETTINGS_FILE),
                "current_time": "2025-01-09T18:30:00Z"
            }
        }
        
    except Exception as e:
        return {
            "error": f"Stats alınamadı: {str(e)}",
            "scraper_stats": {},
            "system_info": {
                "settings_file_exists": os.path.exists(SETTINGS_FILE),
                "current_time": "2025-01-09T18:30:00Z"
            }
        } 