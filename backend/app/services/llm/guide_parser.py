"""
Guide Parser Module for the LLM Service.

This module contains functions for parsing guide text into structured JSON format.
It implements robust parsing with improved error handling and recovery mechanisms.

Recent enhancements:
1. Updated model from claude-3-haiku-20240307 to claude-3-5-haiku-20241022
2. Improved prompts for both completeness and detailed requirements
3. Robust JSON sanitization and fallback mechanisms
4. Better error handling and recovery
"""
import json
import re
from typing import Dict, Any

from app.services.llm.base import LLMService


async def parse_guide_to_json(llm_service: LLMService, guide_text: str) -> Dict[str, Any]:
    """
    Convert report guide text to structured JSON using the LLM.
    
    This function sends the guide text to Claude and asks it to extract
    the structure into a JSON format. It includes fallback mechanisms if
    the initial attempt fails.
    
    Args:
        llm_service: Initialized LLM service instance
        guide_text: The raw text of the report guide
        
    Returns:
        A dictionary containing the structured guide information
    """
    print(f"Parsing guide text ({len(guide_text)} characters)...")
    
    try:
        # First attempt: Try to extract the entire guide in one call
        guide_json = await _extract_full_guide(llm_service, guide_text)
        
        if guide_json:
            print("✅ Successfully parsed guide to JSON")
            return guide_json
        else:
            print("⚠️ Failed to extract guide JSON, using fallback")
            # Return a basic structure to prevent crashes
            return {
                "title": "Report Guide",
                "description": "Guide could not be fully parsed",
                "chapters": [
                    {
                        "title": "Chapter 1",
                        "description": "First chapter",
                        "sections": [
                            {
                                "title": "Section 1.1",
                                "description": "First section",
                                "requirements": ["Requirement 1"]
                            }
                        ]
                    }
                ]
            }
    except Exception as e:
        print(f"❌ Error parsing guide: {str(e)}")
        # Return minimal valid JSON structure in case of error
        return {
            "title": "Report Guide (Error)",
            "description": f"Error parsing guide: {str(e)}",
            "chapters": [
                {
                    "title": "Chapter 1",
                    "description": "Please check the guide format",
                    "sections": [
                        {
                            "title": "Section 1.1",
                            "description": "Error in guide parsing",
                            "requirements": ["Contact support"]
                        }
                    ]
                }
            ]
        }


async def _extract_full_guide(llm_service: LLMService, guide_text: str) -> Dict[str, Any]:
    """
    Attempt to extract the entire guide in one call.
    
    This function uses a carefully crafted prompt to extract the guide
    structure while preserving ALL content from the original guide text.
    
    Args:
        llm_service: Initialized LLM service
        guide_text: The raw guide text
        
    Returns:
        Parsed guide as dictionary or None if parsing failed
    """
    # Create a system prompt that emphasizes completeness and detailed extraction
    system_prompt = """
    You are an expert at extracting structured information from academic report guides.
    Your task is to convert the provided text into a consistent JSON format that captures
    ALL content from the original guide, including ALL requirements and instructions.
    
    You MUST maintain the original structure with chapters and sections.
    Ensure you capture ALL requirements for each section - completeness is critical.
    Preserve original numbering, but convert to a nested structure.
    """
    
    # Create the user prompt with expected output format
    user_prompt = f"""
    Please extract the structure of this report guide and convert it to JSON:
    
    {guide_text}
    
    The output should be valid JSON with this structure:
    {{
        "title": "The guide title",
        "description": "Overall guide description",
        "chapters": [
            {{
                "title": "Chapter 1 title",
                "description": "Chapter description",
                "sections": [
                    {{
                        "title": "Section 1.1 title",
                        "description": "Section description",
                        "requirements": [
                            "Requirement 1",
                            "Requirement 2"
                        ]
                    }}
                ]
            }}
        ]
    }}
    
    IMPORTANT:
    1. Include ALL content from the original guide
    2. Preserve ALL requirements and guidance for each section
    3. Ensure the JSON is valid and properly formatted
    4. Maintain the original structure (chapters, sections, etc.)
    5. Start your response with the JSON object directly
    """
    
    # Call the LLM API with increased token limit to ensure completeness
    response = await llm_service._call_anthropic_api(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=8000,  # Increased from 6000 to ensure we get complete extraction
        temperature=0.2   # Low temperature for more deterministic output
    )
    
    # Debug
    print(f"LLM response length: {len(response)}")
    print(f"Response preview: {response[:200]}...")
    
    try:
        # Try to parse the response as JSON
        # First, try to extract JSON if it's wrapped in other text
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
            print("Found JSON in code block")
        else:
            # If not in code block, use the whole response
            json_text = response
            
        # Clean and parse the JSON
        return _sanitize_json(json_text)
    except Exception as e:
        print(f"Error extracting guide JSON: {str(e)}")
        # Try fallback to partial extraction
        return _extract_partial_json(response)


def _sanitize_json(text: str) -> Dict[str, Any]:
    """
    Attempt to fix common JSON errors in LLM outputs.
    
    This function handles various issues like trailing commas, unquoted keys,
    and other common formatting problems in JSON generated by language models.
    
    Args:
        text: The potentially malformed JSON text
        
    Returns:
        Cleaned and parsed JSON as dictionary
    """
    # Initial clean-up
    text = text.strip()
    
    # Remove any leading/trailing markdown or text before/after JSON
    # First, try to find the first { and last }
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx >= 0 and end_idx >= 0:
        text = text[start_idx:end_idx+1]
    
    # Common JSON errors and fixes
    try:
        # First attempt: Try parsing as-is
        return json.loads(text)
    except json.JSONDecodeError:
        # Fix common issues
        
        # 1. Remove trailing commas before closing brackets
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # 2. Add quotes around unquoted keys
        text = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', text)
        
        # 3. Replace single quotes with double quotes
        text = re.sub(r"'(.*?)'", r'"\1"', text)
        
        # Try again with cleaned text
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON after cleaning: {str(e)}")
            # If we still can't parse, try partial extraction
            raise


def _extract_partial_json(text: str) -> Dict[str, Any]:
    """
    Attempt to extract partial JSON structure from malformed LLM output.
    Uses regex to extract key elements even when JSON parsing fails.
    
    Args:
        text: The malformed JSON text to extract from
        
    Returns:
        A basic JSON structure with whatever could be extracted
    """
    # Initialize basic structure
    guide = {
        "title": "Extracted Guide",
        "description": "Partially extracted from guide text",
        "chapters": []
    }
    
    # Try to extract title
    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
    if title_match:
        guide["title"] = title_match.group(1)
    
    # Try to extract description
    desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', text)
    if desc_match:
        guide["description"] = desc_match.group(1)
    
    # Try to extract chapters
    chapter_matches = re.finditer(r'"title"\s*:\s*"(Chapter [^"]+)"', text)
    for i, match in enumerate(chapter_matches):
        chapter_title = match.group(1)
        guide["chapters"].append({
            "title": chapter_title,
            "description": f"Chapter {i+1}",
            "sections": [{
                "title": f"Section {i+1}.1",
                "description": "Automatically generated section",
                "requirements": ["Requirement extracted from guide"]
            }]
        })
    
    # If no chapters found, add a placeholder
    if not guide["chapters"]:
        guide["chapters"] = [{
            "title": "Chapter 1",
            "description": "Automatically generated chapter",
            "sections": [{
                "title": "Section 1.1",
                "description": "Automatically generated section",
                "requirements": ["Requirement should be added manually"]
            }]
        }]
    
    return guide
