"""
Utility functions for the LLM Service.

This module contains helper functions that are used across different parts of the
LLM service, such as:
1. Extracting section details from guide JSON
2. Retrieving completed sections from the database
3. Other common operations
"""
import json
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session


def extract_section_details(guide_json: Dict[str, Any], section_id: str) -> Dict[str, Any]:
    """
    Extract details for a specific section from the guide JSON.
    
    Args:
        guide_json: The complete guide structure
        section_id: ID of the section to extract (format: "chapter.section")
        
    Returns:
        Dictionary with section details or empty dict if not found
    """
    try:
        # Parse section ID in format "chapter.section"
        chapter_idx, section_idx = map(int, section_id.split('.'))
        
        # Get chapter
        chapter = guide_json.get("chapters", [])[chapter_idx]
        
        # Get section
        section = chapter.get("sections", [])[section_idx]
        
        # Extract details
        return {
            "section_id": section_id,
            "chapter_title": chapter.get("title", f"Chapter {chapter_idx + 1}"),
            "section_title": section.get("title", f"Section {section_idx + 1}"),
            "chapter_idx": chapter_idx,
            "section_idx": section_idx,
            "requirements": section.get("requirements", []),
            "description": section.get("description", "")
        }
    except (IndexError, ValueError, KeyError, TypeError):
        # Return empty dict if section not found
        return {}


def get_completed_sections(db: Session, session_id: str) -> str:
    """
    Retrieve HTML content of previously completed sections from the database.
    
    Args:
        db: Database session
        session_id: The session identifier
        
    Returns:
        String with HTML content of completed sections or message if none found
    """
    try:
        # Import here to avoid circular imports
        from app.db.models.section import Section as SectionModel
        
        # Query completed sections
        completed_sections = db.query(SectionModel).filter(
            SectionModel.session_id == session_id,
            SectionModel.status == "complete"
        ).order_by(
            SectionModel.chapter_idx, 
            SectionModel.section_idx
        ).all()
        
        if not completed_sections:
            return "No completed sections yet."
        
        # Build HTML content
        html_content = ""
        
        for section in completed_sections:
            html_content += f"<h2>Section {section.chapter_idx + 1}.{section.section_idx + 1}</h2>\n"
            html_content += f"{section.content}\n\n"
        
        return html_content
    except Exception as e:
        print(f"Error retrieving completed sections: {str(e)}")
        return "Error retrieving completed sections."


def extract_bullet_points(text: str) -> List[str]:
    """
    Extract bullet points from text input.
    
    This function recognizes various bullet point formats:
    - Dashes: "- Point 1"
    - Bullets: "• Point 1"
    - Asterisks: "* Point 1"
    - Numbers: "1. Point 1" or "1) Point 1"
    
    Args:
        text: Text containing bullet points
        
    Returns:
        List of extracted bullet points
    """
    if not text:
        return []
        
    # Split text into lines
    lines = text.strip().split('\n')
    bullets = []
    
    # Regular expressions for different bullet formats
    bullet_patterns = [
        r'^\s*[-•*]\s+(.+)$',  # Matches: - bullet, • bullet, * bullet
        r'^\s*(\d+[.)])\s+(.+)$',  # Matches: 1. bullet, 1) bullet
    ]
    
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
                
        # If not a bullet but contains substantive text, add it anyway
        if not is_bullet and len(line) > 10:
            bullets.append(line)
    
    return bullets
