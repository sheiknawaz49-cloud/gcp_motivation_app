from typing import List, Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    action: str = Field(..., description="Action type: 'like' or 'dislike'")
    quote: str = Field("", description="The quote text being rated")


class CardItem(BaseModel):
    quote: str
    audio_url: str


class BatchResponse(BaseModel):
    streak: int
    cards: List[CardItem]


class UserProfile(BaseModel):
    name: str
    goal: str = "Daily growth"
    last_mood: str = "focused"
    preferred_voice: str = "female"
    streak: int = 1
    last_quote: Optional[str] = ""
    audio_url: Optional[str] = ""
    liked_quotes: List[str] = []
    disliked_quotes: List[str] = []
    updated_at: Optional[str] = None

class TTSRequest(BaseModel):
    quote: str


class MobileContextRequest(BaseModel):
    app_usage_context: str = Field(..., description="Mobile app context or screen-time summary")