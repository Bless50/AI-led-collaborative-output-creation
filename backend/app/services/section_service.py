from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.db.models.section import Section as SectionModel


def get_section(
    db: Session,
    session_id: str,
    chapter_idx: int,
    section_idx: int
) -> Optional[SectionModel]:
    """
    Get a section by session ID, chapter index, and section index.
    
    Args:
        db: Database session
        session_id: Session ID
        chapter_idx: Chapter index
        section_idx: Section index
        
    Returns:
        Section model or None if not found
    """
    return db.query(SectionModel).filter(
        SectionModel.session_id == session_id,
        SectionModel.chapter_idx == chapter_idx,
        SectionModel.section_idx == section_idx
    ).first()


def get_sections_by_session_id(
    db: Session,
    session_id: str
) -> List[SectionModel]:
    """
    Get all sections for a session.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        List of section models
    """
    return db.query(SectionModel).filter(
        SectionModel.session_id == session_id
    ).order_by(
        SectionModel.chapter_idx,
        SectionModel.section_idx
    ).all()


def get_sections_by_chapter(
    db: Session,
    session_id: str,
    chapter_idx: int
) -> List[SectionModel]:
    """
    Get all sections for a chapter.
    
    Args:
        db: Database session
        session_id: Session ID
        chapter_idx: Chapter index
        
    Returns:
        List of section models
    """
    return db.query(SectionModel).filter(
        SectionModel.session_id == session_id,
        SectionModel.chapter_idx == chapter_idx
    ).order_by(
        SectionModel.section_idx
    ).all()


def update_section_draft(
    db: Session,
    session_id: str,
    chapter_idx: int,
    section_idx: int,
    draft_html: str
) -> bool:
    """
    Update a section's draft HTML.
    
    Args:
        db: Database session
        session_id: Session ID
        chapter_idx: Chapter index
        section_idx: Section index
        draft_html: HTML content with inline citations and references
        
    Returns:
        True if successful, False otherwise
    """
    section = get_section(db, session_id, chapter_idx, section_idx)
    if not section:
        return False
    
    section.draft_html = draft_html
    db.commit()
    db.refresh(section)
    
    return True


def save_section(
    db: Session,
    session_id: str,
    chapter_idx: int,
    section_idx: int
) -> bool:
    """
    Mark a section as saved.
    
    Args:
        db: Database session
        session_id: Session ID
        chapter_idx: Chapter index
        section_idx: Section index
        
    Returns:
        True if successful, False otherwise
    """
    section = get_section(db, session_id, chapter_idx, section_idx)
    if not section:
        return False
    
    section.status = "saved"
    section.saved_at = datetime.now()
    db.commit()
    db.refresh(section)
    
    return True


def get_next_pending_section(
    db: Session,
    session_id: str
) -> Optional[SectionModel]:
    """
    Get the next pending section for a session.
    
    This function returns the first pending section in chapter/section order.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        Next pending section or None if all sections are saved
    """
    return db.query(SectionModel).filter(
        SectionModel.session_id == session_id,
        SectionModel.status == "pending"
    ).order_by(
        SectionModel.chapter_idx,
        SectionModel.section_idx
    ).first()
