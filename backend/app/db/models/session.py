import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, JSON, String
from sqlalchemy.sql import func

from app.db.base_class import Base


class Session(Base):
    """
    Session model for storing guide information and intake data.
    
    This model represents a user session for report generation.
    It stores the parsed guide JSON, intake responses, and session expiration.
    """
    session_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    guide_json = Column(JSON, nullable=False)
    intake_json = Column(JSON, nullable=False, default="{}")
    intake_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    # No expiration to prevent data loss
