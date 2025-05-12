import json
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.db.models.section import Section as SectionModel
from app.schemas.session import SessionCreate, SessionState


def create_session(db: Session, session_data: SessionCreate) -> SessionModel:
    """
    Create a new session with guide JSON.
    
    This function creates a new session in the database and initializes
    section records for each section in the guide.
    
    Args:
        db: Database session
        session_data: Session data with guide_json
        
    Returns:
        Created session model
    """
    # Create session
    session = SessionModel(
        guide_json=session_data.guide_json,
        intake_json={}
    )
    db.add(session)
    db.flush()  # Flush to get session_id
    
    # Create section records
    _initialize_sections(db, session)
    
    # Commit changes
    db.commit()
    db.refresh(session)
    
    return session


def get_session_by_id(db: Session, session_id: str) -> Optional[SessionModel]:
    """
    Get a session by ID.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        Session model or None if not found
    """
    return db.query(SessionModel).filter(SessionModel.session_id == session_id).first()


def get_session_state(db: Session, session: SessionModel) -> SessionState:
    """
    Get the current state of a session.
    
    This function returns the session's guide JSON, intake JSON, intake status,
    and the status of all sections.
    
    Args:
        db: Database session
        session: Session model
        
    Returns:
        SessionState with session data
    """
    # Get section statuses
    sections = db.query(SectionModel).filter(
        SectionModel.session_id == session.session_id
    ).all()
    
    # Create map of "chapter_idx.section_idx" to status
    sections_status = {
        f"{section.chapter_idx}.{section.section_idx}": section.status
        for section in sections
    }
    
    # Return session state
    return SessionState(
        session_id=session.session_id,
        guide_json=session.guide_json,
        intake_json=session.intake_json,
        intake_done=session.intake_done,
        sections_status=sections_status,
        created_at=session.created_at
        # No expiration to prevent data loss
    )


def update_intake_response(
    db: Session,
    session: SessionModel,
    field: str,
    value: Any
) -> bool:
    """
    Update an intake response field.
    
    This function updates a field in the session's intake_json and
    checks if all required intake fields are now complete.
    
    Args:
        db: Database session
        session: Session model
        field: Field name in intake_json
        value: Value for the field
        
    Returns:
        True if all required intake fields are now complete, False otherwise
    """
    # Update intake_json
    intake_json = dict(session.intake_json)
    intake_json[field] = value
    session.intake_json = intake_json
    
    # Check if all required fields are present
    required_fields = [
        "title",
        "department",
        "objectives",
        "problem_statement",
        "sample_size"
    ]
    
    all_fields_present = all(field in intake_json for field in required_fields)
    
    # Update intake_done if all fields are present
    if all_fields_present and not session.intake_done:
        session.intake_done = True
    
    # Commit changes
    db.commit()
    db.refresh(session)
    
    return session.intake_done


def _initialize_sections(db: Session, session: SessionModel) -> None:
    """
    Initialize section records for a session.
    
    This function creates a section record for each section in the guide.
    
    Args:
        db: Database session
        session: Session model
    """
    guide_json = session.guide_json
    
    # Create section records for each chapter and section
    for chapter_idx, chapter in enumerate(guide_json.get("chapters", [])):
        for section_idx, _ in enumerate(chapter.get("sections", [])):
            section = SectionModel(
                session_id=session.session_id,
                chapter_idx=chapter_idx,
                section_idx=section_idx,
                status="pending"
            )
            db.add(section)
 