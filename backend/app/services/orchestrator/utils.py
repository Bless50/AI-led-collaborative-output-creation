"""
Utility functions for the Orchestrator service.

This module contains helper functions used across different parts of the
orchestrator service that don't belong to any specific phase.
"""
from typing import Dict, Any


def extract_section_from_guide(guide_json: Dict[str, Any], section_id: str) -> Dict[str, Any]:
    """
    Extract details for a specific section from the guide JSON.
    
    Args:
        guide_json: The complete guide structure
        section_id: ID of the section to extract (format: "chapter.section")
        
    Returns:
        Dictionary with section details or default if not found
    """
    try:
        # Parse section ID in format "chapter.section"
        chapter_idx, section_idx = map(int, section_id.split('.'))
        
        # Get chapter
        chapter = guide_json.get("chapters", [])[chapter_idx]
        
        # Get section
        section = chapter.get("sections", [])[section_idx]
        
        # Get chapter title
        chapter_title = chapter.get("title", f"Chapter {chapter_idx + 1}")
        
        # Get section title
        section_title = section.get("title", f"Section {section_idx + 1}")
        
        # Build section info
        section_info = {
            "section_id": section_id,
            "chapter_title": chapter_title,
            "chapter_idx": chapter_idx,
            "section_title": section_title,
            "section_idx": section_idx,
            "requirements": section.get("requirements", []),
            "description": section.get("description", "")
        }
        
        return section_info
    except (IndexError, ValueError, KeyError, TypeError) as e:
        # Return default section info
        print(f"Error extracting section {section_id}: {str(e)}")
        return {
            "section_id": section_id,
            "chapter_title": "Unknown Chapter",
            "chapter_idx": -1,
            "section_title": "Unknown Section",
            "section_idx": -1,
            "requirements": [],
            "description": "No description available."
        }


def determine_intake_field(previous_question: str) -> str:
    """
    Determine which intake field to populate based on the previous question.
    
    Primarily looks for tagged fields like [TITLE], then falls back to keyword matching.
    
    Args:
        previous_question: The previous question asked by the AI
        
    Returns:
        Field name to use in intake_json
    """
    import re
    
    # Default field if we can't determine
    default_field = "notes"
    
    # Check if there are no previous questions
    if not previous_question:
        return default_field
        
    # First, look for explicit tags in square brackets like [TITLE]
    tag_match = re.search(r'\[([A-Z_]+)\]', previous_question)
    if tag_match:
        tag = tag_match.group(1).lower()
        # Map the tag to intake_json field
        tag_mapping = {
            "title": "title",
            "report_title": "title",
            "department": "department",
            "academic_level": "academic_level", 
            "target_audience": "target_audience",
            "topic": "topic",
            "length": "length",
            "deadline": "deadline",
            "additional_requirements": "additional_requirements",
            "format": "format",
            "citations": "citations",
            "notes": "notes"
        }
        return tag_mapping.get(tag, default_field)
    
    # If no explicit tag, use keyword matching
    keywords = {
        "title": ["title", "name", "heading"],
        "department": ["department", "faculty", "school", "discipline"],
        "academic_level": ["academic level", "level", "grade", "year"],
        "target_audience": ["audience", "readers", "who will read", "intended for"],
        "topic": ["topic", "subject", "about", "focus"],
        "length": ["length", "pages", "words", "how long"],
        "deadline": ["deadline", "due date", "when is", "submit"],
        "format": ["format", "style", "structure", "organized"],
        "citations": ["citation", "reference", "sources", "bibliography"],
        "additional_requirements": ["requirements", "additional", "special", "specific"],
        "notes": ["notes", "anything else", "other", "additional information"]
    }
    
    # Convert to lowercase for case-insensitive matching
    question_lower = previous_question.lower()
    
    # Check each field's keywords
    for field, field_keywords in keywords.items():
        for keyword in field_keywords:
            if keyword in question_lower:
                return field
                
    # Default to notes if no match found
    return default_field
