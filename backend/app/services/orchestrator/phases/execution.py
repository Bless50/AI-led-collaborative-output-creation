"""
Execution phase handler for the Orchestrator service.

This module handles the execution phase of the Planner → Executor → Reflector workflow
where we generate draft content based on bullet points and web search results.
"""
import json
from typing import Dict, List, Tuple, Any, Optional

from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionModel
from app.db.models.section import Section as SectionModel
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService
from app.services.orchestrator.models import Phase, OrchestratorState
from app.services.orchestrator.utils import extract_section_from_guide

# This will be imported once implemented
# from app.services.search_service import perform_web_search


async def handle_execution_phase(
    db: Session,
    session: SessionModel,
    state: OrchestratorState,
    message: str,
) -> Tuple[Dict[str, Any], OrchestratorState]:
    """
    Handle messages during the execution phase.
    
    During this phase, we:
    1. Perform web search based on section requirements and bullets
    2. Collect search results
    3. Build prompt for Claude
    4. Generate draft content with citations
    5. Transition to reflection phase
    
    Args:
        db: Database session
        session: Session model instance
        state: Current orchestrator state
        message: User message
        
    Returns:
        Tuple of (response, updated state)
    """
    print(f"Handling message in EXECUTION phase: {message[:50]}...")
    
    # Initialize services
    llm_service = LLMService()
    
    # Initialize memory service if needed
    if not hasattr(state, 'memory_service'):
        state.memory_service = MemoryService()
    
    # Store user message in memory
    state.memory_service.add_message(
        session_id=state.session_id, 
        role="user", 
        content=message,
        categories=["execution", state.current_section_id]
    )
    
    # Get section details from guide
    section_info = extract_section_from_guide(session.guide_json, state.current_section_id)
    
    # Retrieve bullet points from memory
    bullets = get_bullet_points_from_memory(state)
    
    # Perform web search based on section requirements and bullet points
    search_results = await perform_search(state.current_section_id, section_info, bullets)
    
    # Generate draft content
    draft_response = await llm_service.generate_executor_response(
        session_id=state.session_id,
        section_info=section_info,
        bullets=bullets,
        search_results=search_results
    )
    
    # Get the draft content
    draft_content = draft_response.get("message", "")
    
    # Store draft in memory
    state.memory_service.add_message(
        session_id=state.session_id,
        role="assistant",
        content=draft_content,
        categories=["execution", state.current_section_id, "draft"]
    )
    
    # Store draft in database
    save_draft_to_database(db, state.session_id, state.current_section_id, draft_content)
    
    # Transition to reflection phase
    state.phase = Phase.REFLECTION
    
    # Format response
    response = {
        "message": draft_content,
        "metadata": {
            "phase": "reflection",
            "section_id": state.current_section_id,
            "generated_content": True
        }
    }
    
    return response, state


def get_bullet_points_from_memory(state: OrchestratorState) -> List[str]:
    """
    Retrieve bullet points for the current section from memory.
    
    Args:
        state: Current orchestrator state
        
    Returns:
        List of bullet points
    """
    # Default empty list
    bullet_points = []
    
    try:
        # Get messages with bullet_points category and current section ID
        results = state.memory_service.client.search(
            user_id=state.session_id,
            categories=["bullet_points", state.current_section_id],
            limit=1  # We only need the most recent set of bullet points
        )
        
        # Process results to extract bullet points
        if results and isinstance(results, list) and len(results) > 0:
            for result in results:
                if isinstance(result, dict) and "content" in result:
                    try:
                        # Parse the content as JSON
                        content = json.loads(result.get("content", "{}"))
                        if "bullet_points" in content:
                            bullet_points = content["bullet_points"]
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error retrieving bullet points: {e}")
    
    # If we still don't have bullet points, create some default ones
    if not bullet_points:
        print("No bullet points found, using defaults")
        bullet_points = ["Introduction to the topic", "Main arguments", "Supporting evidence", "Conclusion"]
    
    return bullet_points


async def perform_search(section_id: str, section_info: Dict[str, Any], bullets: List[str]) -> List[Dict[str, Any]]:
    """
    Perform web search based on section requirements and bullet points.
    
    This is a placeholder until we implement the actual search service.
    
    Args:
        section_id: ID of the section
        section_info: Section details
        bullets: List of bullet points
        
    Returns:
        List of search results
    """
    # Placeholder until we implement the search service
    print("Performing web search (placeholder)")
    
    # In a real implementation, we would call the search service:
    # from app.services.search_service import perform_web_search
    # return await perform_web_search(section_info, bullets)
    
    # For now, return empty results
    return []


def save_draft_to_database(db: Session, session_id: str, section_id: str, content: str) -> None:
    """
    Save generated draft content to the database.
    
    Args:
        db: Database session
        session_id: Session ID
        section_id: Section ID (format: "chapter.section")
        content: Generated content
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
            # Update content and status
            section.content = content
            section.status = "draft"
            db.commit()
            print(f"Draft saved for section {section_id}")
        else:
            print(f"Section {section_id} not found in database")
    except Exception as e:
        print(f"Error saving draft: {e}")
        db.rollback()
