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
"""
import os
import json
from typing import Dict, List, Any

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
    
    We use Claude because:
    - It excels at following complex instructions
    - It can generate high-quality content with citations
    - It's effective at asking Socratic questions
    
    
    We use Claude because:
    - It excels at following complex instructions
    - It can generate high-quality content with citations
    - It's effective at asking Socratic questions
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
    
    def parse_guide_to_json(self, guide_text: str) -> Dict[str, Any]:
        """
        Convert report guide text to structured JSON using the LLM.
        
        Args:
            guide_text: The raw text of the report guide.
            
        Returns:
            A dictionary containing the structured guide information.
        """
        import logging
        logging.info("Parsing guide text to JSON using LLM...")
        try:
            # Try to extract the full guide text in one go
            guide_json = self._extract_full_guide(guide_text)
            if guide_json:
                print("✅ Successfully parsed guide file using LLM")
                return guide_json
                
            # If extraction failed, we should implement a chunking approach here
            # but for now we'll return a default empty structure
            return {
                "title": "ERROR: Failed to parse guide",
                "chapters": []
            }
        except Exception as e:
            logging.error(f"Error parsing guide to JSON: {str(e)}")
            # Return a minimal valid structure instead of raising an exception
            return {
                "title": "ERROR: Failed to parse guide",
                "chapters": []
            }
            
    def _sanitize_json(self, text):
        """Attempt to fix common JSON errors in LLM outputs"""
        import re
        try:
            # Step 1: Fix unterminated strings - add missing closing quotes
            # This regex finds strings that start with a quote but don't end with one
            fixed_text = re.sub(r'"([^"]*)(?=[,\}\]\n])', r'"\1"', text)
            
            # Step 2: Replace literal \n with actual newlines if needed
            fixed_text = fixed_text.replace('\\n', '\n')
            
            # Step 3: Fix trailing commas in arrays/objects
            fixed_text = re.sub(r',\s*([\}\]])', r'\1', fixed_text)
            
            # Step 4: Fix missing commas between array items
            fixed_text = re.sub(r'("[^"]*")\s*(")', r'\1, \2', fixed_text)
            
            # Step 5: Handle truncated JSON by balancing braces
            # Count open and close braces/brackets
            open_braces = fixed_text.count('{')
            close_braces = fixed_text.count('}')
            open_brackets = fixed_text.count('[')
            close_brackets = fixed_text.count(']')
            
            # If imbalanced, try to fix by closing any unclosed structures
            if open_braces > close_braces:
                # Add missing closing braces
                fixed_text = fixed_text + ('}' * (open_braces - close_braces))
                print(f"Added {open_braces - close_braces} closing braces to balance JSON")
                
            if open_brackets > close_brackets:
                # Add missing closing brackets
                fixed_text = fixed_text + (']' * (open_brackets - close_brackets))
                print(f"Added {open_brackets - close_brackets} closing brackets to balance JSON")
            
            # Step 6: Remove any trailing commas before closing braces (common JSON error)
            fixed_text = re.sub(r',\s*}', '}', fixed_text)
            
            # Step 7: Try to fix malformed section at truncation point
            # If JSON ends with an unterminated object/property, try to close it properly
            if fixed_text.rstrip().endswith('"'):
                # Unterminated property name, add empty value and close
                fixed_text = fixed_text + '":""'
            
            # Step 8: Ensure the JSON is properly terminated
            # If we have valid opening structure but no closing, add it
            if fixed_text.lstrip().startswith('{') and not fixed_text.rstrip().endswith('}'): 
                fixed_text = fixed_text + '}'
                        
            return fixed_text
        except Exception as e:
            print(f"Error during JSON sanitization: {str(e)}")
            return text
    
    def _extract_full_guide(self, guide_text: str) -> Dict[str, Any]:
        """Attempt to extract the entire guide in one call."""
        try:
            # Create a customized prompt for the guide extraction
            guide_prompt = f"""
        You are a specialized extraction system that converts thesis/report guide text into structured JSON.
        Follow these rules exactly:
        1. Output ONLY valid JSON - no other text before or after
        2. Follow the exact schema provided
        3. Include EVERY SINGLE section and subsection from the text - do NOT skip any
        4. Include COMPLETE and DETAILED requirements for each section
        5. Do not add any additional fields not in the schema
        6. Escape any special characters in text fields
        
        Your TWO primary objectives with EQUAL importance:
        - COMPLETENESS: Include ALL chapters and sections from the guide
        - DETAIL: Capture the FULL requirements for each section
        
        Convert this thesis/report guide into structured JSON following this schema:
        
        {{
          "title": "GUIDE_TITLE",
          "chapters": [
            {{
              "title": "CHAPTER_TITLE",
              "sections": [
                {{
                  "title": "SECTION_TITLE",
                  "requirements": "FULL_SECTION_REQUIREMENTS",
                  "id": "CHAPTER_NUMBER.SECTION_NUMBER"
                }}
              ]
            }}
          ]
        }}
        
        Follow the schema exactly and make sure all information is properly nested.
        Guidelines:
        1. DO NOT SKIP ANY CONTENT - include ALL sections and their COMPLETE requirements
        2. Keep section numbers (like "1.1", "3.3.2") in the titles
        3. If the document uses different terminology (like "Parts" or "Units"), map them to "chapters" and "sections" in the output
        4. Preserve ALL requirement details including bullet points, numbered lists, and specific instructions
        5. If there are multiple sections with the same title but different chapter contexts, include them all
        
        Report guide text:
        {guide_text}
        """
            
            # Use our unified API method that handles different model formats
            response_text = self._call_anthropic_api(
                prompt=guide_prompt,
                max_tokens=8000,  # Set high to get as much as the model can provide
                temperature=0.2
            )
        
            print("\n===== FULL CLAUDE RESPONSE (JSON) =====\n")
            print(response_text)
            print("\n========================================\n")
            
            # Try to parse the response as JSON
            try:
                guide_json = json.loads(response_text)
                print("✅ Successfully parsed LLM response into Python dictionary")
                return guide_json
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed, attempting to fix common errors...")
                # Attempt to fix common JSON errors
                sanitized_json = self._sanitize_json(response_text)
                
                try:
                    guide_json = json.loads(sanitized_json)
                    print("✅ Successfully parsed sanitized JSON response")
                    return guide_json
                except json.JSONDecodeError as e:
                    # If sanitizing didn't work, fall back to regular expression extraction
                    print(f"⚠️ Sanitization failed, using fallback extraction: {str(e)}")
                    # Create a basic structure and extract what we can
                    guide_dict = self._extract_partial_json(response_text)
                    return guide_dict
                # Fall back to the default structure in case of parsing error
                # But we still return a dictionary not a string
                return {
                    "title": "Report Guide",
                    "chapters": [{
                        "title": "Default Chapter",
                        "sections": [{
                            "title": "Default Section",
                            "requirements": "Please provide content for this section."
                        }]
                    }]
                }
        except Exception as e:
            print(f"❌ Error parsing guide with LLM: {str(e)}")
            # Fall back to default structure
            return {
                "title": "Report Guide",
                "chapters": [{
                    "title": "Default Chapter",
                    "sections": [{
                        "title": "Default Section",
                        "requirements": "Please provide content for this section."
                    }]
                }]
            }
        
        # Initialize the memory service
        if not hasattr(self, 'memory_service'):
            self.memory_service = MemoryService()
            
    def _call_anthropic_api(self, prompt, system=None, max_tokens=1000, temperature=0.7):
        """
        Unified method to call Anthropic API that handles different model formats.
        
        This method dynamically chooses between messages API and completions API
        based on the model being used.
        
        Args:
            prompt: User message or prompt content
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Controls randomness
            
        Returns:
            Generated text content
        """
        # Get client
        client = self.get_client()
        
        # Claude-3 models use messages API
        if "claude-3" in self.model:
            try:
                print(f"Using messages API for {self.model}")
                messages = [{"role": "user", "content": prompt}]
                
                # In the latest API version, system is passed directly
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # Only add system parameter if it's provided
                if system:
                    kwargs["system"] = system
                
                response = client.messages.create(**kwargs)
                return response.content[0].text
            except Exception as e:
                print(f"Error using messages API: {str(e)}")
                raise e
        
        # Older models use completions API
        else:
            try:
                print(f"Using completions API for {self.model}")
                # Format prompt for completions API
                import anthropic
                formatted_prompt = ""
                
                # Add system prompt if provided
                if system:
                    formatted_prompt += f"Human: <s>{system}</s>\n\nAssistant: I'll follow those instructions.\n\n"
                
                # Add user message with proper HUMAN_PROMPT/AI_PROMPT markers
                formatted_prompt += f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}"
                
                response = client.completions.create(
                    model=self.model,
                    prompt=formatted_prompt,
                    max_tokens_to_sample=max_tokens,
                    temperature=temperature
                )
                return response.completion
            except Exception as e:
                print(f"Error using completions API: {str(e)}")
                raise e
                
    def _extract_partial_json(self, text):
        """
        Attempt to extract partial JSON structure from malformed LLM output.
        Uses regex to extract key elements even when JSON parsing fails.
        
        Args:
            text: The malformed JSON text to extract from
            
        Returns:
            A basic JSON structure with whatever could be extracted
        """
        import re  # Import re within the method to ensure it's available
        print("Using regex-based partial JSON extraction as fallback")
        
        # Extract title
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        title = title_match.group(1) if title_match else "Extracted Report Guide"
        
        # Extract chapters - this is a simplified approach
        chapters = []
        
        # Try to find chapter titles
        chapter_titles = re.findall(r'"title"\s*:\s*"([^"]+)".*?"sections"', text, re.DOTALL)
        
        # For each potential chapter, create a basic structure
        for i, chapter_title in enumerate(chapter_titles[1:], 1):  # Skip the first which is likely the document title
            # Create a basic chapter structure
            chapter = {
                "title": chapter_title,
                "sections": [{
                    "title": f"Section {i}.1",
                    "requirements": "Content requirements extracted from guide."
                }]
            }
            chapters.append(chapter)
        
        # If we couldn't extract chapters, provide a default
        if not chapters:
            chapters = [{
                "title": "Extracted Chapter",
                "sections": [{
                    "title": "Extracted Section",
                    "requirements": "Please provide content based on the guide."
                }]
            }]
        
        # Return the partially extracted JSON structure
        return {
            "title": title,
            "chapters": chapters
        }
    
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
            max_tokens: Maximum number of tokens in the response
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Claude's response as a dictionary
        """
        try:
            print(f"Generating response with model {self.model}")
            
            # Extract the user message from the messages list
            user_message = ""
            for message in messages:
                if message.get("role", "").lower() == "user":
                    user_message = message.get("content", "")
                    break
            
            # Use our unified API method that handles API format differences
            content = self._call_anthropic_api(
                prompt=user_message,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
                
            print(f"Claude API response complete - received {len(content)} characters")
            
            # Create response dictionary with content
            # Note: We don't have accurate token counts in this unified approach
            return {
                "content": content,
                "usage": {
                    "input_tokens": 0,  # We don't have accurate token counts
                    "output_tokens": 0  # We don't have accurate token counts
                }
            }
        except Exception as e:
            # Log the error and return a fallback response
            print(f"Error calling Claude API: {str(e)}")
            return {
                "content": "I apologize, but I encountered an error while processing your request. Please try again later.",
                "error": str(e)
            }
    
    async def generate_intake_response(
        self,
        session_id: str,
        guide_json: Dict[str, Any],
        intake_json: Dict[str, Any],
        message: str
    ) -> Dict[str, Any]:
        """
        Generate a response for the Intake phase.
        
        During this phase, Claude asks the user for necessary information
        to understand the report requirements before starting the content creation.
        This is the first phase of the workflow where we gather all initial requirements.
        
        Args:
            session_id: The session identifier
            guide_json: The guide structure
            intake_json: The current intake information (may be empty initially)
            message: The user's message
            
        Returns:
            Claude's response as a dictionary
        """
        # Get relevant context from memory
        context = self.memory_service.get_conversation_history(session_id)
        
        # Format context as a string
        context_str = json.dumps(context, indent=2) if context else "No previous conversation"
        
        # Create system prompt for the Intake role
        system_prompt = """
        You are an expert report consultant who helps users define their report requirements.
        Your job is to gather all necessary information before starting the report creation process.
        
        CRITICAL INSTRUCTION: You must format your questions EXACTLY as shown below.
        Always start with EXACTLY ONE tag, followed by ONE clear, specific question.
        DO NOT ask about multiple things in one question.
        
        Your response should only include ONE of these tagged questions at a time:
        [TITLE] What is the exact title of your report?
        [DEPARTMENT] Which academic department or field of study is this report for?
        [OBJECTIVES] What are the primary objectives of your report?
        [PROBLEM] What is the main problem statement or research question?
        [SAMPLE] What is the academic level of this report (undergraduate, masters, etc.)?
        
        EXAMPLE OF CORRECT FORMAT:
        [TITLE] What is the exact title of your report?
        
        EXAMPLES OF INCORRECT FORMAT:
        - What is the topic and focus area of your report? (missing tag)
        - [TITLE] [PROBLEM] What is your report about? (multiple tags)
        - [TITLE] What is your report title and what department is it for? (asking multiple questions)
        
        IMPORTANT RULES:
        1. Use EXACTLY ONE tag from the list above
        2. Ask EXACTLY ONE specific question
        3. Check intake_json first to avoid asking for information you already have
        4. Do not ask multiple questions or request multiple pieces of information
        5. Do not combine topics like "topic and focus area" - ask for one specific thing
        
        Only after you've gathered ALL the tagged fields, indicate the intake process
        is complete by saying "Thank you for providing all the necessary information. We can now
        move to planning your report sections."
        """
        
        # Create messages for the conversation
        messages = [
            {
                "role": "user",
                "content": f"""
                I need help creating a report based on this guide structure:
                {json.dumps(guide_json, indent=2)}
                
                Here's the information I've collected so far:
                {json.dumps(intake_json, indent=2)}
                
                Previous conversation context:
                {context_str}
                
                My current message is: {message}
                
                Please ask me the necessary questions to understand my report requirements.
                """
            }
        ]
        
        # Generate response
        return await self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
    
    async def generate_planner_response(
        self,
        session_id: str,
        guide_json: Dict[str, Any],
        intake_json: Dict[str, Any],
        current_section_id: str,
        db=None,  # Database session parameter
        message: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a response for the Planner phase focused on the current section.
        
        During this phase, Claude helps plan specific sections of the report
        by asking for bullet points for the current section. The AI leads this
        collaborative process, ensuring the user contributes meaningful content.
        
        Args:
            session_id: The session identifier
            guide_json: The guide structure
            intake_json: The current intake information
            current_section_id: ID of the current section being worked on
            db: Database session for retrieving completed sections
            message: The user's message
            
        Returns:
            Claude's response as a dictionary
        """
        # Extract current section details
        current_section = self._extract_section_details(guide_json, current_section_id)
        
        # Get previously completed sections if db session is provided
        completed_sections_html = "No previous section data available."
        if db:
            completed_sections_html = self._get_completed_sections(db, session_id)
        
        # Get relevant context from memory
        context = self.memory_service.get_planner_context(session_id)
        context_str = json.dumps(context, indent=2) if context else "No previous context"
        
        # Create system prompt for the Planner role
        system_prompt = """
        You are an expert report planner who helps users create high-quality academic reports.
        Your job is to guide the user in providing detailed bullet points for the current section.
        
        Ask for 3-5 specific, detailed bullet points that address the requirements for this section.
        If the user's response is too brief or vague, ask targeted follow-up questions.
        Remember this is an AI-led collaborative process where you guide the user's learning.
        """
        
        # Create messages for the conversation
        messages = [
            {
                "role": "user",
                "content": f"""
                I need help with Section {current_section.get('title', current_section_id)} of my report.
                
                GUIDE STRUCTURE:
                {json.dumps(guide_json, indent=2)}
                
                CURRENT SECTION REQUIREMENTS:
                {json.dumps(current_section, indent=2)}
                
                REPORT CONTEXT (from intake):
                {json.dumps(intake_json, indent=2)}
                
                PREVIOUSLY COMPLETED SECTIONS:
                {completed_sections_html}
                
                CONVERSATION HISTORY:
                {context_str}
                
                My current message is: {message}
                
                Please ask me to provide 3-5 detailed bullet points for this specific section.
                """
            }
        ]
        
        # Generate response
        return await self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
    
    def _extract_section_details(self, guide_json: Dict[str, Any], section_id: str) -> Dict[str, Any]:
        """
        Extract details for a specific section from the guide JSON.
        
        Args:
            guide_json: The complete guide structure
            section_id: ID of the section to extract (format: "chapter.section")
            
        Returns:
            Dictionary with section details or empty dict if not found
        """
        # Parse section_id (expected format: "chapter.section")
        try:
            chapter_idx, section_idx = map(int, section_id.split('.'))
        except (ValueError, AttributeError):
            # Handle case where section_id is not in expected format
            return {"error": f"Invalid section_id format: {section_id}"}
        
        # Navigate the guide structure to find the specific section
        try:
            # Adjust indices for zero-based indexing if needed
            chapter = guide_json["chapters"][chapter_idx - 1]
            section = chapter["sections"][section_idx - 1]
            
            # Return a clean section object with chapter context
            return {
                "section_id": section_id,
                "title": section.get("title", ""),
                "requirements": section.get("requirements", ""),
                "chapter_title": chapter.get("title", ""),
                "chapter_id": chapter.get("chapter_id", str(chapter_idx))
            }
        except (IndexError, KeyError):
            # Handle case where indices are out of range or keys don't exist
            return {"error": f"Section {section_id} not found in guide structure"}
    
    def _get_completed_sections(self, db, session_id: str) -> str:
        """
        Retrieve HTML content of previously completed sections from the database.
        
        Args:
            db: Database session
            session_id: The session identifier
            
        Returns:
            String with HTML content of completed sections or message if none found
        """
        from app.db.models.section import Section
        
        # Query database for completed sections (status='saved')
        completed_sections = (
            db.query(Section)
            .filter(Section.session_id == session_id, Section.status == "saved")
            .order_by(Section.chapter_idx, Section.section_idx)
            .all()
        )
        
        if not completed_sections:
            return "No previously completed sections found."
        
        # Format completed sections
        formatted_sections = []
        for section in completed_sections:
            section_id = f"{section.chapter_idx}.{section.section_idx}"
            formatted_sections.append(
                f"SECTION {section_id}:\n{section.draft_html}\n"
            )
        
        return "\n\n".join(formatted_sections)
    
    async def generate_executor_response(
        self,
        session_id: str,
        section_info: Dict[str, Any],
        bullets: List[str],
        search_results: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate content for a section based on bullets and search results.
        
        During this phase, Claude generates draft content with proper citations
        based on the user's bullet points and web search results.
        
        Args:
            session_id: The session identifier
            section_info: Information about the current section
            bullets: User's bullet points for the section
            search_results: Optional search results from web search
            
        Returns:
            Claude's response as a dictionary
        """
        # Get relevant context from memory
        context = self.memory_service.get_executor_context(session_id, section_info, bullets)
        
        # Format context as a string
        context_str = json.dumps(context, indent=2)
        
        # Format search results if provided
        search_results_str = ""
        if search_results:
            search_results_str = f"""
            Use the following search results as references:
            {json.dumps(search_results, indent=2)}
            
            When using information from these sources, provide proper citations.
            """
        
        # Create system prompt for the Executor role
        system_prompt = """
        You are an expert content creator who specializes in writing high-quality report sections.
        Your job is to generate well-structured, informative content based on the user's requirements.
        
        When search results are provided:
        1. Incorporate relevant information from the search results
        2. Provide proper citations using [Source X] format
        3. Ensure factual accuracy and avoid hallucinations
        
        Write in a clear, professional tone and organize the content logically.
        """
        
        # Create messages for the conversation
        messages = [
            {
                "role": "user",
                "content": f"""
                I need you to write content for the following section:
                {json.dumps(section_info, indent=2)}
                
                Here are my key points for this section:
                {json.dumps(bullets, indent=2)}
                
                {search_results_str}
                
                Previous conversation context:
                {context_str}
                
                Please generate well-structured content for this section.
                """
            }
        ]
        
        # Generate response
        return await self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.7
        )
    
    async def generate_reflector_response(
        self,
        session_id: str,
        draft_content: str
    ) -> Dict[str, Any]:
        """
        Generate Socratic questions to help the user reflect on the draft content.
        
        During this phase, Claude asks thought-provoking questions to help the user
        deepen their understanding and improve the content.
        
        Args:
            session_id: The session identifier
            draft_content: The generated draft content
            
        Returns:
            Claude's response as a dictionary
        """
        # Get relevant context from memory
        context = self.memory_service.get_reflector_context(session_id, draft_content)
        
        # Format context as a string
        context_str = json.dumps(context, indent=2)
        
        # Create system prompt for the Reflector role
        system_prompt = """
        You are a Socratic educator who helps users deepen their understanding through reflection.
        Your job is to ask thought-provoking questions about the content to help the user:
        1. Identify gaps or inconsistencies in the content
        2. Consider alternative perspectives or approaches
        3. Deepen their understanding of the subject matter
        
        Ask 3-5 open-ended questions that encourage critical thinking and reflection.
        Be supportive and constructive in your approach.
        """
        
        # Create messages for the conversation
        messages = [
            {
                "role": "user",
                "content": f"""
                I've created the following draft content:
                
                {draft_content}
                
                Previous conversation context:
                {context_str}
                
                Please ask me Socratic questions to help me reflect on and improve this content.
                """
            }
        ]
        
        # Generate response
        return await self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.7
        )
