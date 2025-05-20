"""
Database operations for orchestrator state persistence.

This module handles the database operations for saving and loading
orchestrator state, keeping these operations separate from the session service
to avoid circular imports.
"""
import json
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel


def save_state_to_db(db: Session, session_id: str, state_dict: Dict[str, Any]) -> bool:
    """
    Save orchestrator state dictionary to the database.
    
    Args:
        db: Database session
        session_id: Session ID
        state_dict: State dictionary to save
        
    Returns:
        True if state was successfully saved, False otherwise
    """
    print(f"DEBUG: Beginning state save for session {session_id}")
    print(f"DEBUG: State to save: {state_dict}")
    
    try:
        # Get session
        print(f"DEBUG: Querying database for session {session_id}")
        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        print(f"DEBUG: Query completed, session found: {session is not None}")
        
        if not session:
            print(f"Session with ID {session_id} not found when saving state")
            return False
        
        # Save state to database
        print(f"DEBUG: Saving state to session.state_json")
        session.state_json = state_dict
        
        print(f"DEBUG: Committing transaction to database")
        db.commit()
        print(f"DEBUG: Transaction committed successfully")
        
        # Verify the saved state
        db.refresh(session)
        print(f"DEBUG: Verified saved state: {session.state_json}")
        
        # Debug log
        phase = state_dict.get('phase', 'unknown')
        print(f"State saved to database for session {session_id}, phase: {phase}")
        return True
    except Exception as e:
        # Log error but continue execution
        import traceback
        print(f"Error saving orchestrator state to database: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        
        # Attempt to roll back the transaction
        try:
            print(f"DEBUG: Rolling back transaction")
            db.rollback()
            print(f"DEBUG: Rollback completed")
        except Exception as rollback_error:
            print(f"DEBUG: Error during rollback: {rollback_error}")
            
        return False


def load_state_from_db(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load orchestrator state dictionary from the database.
    
    Args:
        db: Database session
        session_id: Session ID
        
    Returns:
        State dictionary if found, None otherwise
    """
    print(f"DEBUG: Beginning state load for session {session_id}")
    try:
        # Get session
        print(f"DEBUG: Querying database for session {session_id}")
        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        print(f"DEBUG: Query completed, session found: {session is not None}")
        
        if not session:
            print(f"Session with ID {session_id} not found when loading state")
            return None
        
        # Get state from database
        print(f"DEBUG: Retrieving state_json from session object")
        state_dict = session.state_json
        print(f"DEBUG: state_json type: {type(state_dict)}, value: {state_dict}")
        
        # If no state is stored yet, return None
        if not state_dict:
            print(f"No state found for session {session_id}")
            return None
        
        print(f"State loaded from database for session {session_id}, phase: {state_dict.get('phase', 'unknown')}")
        return state_dict
    except Exception as e:
        import traceback
        print(f"Error loading orchestrator state from database: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return None
