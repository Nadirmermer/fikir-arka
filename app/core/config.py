"""
Configuration settings for Content Manager API v2.0.0
Environment-based configuration with Pydantic
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    """Uygulama genelindeki ayarları yönetir."""
    # App
    app_name: str = "Content Manager API"
    app_version: str = "2.0.0"
    debug: bool = True
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/content_manager.db"
    db_echo: bool = False

    # AI
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    default_ai_model: str = "gemini-2.5-flash"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 2000
    
    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"]

    # Scheduler defaults
    scheduler_timezone: str = "Europe/Istanbul"
    scrape_schedule_hour: int = 7  # 07:00 AM
    scrape_schedule_minute: int = 0

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8',
        case_sensitive=True,
        populate_by_name=True
    )

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Environment helper
def is_development() -> bool:
    """Check if running in development mode"""
    return get_settings().debug

def is_production() -> bool:
    """Check if running in production mode"""
    return not is_development()

# Database path helper
def get_database_path() -> str:
    """Get absolute database file path"""
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        return settings.database_url.replace("sqlite:///", "")
    return str(BASE_DIR / "data" / "content_manager.db")

def ensure_data_directory():
    """Veri (data) klasörünün var olduğundan emin olur."""
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir() 