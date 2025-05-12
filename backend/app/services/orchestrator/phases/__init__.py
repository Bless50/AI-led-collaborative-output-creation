"""
Phase handlers for the Orchestrator service.

This subpackage contains handlers for each phase of the 
Planner → Executor → Reflector workflow:

1. Intake: Gathering initial report requirements
2. Planning: Planning section content with bullet points
3. Execution: Generating drafts with web search integration
4. Reflection: Asking Socratic questions about the draft

Each phase handler is responsible for:
- Processing user input for that phase
- Generating appropriate responses
- Managing state transitions between phases
"""

# Export phase handlers for simplified imports
from app.services.orchestrator.phases.intake import handle_intake_phase
from app.services.orchestrator.phases.planning import handle_planning_phase
from app.services.orchestrator.phases.execution import handle_execution_phase
from app.services.orchestrator.phases.reflection import handle_reflection_phase
