"""
State management for the Orchestrator service.

This module provides an interface for persisting orchestrator state.
It delegates the actual database operations to the state_db module to avoid
circular imports while maintaining a clean API for other orchestrator components.
"""
from typing import Optional
from contextlib import contextmanager

from app.db.session import SessionLocal
from app.services.state_db import save_state_to_db, load_state_from_db
# Import OrchestratorState using relative import to avoid circular imports
from app.services.orchestrator.models import OrchestratorState


def save_orchestrator_state(state: OrchestratorState) -> None:
    """
    Save orchestrator state to the database.
    
    This function converts the OrchestratorState object to a dictionary and
    delegates the actual database operation to the state_db module.
    
    Args:
        state: OrchestratorState to save
    """
    try:
        # Open a database session
        with get_db() as db:
            # Convert state to dictionary and save to database
            state_dict = state.to_dict()
            success = save_state_to_db(db, state.session_id, state_dict)
            
            # Debug log
            if success:
                print(f"State saved to database: phase={state.phase}, section={state.current_section_id}")
            else:
                print(f"Failed to save state to database for session {state.session_id}")
    except Exception as e:
        # Log error but continue execution
        print(f"Error saving orchestrator state: {e}")


def load_orchestrator_state(session_id: str) -> Optional[OrchestratorState]:
    """
    Load orchestrator state from the database.
    
    This function retrieves the state dictionary from the database via the
    state_db module and converts it to an OrchestratorState object if found.
    
    Args:
        session_id: Session ID
        
    Returns:
        OrchestratorState if found, None otherwise
    """
    try:
        # Open a database session
        with get_db() as db:
            # Load state dictionary from database
            state_dict = load_state_from_db(db, session_id)
            
            # If state was found, convert to OrchestratorState object and return
            if state_dict:
                state = OrchestratorState.from_dict(state_dict)
                print(f"State loaded from database: phase={state.phase}, section={state.current_section_id}")
                return state
    except Exception as e:
        print(f"Error loading orchestrator state from database: {e}")
    
    print(f"No state found for session {session_id}, creating new state")
    return None


@contextmanager
def get_db():
    """Database session context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
