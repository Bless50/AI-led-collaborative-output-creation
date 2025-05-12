"""
Planning phase handler for the LLM Service.

This module handles response generation for the planning phase,
where we help the user plan specific sections of the report by asking for bullet points.
"""
import json
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.services.llm.base import LLMService
from app.services.llm.utils import extract_section_details, get_completed_sections


async def generate_planner_response(
    llm_service: LLMService,
    session_id: str,
    guide_json: Dict[str, Any],
    intake_json: Dict[str, Any],
    current_section_id: str,
    db: Optional[Session] = None,
    message: str = ""
) -> Dict[str, Any]:
    """
    Generate a response for the Planner phase focused on the current section.
    
    During this phase, Claude helps plan specific sections of the report
    by asking for bullet points for the current section. The AI leads this
    conversation by prompting the user for their key points.
    
    Args:
        llm_service: Initialized LLM service
        session_id: The session identifier
        guide_json: The guide structure
        intake_json: Intake responses
        current_section_id: ID of the current section (format: "chapter.section")
        db: Optional database session for retrieving completed sections
        message: User message
        
    Returns:
        Claude's response as a dictionary
    """
    # Get context from memory
    context = llm_service.memory_service.get_planning_context(session_id, current_section_id)
    
    # Extract section details from guide
    section_info = extract_section_details(guide_json, current_section_id)
    
    # Format context as a string
    context_str = json.dumps(context, indent=2) if context else "No previous context available."
    
    # Get completed sections if db is provided
    completed_sections = ""
    if db:
        completed_sections = get_completed_sections(db, session_id)
    
    # Format intake information
    report_title = intake_json.get("title", "")
    report_topic = intake_json.get("topic", "")
    
    # Check if we've already asked for bullet points
    bullet_points_requested = False
    if context:
        for entry in context:
            if "bullet_points" in entry.get("categories", []):
                bullet_points_requested = True
                break
    
    # Create system prompt for the Planner role
    system_prompt = """
    You are an expert academic report planner who helps students organize their thoughts.
    Your job is to guide the user in planning the current section by asking for bullet points.
    
    In this planning phase:
    1. Explain what this section should cover based on the guide requirements
    2. Ask the user for bullet points they want to include in this section
    3. Be specific to the current section's requirements
    
    Focus on helping the user organize their thoughts in bullet point format.
    Make it clear you're asking for bullet points SPECIFICALLY for the current section.
    """
    
    # Create messages for the conversation
    content = f"""
    I'm helping you plan the section: "{section_info.get('section_title')}" in chapter "{section_info.get('chapter_title')}"
    
    Report title: {report_title}
    Report topic: {report_topic}
    
    Section requirements:
    {json.dumps(section_info.get('requirements', []), indent=2)}
    Section description: {section_info.get('description', 'No description provided')}
    
    Previous sections:
    {completed_sections}
    
    Previous conversation context:
    {context_str}
    
    User message: {message}
    """
    
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    
    # Generate response
    response = await llm_service.generate_response(
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=1000,
        temperature=0.7
    )
    
    # Add metadata to response
    response["metadata"] = {
        "phase": "planning",
        "section_id": current_section_id,
        "bullet_points_requested": True,  # Mark that we've asked for bullet points
        "section_info": section_info
    }
    
    return response
