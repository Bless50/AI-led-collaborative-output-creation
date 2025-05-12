from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.session_service import get_session_by_id
#from app.services.export_service import generate_chapter_export, generate_full_export

router = APIRouter()


@router.get("/{session_id}/download/chapter/{chapter_idx}")
async def download_chapter(
    session_id: str,
    chapter_idx: int,
    format: str = "pdf",
    db: Session = Depends(get_db)
):
    """
    Download a chapter of the report.
    
    This endpoint generates a PDF or DOCX file for a specific chapter
    by compiling all saved sections in that chapter.
    
    Args:
        session_id: The session ID
        chapter_idx: The chapter index
        format: The export format ("pdf" or "docx")
        db: Database session
        
    Returns:
        FileResponse with the generated file
        
    Raises:
        HTTPException: If the session is not found or the chapter has no saved sections
    """
    # Validate format
    if format not in ["pdf", "docx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Use 'pdf' or 'docx'."
        )
    
    # Get session
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    try:
        # Generate export file
        file_path = await generate_chapter_export(
            db=db,
            session=session,
            chapter_idx=chapter_idx,
            format=format
        )
        
        # Return file
        filename = f"chapter_{chapter_idx}.{format}"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=f"application/{format}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating chapter export: {str(e)}"
        )


@router.get("/{session_id}/download/full")
async def download_full_report(
    session_id: str,
    format: str = "pdf",
    db: Session = Depends(get_db)
):
    """
    Download the full report.
    
    This endpoint generates a PDF or DOCX file for the complete report
    by compiling all saved sections across all chapters.
    
    Args:
        session_id: The session ID
        format: The export format ("pdf" or "docx")
        db: Database session
        
    Returns:
        FileResponse with the generated file
        
    Raises:
        HTTPException: If the session is not found or there are no saved sections
    """
    # Validate format
    if format not in ["pdf", "docx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Use 'pdf' or 'docx'."
        )
    
    # Get session
    session = get_session_by_id(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session with ID {session_id} not found"
        )
    
    try:
        # Generate export file
        file_path = await generate_full_export(
            db=db,
            session=session,
            format=format
        )
        
        # Return file
        filename = f"full_report.{format}"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=f"application/{format}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating full report export: {str(e)}"
        )
