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
        You are a specialized extraction system that converts thesis/report guide text into structured JSON.
        Follow these rules exactly:
        1. Output ONLY valid JSON - no other text before or after
        2. Follow the exact schema provided
        3. Include EVERY SINGLE section and subsection from the text - do NOT skip any
        4. Include COMPLETE and DETAILED requirements for each section
        5. Do not add any additional fields not in the schema
        6. Escape any special characters in text fields
        
        Your TWO primary objectives with EQUAL importance:
        - COMPLETENESS: Include ALL chapters and sections from the guide
        - DETAIL: Capture the FULL requirements for each section
        
        Convert this thesis/report guide into structured JSON following this schema:
        
        {{
          "title": "GUIDE_TITLE",
          "chapters": [
            {{
              "title": "CHAPTER_TITLE",
              "sections": [
                {{
                  "title": "SECTION_TITLE",
                  "requirements": "FULL_SECTION_REQUIREMENTS",
                  "id": "CHAPTER_NUMBER.SECTION_NUMBER"
                }}
              ]
            }}
          ]
        }}
        
        Follow the schema exactly and make sure all information is properly nested.
        Guidelines:
        1. DO NOT SKIP ANY CONTENT - include ALL sections and their COMPLETE requirements
        2. Keep section numbers (like "1.1", "3.3.2") in the titles
        3. If the document uses different terminology (like "Parts" or "Units"), map them to "chapters" and "sections" in the output
        4. Preserve ALL requirement details including bullet points, numbered lists, and specific instructions
        5. If there are multiple sections with the same title but different chapter contexts, include them all
        
        """
    
  
    # Create user prompt with the guide text to satisfy Anthropic API requirements
    user_prompt = f"""Extract ALL chapters and sections from this thesis/report guide using the specified schema. Process the ENTIRE document:

{guide_text}

Ensure you extract EVERY chapter and section, not just the first few. Double-check that nothing is missing."""
    
    # Call the LLM API with increased token limit to ensure completeness
    response = await llm_service._call_anthropic_api(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=8000,  # Significantly increased to ensure complete extraction of large documents
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
