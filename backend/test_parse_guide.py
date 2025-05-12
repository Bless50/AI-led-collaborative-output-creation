import os
import json
import anthropic
import sys

# Force UTF-8 output encoding to handle emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.services.llm_service import LLMService

# This script tests the parse_guide_to_json method directly

def test_parse_guide():
    # Basic guide text for testing
    guide_text = """
    # Thesis Guide
    
    ## Chapter 1: Introduction
    ### 1.1 Background
    Provide context for your research problem and identify the gap your study addresses.
    
    ### 1.2 Objectives
    Clearly state your research aims and objectives.
    """
    
    # Print the version of anthropic we're using
    print(f"Anthropic SDK version: {anthropic.__version__}")
    
    # Initialize LLM service
    print("Creating LLM service...")
    llm_service = LLMService()
    
    # Test parsing
    print("Testing parse_guide_to_json method...")
    try:
        guide_json = llm_service.parse_guide_to_json(guide_text)
        print("\nSuccess! Received response:")
        print(json.dumps(guide_json, indent=2)[:200] + "...")
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_parse_guide()
