"""
Execution phase handler for the LLM Service.

This module handles response generation for the execution phase,
where Claude generates draft content based on bullet points and search results.
"""
import json
from typing import Dict, Any, List

from app.services.llm.base import LLMService


async def generate_executor_response(
    llm_service: LLMService,
    session_id: str,
    section_info: Dict[str, Any],
    bullets: List[str],
    search_results: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate content for a section based on bullets and search results.
    
    During this phase, Claude generates draft content with proper citations
    based on the user's bullet points and web search results.
    
    Args:
        llm_service: Initialized LLM service
        session_id: The session identifier
        section_info: Information about the current section
        bullets: List of bullet points provided by the user
        search_results: Optional list of search results to incorporate
        
    Returns:
        Claude's response as a dictionary
    """
    # Get relevant context from memory
    context = llm_service.memory_service.get_execution_context(session_id, section_info.get("section_id", ""))
    
    # Format context as a string
    context_str = json.dumps(context, indent=2) if context else "No previous context available."
    
    # Format search results if provided
    search_results_str = ""
    if search_results:
        search_results_str = f"""
        Use the following search results as references:
        {json.dumps(search_results, indent=2)}
        
        When using information from these sources, provide proper citations.
        """
    
    # Create system prompt for the Executor role
    system_prompt = """
    You are an expert content creator who specializes in writing high-quality report sections.
    Your job is to generate well-structured, informative content based on the user's requirements.
    
    When search results are provided:
    1. Incorporate relevant information from the search results
    2. Provide proper citations using [Source X] format
    3. Ensure factual accuracy and avoid hallucinations
    
    Write in a clear, professional tone and organize the content logically.
    Include a brief introduction, well-developed body paragraphs, and a conclusion.
    Make sure to cover ALL the bullet points provided by the user.
    """
    
    # Create messages for the conversation
    messages = [
        {
            "role": "user",
            "content": f"""
            I need you to write content for the following section:
            {json.dumps(section_info, indent=2)}
            
            Here are my key points for this section:
            {json.dumps(bullets, indent=2)}
            
            {search_results_str}
            
            Previous conversation context:
            {context_str}
            
            Please generate well-structured content for this section. 
            The content should follow an academic style appropriate for a formal report, 
            covering all the bullet points I've provided. 
            Include proper citations if using information from the search results.
            """
        }
    ]
    
    # Generate response
    response = await llm_service.generate_response(
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=2000,
        temperature=0.7
    )
    
    # Add metadata to response
    response["metadata"] = {
        "phase": "execution",
        "section_id": section_info.get("section_id", ""),
        "section_title": section_info.get("section_title", ""),
        "content_generated": True
    }
    
    return response
