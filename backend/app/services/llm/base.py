"""
Base functionality for the LLM Service.

This module contains the core LLMService class for interacting with the Anthropic Claude API.
It handles client initialization, API calls, and basic response generation.
"""
import os
from typing import Dict, List, Any, Optional

# Use this import for environment variables if python-dotenv is installed
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: dotenv module not found. Environment variables must be set manually.")

import anthropic

from app.services.memory_service import MemoryService


class LLMService:
    """
    Service for interacting with the Anthropic Claude API.
    
    This service handles all communication with Claude, including:
    1. Formatting prompts for different phases of the workflow
    2. Sending requests to the API
    3. Processing responses
    
    The service follows the Planner → Executor → Reflector workflow:
    - Planner: Determines what to ask or do next
    - Executor: Generates content using web search and Claude
    - Reflector: Asks Socratic questions to deepen learning
    """
    
    def __init__(self, api_key=None, model="claude-3-5-haiku-20241022"):
        """
        Initialize the LLM service with the Anthropic API key.
        
        Args:
            api_key: Optional API key for Anthropic. If not provided, it will be read from
                    environment variables.
            model: The Claude model to use. Defaults to claude-3-5-haiku-20241022
        """
        # Force reload environment variables to ensure they're fresh
        load_dotenv(override=True)
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            print("❌ ERROR: No Anthropic API key found in environment variables or .env file!")
            print("Please set ANTHROPIC_API_KEY in your .env file")
            raise ValueError("Anthropic API key is required. Provide as argument or set ANTHROPIC_API_KEY environment variable.")
            
        # Store model to use
        self.model = model
        
        # We're NOT initializing the client here - we'll do it lazily on first use
        # This avoids timing issues and makes debugging easier
        self._client = None
        
        # Initialize memory service
        self.memory_service = MemoryService()
        
        print(f"✅ LLMService initialized with model: {self.model} (client will be created on first use)")
    
    def get_client(self):
        """
        Get the Anthropic client, creating it if needed.
        
        Returns:
            Initialized Anthropic client
            
        Raises:
            ValueError: If client creation fails
        """
        if self._client is None:
            try:
                print("🔄 Creating Anthropic client...")
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                print("✅ Anthropic client successfully created")
            except Exception as e:
                print(f"❌ ERROR creating Anthropic client: {str(e)}")
                raise ValueError(f"Failed to create Anthropic client: {str(e)}") from e
                
        return self._client
    
    async def _call_anthropic_api(self, prompt, system=None, max_tokens=1000, temperature=0.7):
        """
    Unified method to call Anthropic API that handles different model formats.
    
    This method dynamically chooses between messages API and completions API
    based on the model being used.
    
    Args:
        prompt: The user prompt (optional if content is provided directly)
        system: Optional system prompt
        max_tokens: Maximum tokens to generate
        temperature: Controls randomness
        content: Optional direct content to use instead of prompt
        
    Returns:
        Generated text content
    """
        client = self.get_client()
        
        try:
            # Call the Claude API using the messages endpoint (correct for all Claude 3.x models)
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Return the content from the assistant's message
            return message.content[0].text
        except Exception as e:
            print(f"❌ ERROR calling Anthropic API: {str(e)}")
            # Return error message that will be shown to the user
            return f"Error generating response: {str(e)}"
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude based on the provided messages and system prompt.
        
        Args:
            messages: List of message objects with role and content
            system_prompt: System prompt to set Claude's role and behavior
            max_tokens: Maximum tokens to generate in the response
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Claude's response as a dictionary
        """
        client = self.get_client()
        
        try:
            # Create the message using the Anthropic client
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages
            )
            
            # Extract the response text
            response_text = response.content[0].text
            
            # Return a dictionary with the message and empty metadata
            # Phase-specific handlers will add their own metadata
            return {
                "message": response_text,
                "metadata": {}
            }
        except Exception as e:
            print(f"❌ ERROR generating response: {str(e)}")
            # Return error message that will be shown to the user
            return {
                "message": f"Error generating response: {str(e)}",
                "metadata": {
                    "error": str(e)
                }
            }
