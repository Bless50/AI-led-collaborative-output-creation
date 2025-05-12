"""
Intake phase handler for the LLM Service.

This module handles response generation for the intake phase,
where we gather basic requirements for the report before starting content creation.
"""
import json
from typing import Dict, Any

from app.services.llm.base import LLMService


async def generate_intake_response(
    llm_service: LLMService,
    session_id: str,
    guide_json: Dict[str, Any],
    intake_json: Dict[str, Any],
    message: str
) -> Dict[str, Any]:
    """
    Generate a response for the Intake phase.
    
    During this phase, Claude asks the user for necessary information
    to understand the report requirements before starting the content creation.
    
    This is the first phase of the workflow where we gather all initial requirements.
    
    Args:
        llm_service: Initialized LLM service
        session_id: The session identifier
        guide_json: The guide structure
        intake_json: Current intake responses
        message: User message
        
    Returns:
        Claude's response as a dictionary
    """
    # Get context from memory
    context = llm_service.memory_service.get_intake_context(session_id)
    
    # Format context as a string for Claude
    context_str = json.dumps(context, indent=2) if context else "No previous context available."
    
    # Format guide as a string
    guide_str = ""
    if guide_json:
        guide_str = f"""
        Report Guide:
        Title: {guide_json.get('title', 'Report Guide')}
        Description: {guide_json.get('description', 'No description available')}
        
        Structure:
        {json.dumps(guide_json.get('chapters', []), indent=2)}
        """
    
    # Format intake JSON as a string
    intake_str = ""
    if intake_json:
        intake_str = f"Current intake information:\n{json.dumps(intake_json, indent=2)}"
    
    # Check what information we still need
    missing_fields = get_missing_fields(intake_json)
    complete_intake = len(missing_fields) == 0
    
    # Create system prompt for the intake phase
    system_prompt = """
    You are a helpful academic writing assistant who is guiding the user through 
    creating a report. In this initial phase, you are collecting basic information
    about the report requirements.
    
    Ask for ONE piece of information at a time, using a conversational tone. 
    Tag each question with the field name in square brackets, e.g., "What's the title of your report? [TITLE]"
    
    Use these field tags:
    - [TITLE] - For the report title
    - [DEPARTMENT] - For academic department or subject
    - [ACADEMIC_LEVEL] - For the academic level (high school, undergraduate, graduate)
    - [TARGET_AUDIENCE] - For the intended audience
    - [TOPIC] - For the specific topic or focus
    - [LENGTH] - For report length requirements (pages or word count)
    - [DEADLINE] - For submission deadline
    - [FORMAT] - For formatting requirements
    - [CITATIONS] - For citation style (APA, MLA, Chicago, etc.)
    - [ADDITIONAL_REQUIREMENTS] - For any other specific requirements
    
    Once you have collected the TITLE and TOPIC, you can consider the intake complete
    and move on to planning the first section.
    """
    
    # Create user prompt
    user_prompt = f"""
    Previous conversation context:
    {context_str}
    
    Guide information:
    {guide_str}
    
    {intake_str}
    
    User message: {message}
    
    Please respond to the user and continue collecting the necessary information.
    If you have enough information, indicate that by adding "complete_intake": true in your response metadata.
    """
    
    # Create messages for Claude
    messages = [
        {
            "role": "user",
            "content": user_prompt
        }
    ]
    
    # Generate response from Claude
    response = await llm_service.generate_response(
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=1000,
        temperature=0.7
    )
    
    # Add metadata to indicate if intake is complete
    response["metadata"] = {
        "phase": "intake",
        "complete_intake": complete_intake or len(missing_fields) <= 1,
        "missing_fields": missing_fields
    }
    
    return response


def get_missing_fields(intake_json: Dict[str, Any]) -> list:
    """
    Determine what required fields are still missing from the intake.
    
    Args:
        intake_json: Current intake responses
        
    Returns:
        List of missing field names
    """
    required_fields = ["title", "topic"]  # Minimum required fields
    optional_fields = [
        "department", "academic_level", "target_audience", 
        "length", "deadline", "format", "citations", 
        "additional_requirements"
    ]
    
    # Check required fields
    missing = []
    for field in required_fields:
        if field not in intake_json or not intake_json[field]:
            missing.append(field)
    
    # Only add optional fields if they're missing AND we have all required fields
    if not missing:
        for field in optional_fields:
            if field not in intake_json or not intake_json[field]:
                missing.append(field)
    
    return missing
