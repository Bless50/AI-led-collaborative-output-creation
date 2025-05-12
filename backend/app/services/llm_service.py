"""
LLM Service for interacting with the Anthropic Claude API.

This service is responsible for:
1. Sending requests to the Claude API
2. Formatting prompts for different phases of the workflow
3. Processing responses from Claude

The service follows the Planner → Executor → Reflector workflow:
- Planner: Determines what to ask or do next
- Executor: Generates content using web search and Claude
- Reflector: Asks Socratic questions to deepen learning

Note: This file is now a lightweight wrapper around the modular implementation in
the 'llm' package. See app/services/llm/ for the actual implementation.
"""
# Re-export the LLMService class as the main entry point
from app.services.llm import LLMService

# Re-export guide parsing functionality
from app.services.llm import parse_guide_to_json

# Re-export phase-specific handlers
from app.services.llm import (
    generate_intake_response,
    generate_planner_response,
    generate_executor_response,
    generate_reflector_response
)

# Re-export utility functions that might be needed externally
from app.services.llm import extract_section_details

# Module metadata
__version__ = "1.0.0"
__author__ = "Report Builder Team"
