import anthropic
import sys
import os

# Print details about the environment and package
print(f"Python version: {sys.version}")
print(f"Anthropic version: {anthropic.__version__}")
print(f"Anthropic package location: {anthropic.__file__}")

# Examine the structure of the Anthropic client
client = anthropic.Anthropic()
print(f"Client type: {type(client)}")
print(f"Client directory: {dir(client)[:20]}")  # First 20 attributes

# Check if specific APIs exist
print("\nAPI Check:")
has_messages = hasattr(client, "messages")
has_completions = hasattr(client, "completions")
print(f"Has 'messages' API: {has_messages}")
print(f"Has 'completions' API: {has_completions}")

# Try to access the structure
if has_messages:
    print("Messages API structure:", dir(client.messages)[:10])
if has_completions:
    print("Completions API structure:", dir(client.completions)[:10])

print("\nDone!")
