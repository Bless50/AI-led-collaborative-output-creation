import json
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.session import SessionCreate, SessionState, IntakeResponse
from app.services.llm_service import LLMService
from app.services.llm.guide_parser import parse_guide_to_json
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
        
        # Extract text from the file
        guide_text = extract_text_from_file(guide_content).decode('utf-8') \
            if isinstance(guide_content, bytes) else guide_content
        
        # Validate API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Missing ANTHROPIC_API_KEY environment variable"
            )
            
        try:
            # Initialize LLM service for logging/tracking
            print("🔄 Initializing LLM service with claude-3-5-haiku-20241022...")
            llm_service = LLMService()
            
            # Send guide text to be parsed by the LLM service
            print("🔄 Sending guide to Claude API for parsing...")
            guide_json = await parse_guide_to_json(llm_service, guide_text)
            
            print("✅ Successfully parsed guide using Claude LLM")
        except Exception as e:
            print(f"❌ LLM parsing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse guide file with LLM: {str(e)}"
            )
        
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
            #print the extracted text
            print(text)
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
        # For any other type of content, just return as is
        print("Attempting to use content as is...")
        return content
