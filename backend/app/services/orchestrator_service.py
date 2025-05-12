"""
Orchestrator Service for managing the Planner → Executor → Reflector flow.

This service is responsible for:
1. Processing chat messages
2. Determining the current phase (Planner, Executor, Reflector)
3. Routing messages to the appropriate handler
4. Maintaining conversation context and state through mem0

The orchestrator follows a three-phase workflow:
- Planner: Determines what to ask or do next
- Executor: Generates content using web search and Claude
- Reflector: Asks Socratic questions to deepen learning

Note: This file is now a lightweight wrapper around the modular implementation in
the 'orchestrator' package. See app/services/orchestrator/ for the actual implementation.
"""
# Re-export main components from the orchestrator package
from app.services.orchestrator import (
    # Core models
    Phase,
    OrchestratorState,
    
    # Main entry point
    process_chat_message,
    
    # State management
    save_orchestrator_state,
    load_orchestrator_state,
    
    # Utility functions
    extract_section_from_guide
)

# Module metadata
__version__ = "1.0.0"
__author__ = "Report Builder Team"
