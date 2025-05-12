import json
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.session import SessionCreate, SessionState, IntakeResponse
from app.services.llm_service import LLMService
from app.services.session_service import (
    create_session,
    get_session_by_id,
    get_session_state,
    update_intake_response,
)

router = APIRouter()


@router.post("", response_model=Dict[str, str])
async def create_new_session(
    guide_file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Create a new session by uploading a guide file.
    
    This endpoint parses the guide file into JSON and creates a new session.
    
    Args:
        guide_file: The guide file to parse
        db: Database session
        
    Returns:
        Dictionary with session_id
        
    Raises:
        HTTPException: If the guide file is invalid or cannot be parsed
    """
    try:
        # Get file info for debugging
        file_name = guide_file.filename
        content_type = guide_file.content_type
        
        # Read the file content
        guide_content = await guide_file.read()
        
        # Log file information for debugging
        print(f"File: {file_name} | Type: {content_type} | Size: {len(guide_content)} bytes")
        
        # Parse the guide file
        llm_parsing_successful = False
        
        try:
            # First, extract text from the file
            guide_text = extract_text_from_file(guide_content).decode('utf-8') \
                if isinstance(guide_content, bytes) else guide_content
            
            # Check if we have the API key set
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print("⚠️ WARNING: No Anthropic API key found in environment. Using fallback parser.")
                raise ValueError("Missing API key")
                
            # Initialize LLM service for guide parsing - only do this once
            print("🔄 Initializing LLM service for guide parsing...")
            try:
                llm_service = LLMService()  # Already imported at the top
                
                # Use LLM to convert guide text to structured JSON
                print("🔄 Sending guide to Claude API for parsing...")
                guide_json = llm_service.parse_guide_to_json(guide_text)
                
                # Only set success flag and log success if we get here
                llm_parsing_successful = True
                print("✅ Successfully parsed guide file using LLM")
            except Exception as llm_error:
                # If LLM fails, log it and immediately try fallback
                print(f"❌ LLM parsing failed: {str(llm_error)}")
                raise ValueError("LLM parsing failed")
        except ValueError as parse_error:
            if "LLM parsing failed" in str(parse_error):
                print("Falling back to rule-based parser...")
                try:
                    guide_json = parse_guide_file(guide_content)
                    print("✅ Successfully parsed guide file with fallback method")
                except Exception as fallback_error:
                    print(f"❌ Fallback parsing also failed: {str(fallback_error)}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to parse guide file: {str(fallback_error)}"
                    )
        
        # Log parsing status with clear indication which method succeeded
        if not llm_parsing_successful:
            print("⚠️ Used fallback parser instead of LLM - check ANTHROPIC_API_KEY environment variable")
        
        # Create session with parsed guide
        session_data = SessionCreate(guide_json=guide_json)
        session = create_session(db=db, session_data=session_data)
        
        return {"session_id": session.session_id}
    except Exception as e:
        error_msg = f"Error creating session: {str(e)} | File: {file_name} | Type: {content_type}"
        print(error_msg)
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )


@router.get("/{session_id}/state", response_model=SessionState)
def get_session_current_state(
    session_id: str,
    db: Session = Depends(get_db)
) -> SessionState:
    """
    Get the current state of a session.
    
    This endpoint returns the session's guide JSON, intake JSON, intake status,
    and the status of all sections.
    
    Args:
        session_id: The session ID
        db: Database session
        
    Returns:
        SessionState object with session data
        
    Raises:
        HTTPException: If the session is not found
    """
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    return get_session_state(db=db, session=session)


@router.post("/{session_id}/intake-response", response_model=Dict[str, bool])
def update_session_intake(
    session_id: str,
    intake_data: IntakeResponse,
    db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """
    Update intake response for a session.
    
    This endpoint updates a field in the session's intake_json and
    checks if all required intake fields are now complete.
    
    Args:
        session_id: The session ID
        intake_data: The intake field and value to update
        db: Database session
        
    Returns:
        Dictionary with intake_done status
        
    Raises:
        HTTPException: If the session is not found
    """
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    intake_done = update_intake_response(
        db=db,
        session=session,
        field=intake_data.field,
        value=intake_data.value
    )
    
    return {"intake_done": intake_done}


def extract_text_from_file(content: bytes) -> str:
    """Extract text from various file formats (DOCX, PDF, plain text)."""
    # Check if it's a DOCX file (starts with PK - zip archive signature)
    if content.startswith(b'PK'):
        try:
            print("Detected DOCX file, extracting text...")
            import io
            from docx import Document
            
            doc = Document(io.BytesIO(content))
            # Extract text with style information if available
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            text = "\n".join(paragraphs)
            print(f"Extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            print(f"Error extracting text from DOCX: {str(e)}")
            raise ValueError(f"Failed to extract text from DOCX file: {str(e)}")
    
    # Check if it's a PDF file
    elif content.startswith(b'%PDF'):
        try:
            print("Detected PDF file, extracting text...")
            import io
            from PyPDF2 import PdfReader
            
            pdf = PdfReader(io.BytesIO(content))
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            print(f"Extracted {len(text)} characters from PDF")
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF file: {str(e)}")
    
    # If not recognized, try as plain text
    else:
        try:
            print("Attempting to decode as plain text...")
            text = content.decode('utf-8')
            print(f"Decoded {len(text)} characters as UTF-8 text")
            return text
        except UnicodeDecodeError:
            try:
                # Try with a more lenient encoding
                print("UTF-8 failed, trying with latin-1 encoding...")
                text = content.decode('latin-1')
                print(f"Decoded {len(text)} characters as latin-1 text")
                return text
            except Exception as e:
                print(f"Error decoding as text: {str(e)}")
                raise ValueError(f"Could not decode file content: {str(e)}")


def parse_text_to_guide_structure(text: str) -> Dict[str, Any]:
    """Parse extracted text into a structured guide JSON with proper subsection handling."""
    import re
    
    # Split text into lines and clean up
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Set a default guide title
    guide_title = "Report Guide"
    if lines:
        guide_title = lines[0]
    
    # Initialize guide structure
    guide_json = {
        "title": guide_title,
        "chapters": []
    }
    
    # Patterns for different heading types
    chapter_patterns = [
        r'^chapter\s+\d+',      # Chapter followed by number
        r'^\d+\.\s+[A-Z]',     # Number followed by dot and capital letter (e.g., "1. Introduction")
        r'^[IVX]+\.\s+',       # Roman numeral followed by dot
        r'^[A-Z\s]{5,}$'       # All uppercase text (minimum 5 chars)
    ]
    
    section_patterns = [
        r'^\d+\.\d+\.?\s+',    # Section numbering like 1.1, 2.3
        r'^section\s+\d+',     # Section followed by number
        r'^[A-Z][a-z]+\s+\d+',  # Word followed by number (e.g., "Part 1")
        r'^\([a-z]\)'          # Lettered list like (a), (b)
    ]
    
    subsection_patterns = [
        r'^\d+\.\d+\.\d+\.?\s+',  # Subsection like 1.1.1, 3.3.2
        r'^[a-z]\)\s+',           # Lettered list like a), b)
        r'^\d+\)\s+',             # Numbered list like 1), 2)
        r'^•\s+'                  # Bullet points
    ]
    
    current_chapter = None
    current_section = None
    current_subsection = None
    content_buffer = []
    
    def save_current_content():
        """Save accumulated content to the appropriate level"""
        nonlocal content_buffer
        if content_buffer:
            content_text = "\n".join(content_buffer)
            content_buffer = []
            
            if current_subsection:
                current_subsection["requirements"] = content_text
            elif current_section:
                current_section["requirements"] = content_text
    
    # Process text line by line
    for i, line in enumerate(lines):
        # Determine line type
        is_chapter = any(re.match(pattern, line) for pattern in chapter_patterns) or (
            i < 5 and len(line) < 60 and not current_chapter)
        
        is_section = not is_chapter and any(re.match(pattern, line) for pattern in section_patterns) or (
            re.match(r'^\d+\.\d+\s+', line))  # Match patterns like "3.1 Research Design"
        
        is_subsection = not is_chapter and not is_section and any(
            re.match(pattern, line) for pattern in subsection_patterns) or (
            re.match(r'^\d+\.\d+\.\d+\s+', line))  # Match patterns like "3.3.1 Nature of Research"
        
        # Handle chapters
        if is_chapter:
            # Save any accumulated content
            save_current_content()
            
            # Create new chapter
            current_chapter = {
                "title": line,
                "sections": []
            }
            guide_json["chapters"].append(current_chapter)
            current_section = None
            current_subsection = None
        
        # Handle sections
        elif is_section and current_chapter:
            # Save any accumulated content
            save_current_content()
            
            # Create new section
            current_section = {
                "title": line,
                "requirements": "",
                "subsections": []  # Add subsections list
            }
            current_chapter["sections"].append(current_section)
            current_subsection = None
        
        # Handle subsections
        elif is_subsection and current_section:
            # Save any accumulated content
            save_current_content()
            
            # Create new subsection
            current_subsection = {
                "title": line,
                "requirements": ""
            }
            # Ensure subsections exist in section
            if "subsections" not in current_section:
                current_section["subsections"] = []
            current_section["subsections"].append(current_subsection)
        
        # Handle content lines
        elif line:
            content_buffer.append(line)
    
    # Save any remaining content
    save_current_content()
    
    # Process chapters to ensure proper structure
    for chapter in guide_json["chapters"]:
        # If a chapter has no sections, add a section with chapter name
        if not chapter["sections"]:
            # Use the chapter name as the section title without introducing "Introduction"
            section_title = chapter["title"].split(" ")[0] if " " in chapter["title"] else chapter["title"]
            chapter["sections"] = [{
                "title": section_title,
                "requirements": "Please provide content for this section."
            }]
            
        # Process each section to flatten subsections if needed
        for section in chapter["sections"]:
            # If there are subsections but no actual section content, move the first subsection content up
            if "subsections" in section and section["subsections"] and not section["requirements"].strip():
                if len(section["subsections"]) == 1:
                    # If only one subsection, merge it with the section
                    section["requirements"] = section["subsections"][0]["requirements"]
                    del section["subsections"]
            
            # Remove empty subsections list
            if "subsections" in section and not section["subsections"]:
                del section["subsections"]
    
    # Create default structure if no chapters were found
    if not guide_json["chapters"]:
        print("Creating default guide structure")
        guide_json["chapters"] = [{
            "title": "Chapter 1",
            "sections": [{
                "title": "Section 1",
                "requirements": "Please provide content for this section."
            }]
        }]
    
    total_sections = sum(len(ch["sections"]) for ch in guide_json["chapters"])
    total_subsections = sum(
        sum(len(section.get("subsections", [])) for section in ch["sections"])
        for ch in guide_json["chapters"]
    )
    
    print(f"Built guide with {len(guide_json['chapters'])} chapters, {total_sections} sections, and {total_subsections} subsections")
    return guide_json


def extract_text_from_file(content: bytes) -> bytes:
    """
    Extract text from various file formats (DOCX, PDF, plain text).
    This is now a utility function used by our LLM-based parsing.
    """
    
    # Check file types and extract content appropriately
    if isinstance(content, str):
        return content.encode('utf-8')
        
    # Check if it's a DOCX file (starts with PK - zip archive signature)
    if content.startswith(b'PK'):
        try:
            print("Detected DOCX file, extracting text...")
            import io
            from docx import Document
            
            doc = Document(io.BytesIO(content))
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            text = "\n".join(paragraphs)
            print(f"Extracted {len(text)} characters from DOCX")
            return text.encode('utf-8')
        except Exception as e:
            print(f"Error extracting text from DOCX: {str(e)}")
            raise ValueError(f"Failed to extract text from DOCX file: {str(e)}")
    
    # Check if it's a PDF file
    elif content.startswith(b'%PDF'):
        try:
            print("Detected PDF file, extracting text...")
            import io
            from PyPDF2 import PdfReader
            
            pdf = PdfReader(io.BytesIO(content))
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            print(f"Extracted {len(text)} characters from PDF")
            return text.encode('utf-8')
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF file: {str(e)}")
    
    # If not recognized, try as plain text
    else:
        try:
            print("Attempting to decode as text...")
            return content
        except Exception as e:
            print(f"Error with content: {str(e)}")
            return content


def parse_guide_file(content: bytes) -> Dict[str, Any]:
    """
    Parse the guide file content into a structured JSON.
    
    This function converts guide file formats (JSON, text, DOCX, PDF) into a standardized JSON structure.
    
    Args:
        content: The guide file content as bytes
        
    Returns:
        Structured guide JSON
        
    Raises:
        ValueError: If the guide file cannot be parsed
    """
    # Log the file signature for debugging
    file_signature = content[:20].hex()
    print(f"File signature: {file_signature}")
    
    # Check if content is a PDF or DOCX (binary file)
    is_binary = False
    if content.startswith(b'%PDF'):
        print("PDF file detected")
        is_binary = True
    elif content.startswith(b'PK'):
        print("DOCX file detected")
        is_binary = True
    
    # For non-binary files, try parsing as JSON first
    if not is_binary:
        try:
            print("Attempting to parse as JSON...")
            return json.loads(content)
        except Exception as e:
            print(f"Not a valid JSON: {str(e)}")
    
    # For all other files (binary or text that's not JSON), extract text first
    try:
        # Extract text from file (PDF, DOCX, or text)
        text = extract_text_from_file(content)
        
        # Parse the extracted text into guide structure
        return parse_text_to_guide_structure(text)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise ValueError(f"Failed to parse guide file: {str(e)}")
