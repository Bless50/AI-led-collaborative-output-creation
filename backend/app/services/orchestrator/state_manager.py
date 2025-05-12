"""
State management for the Orchestrator service.

This module contains functions for persisting orchestrator state to mem0
and retrieving it. Using mem0 allows us to maintain state between API calls
without relying on additional database tables.
"""
import json
from typing import Optional

from app.services.memory_service import MemoryService
# Import OrchestratorState using relative import to avoid circular imports
from app.services.orchestrator.models import OrchestratorState


def save_orchestrator_state(state: OrchestratorState) -> None:
    """
    Save orchestrator state to memory.
    
    We store the orchestrator state in mem0 with a special category to distinguish
    it from regular conversation messages. This allows us to maintain state
    between requests without using a separate database table.
    
    Args:
        state: OrchestratorState to save
    """
    try:
        # Initialize memory service if not already in state
        if not hasattr(state, 'memory_service'):
            state.memory_service = MemoryService()
        
        # Convert state to dictionary
        state_dict = state.to_dict()
        
        # Save state to mem0
        # Use messages format as required by mem0 API
        state.memory_service.client.add(
            messages=[{
                "role": "system",
                "content": json.dumps(state_dict)
            }],
            user_id=state.session_id,
            categories=["orchestrator_state"]
        )
        
        # Debug log
        print(f"State saved: phase={state.phase}, section={state.current_section_id}")
    except Exception as e:
        # Log error but continue execution
        print(f"Error saving orchestrator state: {e}")
        pass


def load_orchestrator_state(session_id: str) -> Optional[OrchestratorState]:
    """
    Load orchestrator state from memory.
    
    We store the orchestrator state in mem0 with a special tag to distinguish
    it from regular conversation messages. This allows us to maintain state
    between requests without using a separate database table.
    
    Args:
        session_id: Session ID
        
    Returns:
        OrchestratorState if found, None otherwise
    """
    try:
        # Initialize memory service
        memory_service = MemoryService()
        
        # Get all memories directly using the user_id without filtering
        # We'll manually look for the orchestrator state tag
        try:
            # Print the results for debugging
            print("Fetching orchestrator state from mem0...")
            results = memory_service.client.get_all(
                user_id=session_id
            )
            print(f"Results type: {type(results)}, data: {results[:100] if isinstance(results, list) else results}")
            
            # If we get a valid list of results, try to find orchestrator state
            if results and isinstance(results, list):
                for entry in results:
                    if isinstance(entry, dict):
                        # For dictionary entries, look for orchestrator_state in categories
                        categories = entry.get("categories", [])
                        if isinstance(categories, list) and "orchestrator_state" in categories:
                            try:
                                state_data = entry.get("content", "{}")
                                state_dict = json.loads(state_data)
                                
                                # Create and return state object
                                state = OrchestratorState.from_dict(state_dict)
                                print(f"State loaded: phase={state.phase}, section={state.current_section_id}")
                                return state
                            except (json.JSONDecodeError, AttributeError) as e:
                                print(f"Error parsing state data: {e}")
                                continue
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            pass
    except Exception as e:
        print(f"Error loading orchestrator state: {e}")
        # Silently fail and create a new state
        pass
    
    print("No state found, creating new state")
    return None
