"""
Test creating a sub-agent directly to isolate the error.
"""

import sys
import os

# Add paths
sys.path.insert(0, '../../src')
sys.path.insert(0, '.')

# Apply compatibility patches
from compatibility_layer import ensure_compatibility
ensure_compatibility()

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from deepagents.model import get_model

# Create a simple test tool
@tool
def test_tool(input: str) -> str:
    """A simple test tool."""
    return f"Test result: {input}"

# Get model
model = get_model("openrouter/z-ai/glm-4.5")

print("Creating agent with test tool...")
try:
    agent = create_react_agent(model, prompt="Test agent", tools=[test_tool])
    print("✅ Agent created successfully with test tool")
except Exception as e:
    print(f"❌ Error creating agent with test tool: {e}")

# Now test with the problematic tools
print("\nTesting with deepagents tools...")
from deepagents.tools import write_todos, write_file, read_file, ls, edit_file

tools = [write_todos, write_file, read_file, ls, edit_file]

for tool in tools:
    print(f"\nTesting tool: {getattr(tool, 'name', 'unknown')}")
    try:
        agent = create_react_agent(model, prompt="Test agent", tools=[tool])
        print(f"  ✅ Success")
    except KeyError as e:
        print(f"  ❌ KeyError: {e}")
        # Try to identify the issue
        import inspect
        if hasattr(tool, 'func'):
            func = tool.func
            sig = inspect.signature(func)
            print(f"  Function parameters: {list(sig.parameters.keys())}")
            print(f"  Function annotations: {func.__annotations__ if hasattr(func, '__annotations__') else 'None'}")
    except Exception as e:
        print(f"  ❌ Other error: {e}")