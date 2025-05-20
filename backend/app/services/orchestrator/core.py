"""
Core functionality for the Orchestrator service.

This module contains the main entry point (process_chat_message) for handling user messages
and utility functions used across different phases of the Planner → Executor → Reflector workflow.
"""
import json
from typing import Dict, Any, Tuple, Optional

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.services.session_service import get_session_by_id, store_intake_field
from app.services.orchestrator.models import Phase, OrchestratorState
from app.services.state_db import save_state_to_db, load_state_from_db
from app.services.orchestrator.utils import extract_section_from_guide, determine_intake_field

# Import phase handlers - will be moved to separate modules
from app.services.orchestrator.phases.intake import handle_intake_phase
from app.services.orchestrator.phases.planning import handle_planning_phase
from app.services.orchestrator.phases.execution import handle_execution_phase
from app.services.orchestrator.phases.reflection import handle_reflection_phase


async def process_chat_message(
    db: Session,
    session_id: str,
    message: str,
) -> Dict[str, Any]:
    """
    Process a chat message from the user and generate a response.
    
    This is the main entry point for the orchestrator service.
    It determines the current phase, routes the message to the appropriate handler,
    and returns the response.
    
    The function follows these steps:
    1. Load the session and state information
    2. Process the message through the appropriate phase handler
    3. Save the updated state
    4. Return the response to the client
    
    Args:
        db: Database session
        session_id: Session ID
        message: User message
        
    Returns:
        Dict containing the AI response and updated state
    """
    # Get session
    session = get_session_by_id(db, session_id)
    if not session:
        # Return properly formatted error response matching ChatResponse schema
        return {
            "message": f"Session with ID {session_id} not found",
            "metadata": {
                "phase": "error",
                "error": "session_not_found"
            }
        }
        
    # Special command handling
    if message.strip().lower() == "force-complete-intake":
        # Special command for testing to force completion of the intake phase
        state_dict = load_state_from_db(db, session_id)
        state = OrchestratorState.from_dict(state_dict) if state_dict else OrchestratorState(session_id)
        state.phase = Phase.PLANNING
        save_state_to_db(db, session_id, state.to_dict())
        return {
            "message": "Intake phase forced to complete. Transitioning to planning phase.",
            "metadata": {
                "phase": "planning",
                "section_id": None
            }
        }
        
    # Load state from database or create new state
    state_dict = load_state_from_db(db, session_id)
    
    # Create state object from dictionary or create new state if not found
    if state_dict:
        state = OrchestratorState.from_dict(state_dict)
    else:
        # Create new state in intake phase
        state = OrchestratorState(session_id)
        
    # Print debug info about the current state
    print(f"Current state: phase={state.phase}, section={state.current_section_id}")
    
    # Process message based on current phase
    response = None
    updated_state = None
    
    if state.phase == Phase.INTAKE:
        response, updated_state = await handle_intake_phase(db, session, state, message)
    elif state.phase == Phase.PLANNING:
        response, updated_state = await handle_planning_phase(db, session, state, message)
    elif state.phase == Phase.EXECUTION:
        response, updated_state = await handle_execution_phase(db, session, state, message)
    elif state.phase == Phase.REFLECTION:
        response, updated_state = await handle_reflection_phase(db, session, state, message)
    else:
        # Unknown phase - return error
        response = {
            "message": f"Unknown phase: {state.phase}",
            "metadata": {
                "phase": "error",
                "error": "unknown_phase"
            }
        }
        updated_state = state
        
    # Make sure we have a valid state to save
    if updated_state:
        # Save updated state to database
        save_state_to_db(db, session_id, updated_state.to_dict())
        
    return response


# extract_section_from_guide function moved to utils.py


# determine_intake_field function moved to utils.py
