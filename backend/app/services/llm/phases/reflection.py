"""
Reflection phase handler for the LLM Service.

This module handles response generation for the reflection phase,
where Claude asks Socratic questions to help the user deepen their understanding.
"""
import json
from typing import Dict, Any

from app.services.llm.base import LLMService


async def generate_reflector_response(
    llm_service: LLMService,
    session_id: str,
    draft_content: str
) -> Dict[str, Any]:
    """
    Generate Socratic questions to help the user reflect on the draft content.
    
    During this phase, Claude asks thought-provoking questions to help the user
    deepen their understanding and improve the content.
    
    Args:
        llm_service: Initialized LLM service
        session_id: The session identifier
        draft_content: The generated draft content
        
    Returns:
        Claude's response as a dictionary
    """
    # Get relevant context from memory
    context = llm_service.memory_service.get_reflector_context(session_id, draft_content)
    
    # Format context as a string
    context_str = json.dumps(context, indent=2) if context else "No previous context available."
    
    # Create system prompt for the Reflector role
    system_prompt = """
    You are a Socratic educator who helps users deepen their understanding through reflection.
    Your job is to ask thought-provoking questions about the content to help the user:
    1. Identify gaps or inconsistencies in the content
    2. Consider alternative perspectives or approaches
    3. Deepen their understanding of the subject matter
    
    Ask 3-5 open-ended questions that encourage critical thinking and reflection.
    Be supportive and constructive in your approach.
    
    Examples of good Socratic questions:
    - "How might someone with a different perspective view this issue?"
    - "What evidence would strengthen your argument in section X?"
    - "How does this connect to concepts we covered in earlier sections?"
    - "What implications might follow from your conclusion?"
    """
    
    # Create messages for the conversation
    messages = [
        {
            "role": "user",
            "content": f"""
            I've created the following draft content:
            
            {draft_content}
            
            Previous conversation context:
            {context_str}
            
            Please ask me Socratic questions to help me reflect on and improve this content.
            Focus on questions that will deepen my understanding, identify areas for improvement,
            and encourage critical thinking about the material.
            """
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
        "phase": "reflection",
        "reflection_questions": True
    }
    
    return response
