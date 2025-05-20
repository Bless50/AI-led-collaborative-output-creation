import json
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.db.models.section import Section as SectionModel
from app.schemas.session import SessionCreate, SessionState
# Note: We no longer import from orchestrator to break circular dependency


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


def store_intake_field(
    db: Session,
    session: SessionModel,
    field: str,
    value: Any
) -> bool:
    """
    Store a field from the intake conversation.
    
    This function stores a report requirement field in the session's intake_json
    and checks if all required intake fields are now complete.
    
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
    
    # We no longer check for predefined required fields
    # The intake completion is controlled by Claude's decisions
    # The intake_done flag is now just an informational field
    # that will be set by the orchestrator service when it decides
    # to move to the next phase
    
    # For now we don't modify the intake_done flag here
    
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
    try:
        # Get chapters from guide
        guide_json = session.guide_json
        chapters = guide_json.get("chapters", [])
        
        # Create section records for each section in the guide
        for chapter_idx, chapter in enumerate(chapters):
            sections = chapter.get("sections", [])
            for section_idx, section in enumerate(sections):
                db_section = SectionModel(
                    session_id=session.session_id,
                    chapter_idx=chapter_idx,
                    section_idx=section_idx,
                    title=section.get("title", ""),
                    content="",  # Initially empty
                    status="pending"  # Start as pending
                )
                db.add(db_section)
    except Exception as e:
        print(f"Error initializing sections: {str(e)}")


# Orchestrator state functions have been moved to state_db.py to avoid circular imports