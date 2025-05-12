"""
Orchestrator Package - Main entry points for the Orchestrator service.

This package manages the Planner → Executor → Reflector workflow for report generation.
The code is organized into smaller modules by responsibility, keeping each file focused
and maintainable with clear separation of concerns.

Main components:
- models.py: Contains data models (Phase enum, OrchestratorState)
- core.py: Contains the main process_chat_message function and utilities
- state_manager.py: Functions for persisting state to mem0
- phases/: Subpackage containing handlers for each phase
"""

# Re-export main functions and classes for simplified imports
from app.services.orchestrator.models import Phase, OrchestratorState
from app.services.orchestrator.core import process_chat_message
from app.services.orchestrator.utils import extract_section_from_guide

# Export state management functions
from app.services.orchestrator.state_manager import save_orchestrator_state, load_orchestrator_state

# Version info
__version__ = "1.0.0"
