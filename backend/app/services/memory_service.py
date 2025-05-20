import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the actual mem0 client
from mem0 import MemoryClient


class MemoryService:
    """
    Service for managing conversation memory using mem0.
    
    This service handles storing and retrieving conversation context
    throughout the report generation process. We use mem0 because:
    1. It provides persistent memory across user sessions
    2. It enables semantic search for relevant context
    3. It maintains the conversation flow in our Planner → Executor → Reflector loop
    
    The memory layer is crucial for our AI-led workflow as it allows Claude to:
    - Remember previous sections when generating new content
    - Maintain consistency in style and terminology
    - Recall user preferences and constraints
    - Generate relevant reflection questions
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the memory service with the mem0 API key.
        
        Args:
            api_key: Optional API key for mem0. If not provided, it will be read from
                    environment variables.
        """
        # Use provided API key or get from environment
        api_key = api_key or os.getenv("MEM0_API_KEY")
        if not api_key:
            raise ValueError("MEM0_API_KEY not found in environment variables")
            
        # Initialize the mem0 client
        self.client = MemoryClient(api_key=api_key)
    
    def initialize_session_memory(self, session_id: str, guide_json: Dict[str, Any]) -> None:
        """
        Initialize memory for a new session.
        
        We store the guide structure in memory to provide context for the
        Planner phase. This helps the AI understand the report structure
        when generating questions and prompts.
        
        Args:
            session_id: The unique session identifier
            guide_json: The parsed guide structure
        """
        # Create initial system message explaining the guide structure
        system_message = {
            "role": "system",
            "content": f"This is a new report generation session. The guide structure is: {guide_json}"
        }
        
        # Add to mem0 with the session_id as the user_id
        # According to the mem0 guide, we should use the messages parameter
        self.client.add(messages=[system_message], user_id=session_id)
    
    def add_message(self, session_id: str, role: str, content: str, categories=None) -> None:
        """
        Add a message to memory.
        
        This stores a conversation message in mem0 with the appropriate metadata.
        
        Args:
            session_id: The session identifier
            role: The role of the message sender (user or assistant)
            content: The message content
            categories: Optional list of categories to tag this message with
        """
        # According to the mem0 guide, we should structure our data differently
        # We'll use a message object with role and content
        message = {"role": role, "content": content}
        
        # Create add parameters
        add_params = {
            "messages": [message],
            "user_id": session_id
        }
        
        # Add metadata if categories are provided
        if categories:
            add_params["metadata"] = {"categories": categories}
        
        # Add to mem0
        try:
            self.client.add(**add_params)
        except Exception as e:
            print(f"Error adding message to memory: {str(e)}")
            # Continue execution even if memory storage fails
        
    def add_user_message(self, session_id: str, content: str) -> None:
        """
        Add a user message to memory.
        
        Args:
            session_id: The session identifier
            content: The message content
        """
        self.add_message(session_id, "user", content)
        
    def add_assistant_message(self, session_id: str, content: str) -> None:
        """
        Add an assistant message to memory.
        
        Args:
            session_id: The session identifier
            content: The message content
        """
        self.add_message(session_id, "assistant", content)
    
    def get_conversation_history(self, session_id: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        This retrieves all conversation messages for the given session.
        If a query is provided, it will perform a semantic search to find
        relevant messages.
        
        Args:
            session_id: The session identifier
            query: Optional query for semantic search
            
        Returns:
            List of conversation messages
        """
        # The mem0 API expects filters in a specific format
        filters = {
            "user_id": session_id
        }
        
        if query:
            # Semantic search for relevant context
            return self.client.search(query, version="v2", filters=filters)
        else:
            # Get all conversation history
            return self.client.get_all(version="v2", filters=filters, page=1, page_size=100)
    
    def get_intake_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get context for the Intake phase.
        
        This retrieves messages categorized as intake-related for the given session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of intake-related messages
        """
        # For now, just get all messages for this session
        # We'll implement more sophisticated filtering once we understand
        # how categories are stored in mem0
        
        # The mem0 API expects filters in a specific format
        filters = {
            "user_id": session_id
        }
        
        # Get all conversation history for this session
        try:
            return self.client.get_all(version="v2", filters=filters, page=1, page_size=100)
        except Exception as e:
            print(f"Error getting intake context: {str(e)}")
            return []
    
    def get_planner_context(self, session_id: str, current_section: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get context for the Planner phase.
        
        The Planner needs to know:
        1. What information has already been collected
        2. What section we're currently working on
        3. Any user preferences or constraints mentioned
        
        Args:
            session_id: The session identifier
            current_section: Optional current section information
            
        Returns:
            Relevant context for the Planner
        """
        query = f"What information do I need to ask about {current_section['title'] if current_section else 'the report'}?"
        return self.get_conversation_history(session_id, query)
    
    def get_executor_context(self, session_id: str, section_info: Dict[str, Any], bullets: List[str]) -> List[Dict[str, Any]]:
        """
        Get context for the Executor phase.
        
        The Executor needs:
        1. Guide requirements for the current section
        2. User's bullet points
        3. Relevant information from previous sections
        4. Any user preferences or constraints
        
        Args:
            session_id: The session identifier
            section_info: Information about the current section
            bullets: User's bullet points
            
        Returns:
            Relevant context for content generation
        """
        # Create a query that captures the essence of this section
        query = f"Information relevant to writing {section_info['title']} with these key points: {bullets}"
        return self.get_conversation_history(session_id, query)
    
    def get_reflector_context(self, session_id: str, draft_content: str) -> List[Dict[str, Any]]:
        """
        Get context for the Reflector phase.
        
        The Reflector needs:
        1. The current draft content
        2. Previous reflection patterns
        3. User's learning style and preferences
        
        Args:
            session_id: The session identifier
            draft_content: The generated draft content
            
        Returns:
            Relevant context for generating reflection questions
        """
        query = f"What would be good reflection questions about: {draft_content[:200]}..."
        return self.get_conversation_history(session_id, query)
    
    
