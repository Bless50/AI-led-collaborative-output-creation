"""
Planning phase handler for the Orchestrator service.

This module handles the planning phase of the Planner → Executor → Reflector workflow
where we identify and plan content for specific sections of the report.
"""
import json
import re
from typing import Dict, Tuple, Any, List

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService
from app.services.orchestrator.models import Phase, OrchestratorState
from app.services.orchestrator.utils import extract_section_from_guide


async def handle_planning_phase(
    db: Session,
    session: SessionModel,
    state: OrchestratorState,
    message: str,
) -> Tuple[Dict[str, Any], OrchestratorState]:
    """
    Handle messages during the planning phase.
    
    During this phase, we:
    1. Identify next section to work on
    2. Ask for bullet points
    3. Store bullets in memory
    
    Why use mem0 here?
    - Allows us to maintain complex state (like bullet points) without custom database tables
    - Semantic search makes it easy to retrieve relevant context
    - Works well with our stateless API design
    
    Args:
        db: Database session
        session: Session model instance
        state: Current orchestrator state
        message: User message
        
    Returns:
        Tuple of (response, updated state)
    """
    print(f"Handling message in PLANNING phase: {message[:50]}...")
    
    # Initialize services
    llm_service = LLMService()
    
    # Initialize memory service if needed
    if not hasattr(state, 'memory_service'):
        state.memory_service = MemoryService()
    
    # Get session information
    guide_json = session.guide_json
    intake_json = session.intake_json
    
    # Store user message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="user", 
        content=message,
        categories=["planning"]
    )
    
    # Check if we have a current section
    if state.current_section_id:
        # We're working on a section, so process bullets
        section_info = extract_section_from_guide(guide_json, state.current_section_id)
        
        # Extract bullet points from the message
        bullet_points = extract_bullet_points(message)
        
        # Store bullet points in memory
        state.memory_service.add_message(
            session_id=state.session_id,
            role="system",
            content=json.dumps({
                "section_id": state.current_section_id,
                "bullet_points": bullet_points,
            }),
            categories=["bullet_points", state.current_section_id]
        )
        
        # Transition to execution phase
        state.phase = Phase.EXECUTION
        
        # Generate response
        response = {
            "message": f"Great! I've captured your bullet points for the section '{section_info.get('section_title')}'. Let me generate a draft based on these points.",
            "metadata": {
                "phase": "execution",
                "section_id": state.current_section_id,
                "bullet_points": bullet_points
            }
        }
    else:
        # We need to identify the next section to work on
        # In a real implementation, we'd query the database to find the next unfinished section
        # For now, we'll use a simple algorithm to identify the first section
        
        # Find the next section
        next_section_id = find_next_section(guide_json)
        state.current_section_id = next_section_id
        
        # Get section details
        section_info = extract_section_from_guide(guide_json, next_section_id)
        
        # Generate response from LLM for the planning phase
        response = await llm_service.generate_planner_response(
            session_id=state.session_id,
            guide_json=guide_json,
            intake_json=intake_json,
            current_section_id=next_section_id,
            db=db,
            message=message
        )
        
        # Store assistant message in memory
        state.memory_service.add_message(
            session_id=state.session_id, 
            role="assistant", 
            content=response.get("message", ""),
            categories=["planning", next_section_id]
        )
        
        # Add section_id to metadata
        response["metadata"]["section_id"] = next_section_id
    
    return response, state


def extract_bullet_points(message: str) -> List[str]:
    """
    Extract bullet points from a user message.
    
    Supports various formats: -, *, •, numbers, etc.
    
    Args:
        message: User message containing bullet points
        
    Returns:
        List of extracted bullet points
    """
    # Split message into lines
    lines = message.strip().split('\n')
    
    # Patterns for bullet points
    bullet_patterns = [
        r'^\s*[-•*]\s+(.+)$',  # Matches: - bullet, • bullet, * bullet
        r'^\s*(\d+[.)])\s+(.+)$',  # Matches: 1. bullet, 1) bullet
    ]
    
    bullets = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        is_bullet = False
        for pattern in bullet_patterns:
            match = re.match(pattern, line)
            if match:
                is_bullet = True
                # If it's a numbered bullet, get the second group
                if len(match.groups()) > 1:
                    bullets.append(match.group(2))
                else:
                    bullets.append(match.group(1))
                break
                
        # If the line doesn't match a bullet pattern but we have bullets already,
        # assume it's a continuation of the previous bullet
        if not is_bullet and bullets and not re.match(r'^\s*$', line):
            if len(line) > 3:  # Avoid adding very short lines
                bullets.append(line)
    
    return bullets


def find_next_section(guide_json: Dict[str, Any]) -> str:
    """
    Find the next section ID to work on.
    
    This is a simple implementation that returns the first section.
    In a real implementation, we'd query the database to find incomplete sections.
    
    Args:
        guide_json: Guide JSON structure
        
    Returns:
        Section ID in format "chapter.section"
    """
    # For now, just return the first section of the first chapter
    if guide_json.get("chapters") and len(guide_json["chapters"]) > 0:
        chapter = guide_json["chapters"][0]
        if chapter.get("sections") and len(chapter["sections"]) > 0:
            return "0.0"
    
    # Default if no sections found
    return "0.0"
