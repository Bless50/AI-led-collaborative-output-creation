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
    
    # Get the current intake data to pass to Claude
    current_intake_data = get_current_intake_data(intake_json)
    # We're no longer using the concept of "missing fields"
    
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
    - [LENGTH] - For report length requirements (pages or word count)
    - [DEADLINE] - For submission deadline
    - [FORMAT] - For formatting requirements
    - [CITATIONS] - For citation style (APA, MLA, Chicago, etc.)
    - [ADDITIONAL_REQUIREMENTS] - For any other specific requirements
    
    As you collect information, maintain a JSON object of all requirements gathered so far.
    Every time you respond, include a MACHINE-READABLE JSON object at the end of your message
    between <REQUIREMENTS_JSON> and </REQUIREMENTS_JSON> tags, containing all fields you've
    gathered. For example:
    
    <REQUIREMENTS_JSON>
    {
      "title": "Climate Change Effects on Coral Reefs",
      "department": "Marine Biology",
      "academic_level": "Undergraduate",
      ...
    }
    </REQUIREMENTS_JSON>
    
    When you believe you have collected all necessary information, include "complete_intake": true
    in this JSON object AND in your response metadata. The system will extract this JSON data automatically,
    so the user will not see it in the frontend.
    
    Once you have collected all this information you can consider the intake complete
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
    
    # Extract structured JSON from Claude's response
    import re
    message_content = response.get("message", "")
    
    # Function to extract requirements JSON from Claude's response
    def extract_requirements_json(message_text):
        """Extract the requirements JSON from Claude's message between tags"""
        json_match = re.search(r'<REQUIREMENTS_JSON>\s*(.+?)\s*</REQUIREMENTS_JSON>', 
                              message_text, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                requirements_data = json.loads(json_str)
                print(f"DEBUG LLM: Successfully extracted requirements JSON: {json.dumps(requirements_data, indent=2)}")
                return requirements_data
            except json.JSONDecodeError as e:
                print(f"ERROR: Could not parse requirements JSON: {e}")
                print(f"JSON string was: {json_match.group(1)}")
                return {}
        else:
            print("DEBUG LLM: No requirements JSON found in Claude's response")
            return {}
    
    # Extract the requirements JSON
    requirements_json = extract_requirements_json(message_content)
    
    # Check for completion signal in the extracted JSON or message patterns
    json_indicates_completion = bool(requirements_json and requirements_json.get("complete_intake") is True)
    
    # Look for explicit completion signals in Claude's response text
    completion_indicators = [
        r'"complete_intake"\s*:\s*true',  # JSON format
        r"'complete_intake'\s*:\s*true",  # Single-quote JSON
        r"ready to\s+proceed",            # Natural language
        r"we have\s+all\s+information",
        r"intake\s+complete",
        r"have\s+enough\s+information",
        r"move\s+to\s+planning",
        r"start\s+planning"
    ]
    
    # Check if Claude indicates we should transition in the message text
    text_indicates_completion = any(bool(re.search(pattern, message_content, re.IGNORECASE)) 
                                   for pattern in completion_indicators)
    
    # Combined signal (either JSON or text indication)
    claude_indicates_completion = json_indicates_completion or text_indicates_completion
    
    print(f"DEBUG LLM: JSON indicates completion: {json_indicates_completion}")
    print(f"DEBUG LLM: Text indicates completion: {text_indicates_completion}")
    print(f"DEBUG LLM: Overall completion indication: {claude_indicates_completion}")
    
    # Merge any extracted requirements with existing intake data
    # Note: This will update the intake_json with any new fields Claude has identified
    if requirements_json:
        # Remove the machine tags from the displayed message
        # This ensures the user doesn't see the raw JSON
        clean_message = re.sub(r'<REQUIREMENTS_JSON>.*?</REQUIREMENTS_JSON>', '', 
                              message_content, flags=re.DOTALL).strip()
        response["message"] = clean_message
        
        # If we extracted valid requirements JSON, include it in the metadata
        # for the orchestrator to store in the database
        response["metadata"] = {
            "phase": "intake",
            "complete_intake": claude_indicates_completion,
            "requirements_json": requirements_json  # Include the structured data Claude provided
        }
        print(f"DEBUG LLM: Including requirements JSON in metadata: {json.dumps(requirements_json, indent=2)}")
    else:
        # Fall back to our existing approach if no structured JSON was found
        response["metadata"] = {
            "phase": "intake",
            "complete_intake": claude_indicates_completion,
            "current_intake": current_intake_data
        }
    
    print(f"DEBUG LLM: Completion indicated: {claude_indicates_completion}")
    
    
    return response


def get_current_intake_data(intake_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simply return the current intake data with no field validation.
    Each response from Claude is stored in intake_json with the corresponding question/field.
    
    Args:
        intake_json: Current stored intake responses
        
    Returns:
        The current intake_json exactly as stored
    """
    # No validation, just return what we have
    return intake_json
