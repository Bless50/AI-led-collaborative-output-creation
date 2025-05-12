import anthropic
import os

# Get API key from environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("WARNING: ANTHROPIC_API_KEY environment variable not set")
    print("Please set it before running this script")
    exit(1)
    
client = anthropic.Anthropic(api_key=api_key)
query = "What is the capital of France?"
system_prompt = "You are a helpful assistant."
message = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": query}
    ]
)
print(message.content)
