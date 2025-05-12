"""
LLM Service Package - Main entry points for interacting with the Anthropic Claude API.

This package handles all communication with Claude, including:
1. Formatting prompts for different phases of the workflow
2. Sending requests to the API
3. Processing responses

The code is organized into smaller modules by responsibility:
- base.py: Core API functionality (client initialization, API calls)
- guide_parser.py: Functions for parsing guide text to JSON
- phases/: Handlers for different phases (intake, planning, execution, reflection)
- utils.py: Helper functions used across modules
"""

# Re-export main LLMService class and important components
from app.services.llm.base import LLMService

# Export guide parsing functionality
from app.services.llm.guide_parser import parse_guide_to_json

# Export phase-specific handlers
from app.services.llm.phases import (
    generate_intake_response,
    generate_planner_response,
    generate_executor_response,
    generate_reflector_response
)

# Export utility functions that might be needed externally
from app.services.llm.utils import extract_section_details

# Version info
__version__ = "1.0.0"
