"""
Reflection phase handler for the Orchestrator service.

This module handles the reflection phase of the Planner → Executor → Reflector workflow
where we ask Socratic questions about the draft content to deepen understanding.
"""
import json
from typing import Dict, Tuple, Any

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.db.models.section import Section as SectionModel
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService
from app.services.orchestrator.models import Phase, OrchestratorState


async def handle_reflection_phase(
    db: Session,
    session: SessionModel,
    state: OrchestratorState,
    message: str,
) -> Tuple[Dict[str, Any], OrchestratorState]:
    """
    Handle messages during the reflection phase.
    
    During this phase, we:
    1. Ask Socratic questions about the draft
    2. Store user's reflections in memory
    3. Mark section as saved
    4. Advance to next section
    
    This is where we complete the Planner → Executor → Reflector loop
    before moving on to the next section.
    
    Args:
        db: Database session
        session: Session model instance
        state: Current orchestrator state
        message: User message
        
    Returns:
        Tuple of (response, updated state)
    """
    print(f"Handling message in REFLECTION phase: {message[:50]}...")
    
    # Initialize services
    llm_service = LLMService()
    
    # Initialize memory service if needed
    if not hasattr(state, 'memory_service'):
        state.memory_service = MemoryService()
    
    # Store user's reflection in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="user", 
        content=message,
        categories=["reflection", state.current_section_id]
    )
    
    # Get draft content for this section
    draft_content = get_draft_from_memory(state)
    
    # Mark section as complete in database
    section_completed = mark_section_complete(db, state.session_id, state.current_section_id)
    
    # Generate Socratic questions about the draft
    # In a full implementation, we would call Claude here, but for now we'll use a placeholder
    response_text = "Thank you for your reflections. Let's move on to the next section."
    
    # Reset section ID to start planning the next section
    state.current_section_id = None
    
    # Transition back to planning phase for next section
    state.phase = Phase.PLANNING
    
    # Format response
    response = {
        "message": response_text,
        "metadata": {
            "phase": "planning",
            "section_completed": section_completed,
            "reflection_received": True
        }
    }
    
    # Store assistant message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="assistant", 
        content=response_text,
        categories=["reflection"]
    )
    
    return response, state


def get_draft_from_memory(state: OrchestratorState) -> str:
    """
    Get the draft content for the current section from memory.
    
    Args:
        state: Current orchestrator state
        
    Returns:
        Draft content as a string
    """
    try:
        # Search for draft content in memory
        results = state.memory_service.client.search(
            user_id=state.session_id,
            categories=["execution", state.current_section_id, "draft"],
            limit=1  # Get the most recent draft
        )
        
        # Extract draft content
        if results and isinstance(results, list) and len(results) > 0:
            for result in results:
                if isinstance(result, dict) and "content" in result:
                    return result.get("content", "")
    except Exception as e:
        print(f"Error retrieving draft: {e}")
    
    # Return empty string if not found
    return ""


def mark_section_complete(db: Session, session_id: str, section_id: str) -> bool:
    """
    Mark a section as complete in the database.
    
    Args:
        db: Database session
        session_id: Session ID
        section_id: Section ID (format: "chapter.section")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse section ID
        chapter_idx, section_idx = map(int, section_id.split('.'))
        
        # Find section in database
        section = db.query(SectionModel).filter(
            SectionModel.session_id == session_id,
            SectionModel.chapter_idx == chapter_idx,
            SectionModel.section_idx == section_idx
        ).first()
        
        if section:
            # Update status
            section.status = "complete"
            db.commit()
            print(f"Section {section_id} marked complete")
            return True
        else:
            print(f"Section {section_id} not found in database")
            return False
    except Exception as e:
        print(f"Error marking section complete: {e}")
        db.rollback()
        return False
