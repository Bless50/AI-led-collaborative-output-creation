
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class Section(Base):
    """
    Section model for storing section drafts and status.
    
    This model represents a section of a report, storing the draft HTML
    content (including inline citations and references) and the section status.
    """
    # Composite primary key: session_id, chapter_idx, section_idx
    session_id = Column(String, ForeignKey("session.session_id", ondelete="CASCADE"), primary_key=True)
    chapter_idx = Column(Integer, primary_key=True)
    section_idx = Column(Integer, primary_key=True)
    
    # Section status: 'pending' or 'saved'
    status = Column(
        String, 
        default="pending",
        nullable=False
    )
    
    # HTML content with inline citations and references
    draft_html = Column(Text, nullable=True)
    
    # Timestamp when the section was saved
    saved_at = Column(DateTime, nullable=True)
    
    @property
    def is_saved(self) -> bool:
        """Check if the section has been saved"""
        return self.status == "saved"
    
    def save(self) -> None:
        """Mark the section as saved and set the saved_at timestamp"""
        self.status = "saved"
        self.saved_at = func.now()
