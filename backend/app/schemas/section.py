from typing import Optional

from pydantic import BaseModel, Field


class SectionBase(BaseModel):
    """
    Base schema for section operations
    """
    chapter_idx: int = Field(..., description="Chapter index (0-based)")
    section_idx: int = Field(..., description="Section index within chapter (0-based)")


class SectionSave(SectionBase):
    """
    Schema for saving a section
    """
    pass


class SectionResponse(SectionBase):
    """
    Schema for section response
    """
    session_id: str
    status: str
    draft_html: Optional[str] = None

    class Config:
        from_attributes = True
