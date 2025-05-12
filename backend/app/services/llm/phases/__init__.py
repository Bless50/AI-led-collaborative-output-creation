"""
Phase-specific handlers for the LLM Service.

This subpackage contains specialized modules for each phase of the 
Planner → Executor → Reflector workflow:

1. Intake: Gathering initial report requirements
2. Planning: Planning section content with bullet points
3. Execution: Generating drafts with web search integration
4. Reflection: Asking Socratic questions about the draft

Each phase handler formats prompts specific to its phase and processes
the responses from Claude accordingly.
"""

# Export phase-specific handler functions
from app.services.llm.phases.intake import generate_intake_response
from app.services.llm.phases.planning import generate_planner_response
from app.services.llm.phases.execution import generate_executor_response
from app.services.llm.phases.reflection import generate_reflector_response
