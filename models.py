from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class StoryCreate(BaseModel):
    """Schema for submitting a new story"""
    title: Optional[str] = Field(None, max_length=255)  # NEW
    author_name: Optional[str] = Field(None, max_length=255)
    author_email: Optional[EmailStr] = None
    story_text: str = Field(..., min_length=10, max_length=10000)
    category: str

class StoryResponse(BaseModel):
    """Schema for returning a story to the frontend"""
    id: int
    title: Optional[str]  # NEW
    author_name: Optional[str]
    story_text: str
    category: str
    created_at: datetime
    approved: bool = False
    
    class Config:
        from_attributes = True

class StoryAdmin(StoryResponse):
    """Admin view includes email"""
    author_email: Optional[str]
