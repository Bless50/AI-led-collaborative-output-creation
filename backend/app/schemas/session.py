from datetime import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """
    Schema for creating a new session from a guide file
    """
    guide_json: Dict[str, Any] = Field(..., description="Parsed guide JSON with chapters and sections")


class SessionState(BaseModel):
    """
    Schema for returning the current state of a session
    """
    session_id: str
    guide_json: Dict[str, Any]
    intake_json: Dict[str, Any]
    intake_done: bool
    sections_status: Dict[str, str] = Field(..., description="Map of 'chapter_idx.section_idx' to status ('pending' or 'saved')")
    created_at: datetime
    # No expiration to prevent data loss

    class Config:
        from_attributes = True


class IntakeResponse(BaseModel):
    """
    Schema for updating intake responses
    """
    field: str = Field(..., description="Field name in the intake_json")
    value: Any = Field(..., description="Value for the field")


class ChatMessage(BaseModel):
    """
    Schema for chat messages
    """
    role: str = Field(..., description="Role of the message sender ('user' or 'assistant')")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """
    Schema for chat requests
    """
    message: str = Field(..., description="User message")


class ChatResponse(BaseModel):
    """
    Schema for chat responses
    """
    message: str = Field(..., description="Assistant message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the frontend")
