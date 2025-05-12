"""
Models for the Orchestrator service.

This module contains the data models used by the orchestrator service:
- Phase enum: Represents the different phases of the report generation workflow
- OrchestratorState: Tracks state across requests in the Planner → Executor → Reflector flow
"""
import json
from enum import Enum
from typing import Dict, Optional, Any

from app.services.memory_service import MemoryService


class Phase(str, Enum):
    """
    Enum representing the different phases of the report generation process.
    
    The workflow follows a Planner → Executor → Reflector architecture:
    - INTAKE: Initial gathering of report requirements
    - PLANNING: Planning section content with bullet points
    - EXECUTION: Generating drafts with web search integration
    - REFLECTION: Asking Socratic questions about the draft
    """
    INTAKE = "intake"
    PLANNING = "planning"
    EXECUTION = "execution"
    REFLECTION = "reflection"


class OrchestratorState:
    """
    Class to represent the current state of the orchestration process.
    
    This class tracks the current phase, section, and other state information
    needed for the Planner → Executor → Reflector workflow. While chat history
    is stored in mem0, we keep track of the current phase and section here.
    
    Attributes:
        session_id (str): Unique identifier for the session
        phase (Phase): Current phase of the workflow
        current_section_id (Optional[str]): Current section being worked on (format: "chapter.section")
        memory_service (MemoryService): Service for storing/retrieving memory
    """
    def __init__(
        self,
        session_id: str,
        phase: Phase = Phase.INTAKE,
        current_section_id: Optional[str] = None,
    ):
        """
        Initialize the orchestrator state.
        
        Args:
            session_id: Unique identifier for the session
            phase: Current phase of the workflow (default: intake)
            current_section_id: Current section ID (format: "chapter.section")
        """
        self.session_id = session_id
        self.phase = phase
        self.current_section_id = current_section_id
        # Initialize memory service for this session
        self.memory_service = MemoryService()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for storage.
        
        Returns:
            Dictionary representation of the state
        """
        return {
            "session_id": self.session_id,
            "phase": self.phase,
            "current_section_id": self.current_section_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorState":
        """
        Create state from dictionary.
        
        Args:
            data: Dictionary containing state data
            
        Returns:
            Initialized OrchestratorState instance
        """
        return cls(
            session_id=data["session_id"],
            phase=data["phase"],
            current_section_id=data["current_section_id"],
        )
