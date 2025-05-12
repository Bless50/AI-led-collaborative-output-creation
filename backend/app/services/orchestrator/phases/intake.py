"""
Intake phase handler for the Orchestrator service.

This module handles the initial phase of the Planner → Executor → Reflector workflow
where we gather basic requirements for the report from the user.
"""
import json
from typing import Dict, Tuple, Any

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.services.session_service import update_intake_response
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService
from app.services.orchestrator.models import Phase, OrchestratorState


async def handle_intake_phase(
    db: Session,
    session: SessionModel,
    state: OrchestratorState,
    message: str,
) -> Tuple[Dict[str, Any], OrchestratorState]:
    """
    Handle messages during the intake phase.
    
    During this phase, we:
    1. Gather basic requirements for the report
    2. Determine the topic, academic level, etc.
    3. Once intake is done, transition to planning phase
    
    Args:
        db: Database session
        session: Session model instance
        state: Current orchestrator state
        message: The user's message
        
    Returns:
        Tuple of (response, updated state)
    """
    print(f"Handling message in INTAKE phase: {message[:50]}...")
    
    # Initialize memory service if needed
    if not hasattr(state, 'memory_service'):
        state.memory_service = MemoryService()
    
    # Get existing intake JSON or initialize empty dict
    intake_json = session.intake_json or {}
    
    # Get guide JSON
    guide_json = session.guide_json
    
    # Initialize LLM service
    llm_service = LLMService()
    
    # Get previous messages to determine which field to update
    previous_messages = state.memory_service.get_intake_context(state.session_id)
    previous_question = ""
    
    if previous_messages and len(previous_messages) > 0:
        # Get the last message from the assistant
        for msg in reversed(previous_messages):
            if msg.get("role") == "assistant":
                previous_question = msg.get("content", "")
                break
                
        # Determine which field to update based on the last question
        from app.services.orchestrator.utils import determine_intake_field
        field_to_update = determine_intake_field(previous_question)
        
        # Update intake JSON
        if field_to_update:
            intake_json[field_to_update] = message
            
            # Update in database
            update_intake_response(db, session.session_id, intake_json)
    
    # Check if we should transition to planning phase
    # We'll transition if we have at least title and topic fields
    required_fields = ["title", "topic"]
    has_required_fields = all(field in intake_json for field in required_fields)
    
    # Store user message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="user", 
        content=message,
        categories=["intake"]
    )
    
    # Generate response from LLM
    response = await llm_service.generate_intake_response(
        session_id=state.session_id,
        guide_json=guide_json,
        intake_json=intake_json,
        message=message
    )
    
    # Store assistant message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="assistant", 
        content=response.get("message", ""),
        categories=["intake"]
    )
    
    # Check if the LLM indicated we should transition to planning
    transition_to_planning = False
    metadata = response.get("metadata", {})
    
    if metadata.get("complete_intake", False) or has_required_fields:
        transition_to_planning = True
    
    # Transition to planning phase if needed
    if transition_to_planning:
        print("Transitioning to PLANNING phase")
        state.phase = Phase.PLANNING
        
        # Add phase transition to response metadata
        response["metadata"]["phase"] = "planning"
    else:
        # Still in intake phase
        response["metadata"]["phase"] = "intake"
    
    return response, state
