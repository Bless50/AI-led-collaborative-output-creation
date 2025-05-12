import anthropic
import os

# Get API key from environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("WARNING: ANTHROPIC_API_KEY environment variable not set")
    print("Please set it before running this script")
    exit(1)
    
client = anthropic.Anthropic(api_key=api_key)
print(f"Using Anthropic API with key: {api_key[:5]}...")

# Test the fix with the same pattern we updated in generate_response
try:
    print("Sending test message to Claude...")
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Say hello and explain how the Anthropic API messages format works"}],
        system="You are a helpful API expert. Be brief and concise.",
        temperature=0.7
    )
    
    # Extract the content similar to our generate_response method
    content = response.content[0].text
    
    # Show response
    print("\n=== RESPONSE ===")
    print(f"Received {len(content)} characters")
    print(content[:300] + "..." if len(content) > 300 else content)
    print("=== END RESPONSE ===\n")
    
    print("✅ SUCCESS: API call worked properly with the updated format")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    print("Check your API key and the request format")
