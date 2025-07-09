from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.scraper_service import scraper_service

router = APIRouter()

class TwitterLoginRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    email_password: str | None = None


@router.post("/login")
async def twitter_login(req: TwitterLoginRequest):
    """Kullanıcıdan alınan bilgilerle TwScrape login yapar."""
    result = await scraper_service.twitter_login(
        req.username, req.password, req.email, req.email_password
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Login failed")) 