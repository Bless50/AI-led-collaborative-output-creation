"""
Intake phase handler for the Orchestrator service.

This module handles the initial phase of the Planner → Executor → Reflector workflow
where we gather basic requirements for the report from the user.
"""
import json
from typing import Dict, Tuple, Any

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.services.session_service import store_intake_field
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
    
    # Initialize LLM service and import the generate_intake_response function
    llm_service = LLMService()
    from app.services.llm import generate_intake_response
    
    # Get previous messages to determine which field to update
    try:
        previous_messages = state.memory_service.get_intake_context(state.session_id)
        previous_question = ""
        
        # Add type checking and error handling
        if previous_messages and isinstance(previous_messages, list) and len(previous_messages) > 0:
            # Get the last message from the assistant
            for msg in reversed(previous_messages):
                # Make sure msg is a dictionary and has the expected attributes
                if isinstance(msg, dict) and "role" in msg and msg["role"] == "assistant":
                    previous_question = msg.get("content", "")
                    break
    except Exception as e:
        print(f"Error processing previous messages: {str(e)}")
        previous_question = ""  # Fail gracefully
    
    # Determine which field to update based on the last question
    field_to_update = None
    try:
        from app.services.orchestrator.utils import determine_intake_field
        field_to_update = determine_intake_field(previous_question)
    except Exception as e:
        print(f"Error determining field to update: {str(e)}")
    
    # Add this field to intake JSON collection
    if field_to_update:
        intake_json[field_to_update] = message
        
        # Store in database
        try:
            store_intake_field(db, session, field_to_update, message)
        except Exception as e:
            print(f"Error storing intake field: {str(e)}")
            # Continue execution even if storage fails
    
    # The LLM is primarily responsible for determining when intake is complete
    # We'll rely on Claude's determination, but do a basic check as a fallback
    required_fields = ["title", "department", "academic_level", "target_audience"]
    has_minimum_fields = "title" in intake_json  # Title is absolutely required
    
    # Store user message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="user", 
        content=message,
        categories=["intake"]
    )
    
    # Generate response from LLM
    try:
        # Call generate_intake_response as a standalone function
        response = await generate_intake_response(
            llm_service=llm_service,
            session_id=state.session_id,
            guide_json=guide_json,
            intake_json=intake_json,
            message=message
        )
    except Exception as e:
        print(f"Error generating LLM response: {str(e)}")
        # Provide a fallback response in case of LLM failure
        response = {
            "message": "I'm sorry, I'm having trouble processing your request. Could you please try again?",
            "metadata": {"phase": "intake"}
        }
    
    # Store assistant message in memory
    try:
        state.memory_service.add_message(
            session_id=state.session_id, 
            role="assistant", 
            content=response.get("message", ""),
            categories=["intake"]
        )
    except Exception as e:
        print(f"Error storing assistant message: {str(e)}")
        # Continue execution even if memory storage fails
    
    # Check if the LLM indicated we should transition to planning
    try:
        transition_to_planning = False
        metadata = response.get("metadata", {})
        
        print(f"DEBUG INTAKE: Processing metadata for phase transition: {metadata}")
        
        # Get requirements JSON if provided by Claude
        requirements_json = metadata.get("requirements_json", {})
        
        # If Claude provided structured requirements JSON, update multiple fields at once
        if requirements_json:
            print(f"DEBUG INTAKE: Received structured requirements JSON from Claude: {json.dumps(requirements_json, indent=2)}")
            
            # Update all fields in the requirements JSON
            for field, value in requirements_json.items():
                # Skip the complete_intake flag as it's not an actual field
                if field != "complete_intake":
                    # Store each field in the intake_json and database
                    intake_json[field] = value
                    try:
                        store_intake_field(db, session, field, value)
                        print(f"DEBUG INTAKE: Updated field '{field}' with value: {value}")
                    except Exception as e:
                        print(f"ERROR: Failed to store field '{field}': {str(e)}")
        
        # Check for complete_intake flag in the API metadata
        api_complete_intake = metadata.get("complete_intake", False)
        print(f"DEBUG INTAKE: API complete_intake flag is: {api_complete_intake}")
        
        # NEW: Also check for completion signals embedded in message content
        message_content = response.get("message", "")
        print(f"DEBUG INTAKE: Checking message content for embedded completion signals")
        
        # Look for JSON-like patterns indicating completion
        message_indicates_completion = False
        import re
        completion_patterns = [
            r'"complete_intake"\s*:\s*true',   # Standard JSON format
            r"'complete_intake'\s*:\s*true",   # Single quotes
            r"we have.*information",            # Natural language indicators
            r"ready to.*proceed",
            r"ready to.*start",
            r"start.*planning",
            r"move to.*next phase"
        ]
        
        for pattern in completion_patterns:
            if re.search(pattern, message_content, re.IGNORECASE):
                print(f"DEBUG INTAKE: Found completion signal in message: {pattern}")
                message_indicates_completion = True
                break
        
        # Check if we have the minimum necessary fields
        has_title = "title" in intake_json and intake_json["title"]
        
        # Transition to planning if (1) API says complete, OR (2) message indicates complete, OR (3) we at least have a title
        # Claude is now the primary authority on when intake is complete
        transition_to_planning = api_complete_intake or message_indicates_completion or has_title
        
        # Transition to planning phase if needed
        if transition_to_planning:
            print("========== Transitioning to PLANNING phase ===========")
            print(f"DEBUG INTAKE: Before transition - state.phase={state.phase}")
            state.phase = Phase.PLANNING
            print(f"DEBUG INTAKE: After transition - state.phase={state.phase}")
            print(f"DEBUG INTAKE: State object ID after transition: {id(state)}")
            print("=====================================================")
            
            # Add phase transition to response metadata
            if isinstance(response, dict) and isinstance(response.get("metadata"), dict):
                response["metadata"]["phase"] = "planning"
            else:
                # Ensure response has the right structure
                response = {
                    "message": response.get("message", "I'll help you plan your report."),
                    "metadata": {"phase": "planning"}
                }
        else:
            print("DEBUG INTAKE: Not transitioning to planning phase yet, staying in intake")
            # When we're clearly ready but something is preventing transition
            if message_indicates_completion and not transition_to_planning:
                print("IMPORTANT: Claude indicates completion in message but transition conditions prevent it!")
                print("DEBUG INTAKE: Consider using /complete_intake command if you're stuck in intake")
            
            # Still in intake phase
            if isinstance(response, dict) and isinstance(response.get("metadata"), dict):
                response["metadata"]["phase"] = "intake"
            else:
                # Ensure response has the right structure
                response = {
                    "message": response.get("message", "Let's continue gathering information."),
                    "metadata": {"phase": "intake"}
                }
    except Exception as e:
        print(f"Error handling phase transition: {str(e)}")
        # Provide a fallback response
        response = {
            "message": "I'm processing your request. Could you tell me more about your report requirements?",
            "metadata": {"phase": "intake"}
        }
    
    return response, state
