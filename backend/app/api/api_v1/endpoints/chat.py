from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.session import ChatRequest, ChatResponse
from app.services.session_service import get_session_by_id
from app.services.orchestrator_service import process_chat_message

router = APIRouter()


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_with_orchestrator(
    session_id: str,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Process a chat message through the orchestrator.
    
    This endpoint handles the AI-driven conversation flow, including:
    - Intake phase (collecting metadata)
    - Section phase (bullets → draft → reflection)
    
    The orchestrator follows the Planner → Executor → Reflector loop
    and uses mem0 for context management.
    
    Args:
        session_id: The session ID
        chat_request: The user's chat message
        db: Database session
        
    Returns:
        ChatResponse with assistant message and metadata
        
    Raises:
        HTTPException: If the session is not found or an error occurs
    """
    # Get session
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    try:
        # Process message through orchestrator
        response = await process_chat_message(
            db=db,
            session_id=session_id,
            message=chat_request.message
        )
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {str(e)}"
        )


@router.post("/{session_id}/save-section", response_model=Dict[str, bool])
async def save_section(
    session_id: str,
    chapter_idx: int,
    section_idx: int,
    db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """
    Save a section after it has been drafted and reviewed.
    
    This endpoint marks a section as saved and sets the saved_at timestamp.
    
    Args:
        session_id: The session ID
        chapter_idx: The chapter index
        section_idx: The section index
        db: Database session
        
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If the session or section is not found
    """
    from app.services.section_service import save_section
    
    # Get session
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    try:
        # Save section
        success = save_section(
            db=db,
            session_id=session_id,
            chapter_idx=chapter_idx,
            section_idx=section_idx
        )
        
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving section: {str(e)}"
        )
