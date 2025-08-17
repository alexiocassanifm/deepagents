"""
Test creating an agent with all tools together to reproduce the error.
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
from deepagents.model import get_model
from deepagents.tools import write_todos, write_file, read_file, ls, edit_file

# Import MCP tools
from mcp_integration import initialize_deep_planning_mcp_tools

# Get all tools
print("Getting all tools...")
deep_planning_tools, mcp_wrapper, mcp_client = initialize_deep_planning_mcp_tools()
built_in_tools = [write_todos, write_file, read_file, ls, edit_file]

# Combine all tools
all_tools = list(deep_planning_tools) + built_in_tools

print(f"Total tools: {len(all_tools)}")

# Get model
model = get_model("openrouter/z-ai/glm-4.5")

print("\nCreating agent with all tools...")
try:
    agent = create_react_agent(model, prompt="Test agent", tools=all_tools)
    print("✅ Agent created successfully with all tools")
except KeyError as e:
    print(f"❌ KeyError: {e}")
    print("\nDebugging - checking each tool:")
    
    # Try to find which tool causes the issue
    for i, tool in enumerate(all_tools):
        print(f"\n{i+1}. Tool: {getattr(tool, 'name', 'unknown')}")
        try:
            # Try creating agent with tools up to this point
            test_tools = all_tools[:i+1]
            test_agent = create_react_agent(model, prompt="Test", tools=test_tools)
            print(f"   ✅ OK with {i+1} tools")
        except KeyError as e:
            print(f"   ❌ Failed at tool {i+1}: {e}")
            
            # Check this specific tool
            import inspect
            if hasattr(tool, 'func'):
                func = tool.func
            elif hasattr(tool, '_run'):
                func = tool._run
            elif callable(tool):
                func = tool
            else:
                func = None
                
            if func:
                try:
                    sig = inspect.signature(func)
                    print(f"   Parameters: {list(sig.parameters.keys())}")
                    
                    # Check annotations
                    if hasattr(func, '__annotations__'):
                        print(f"   Annotations: {func.__annotations__}")
                    
                    # Check for missing annotations
                    for param_name in sig.parameters:
                        if param_name not in func.__annotations__ and param_name not in ['self', 'cls']:
                            print(f"   ⚠️ Missing annotation for: {param_name}")
                except Exception as e:
                    print(f"   Error inspecting: {e}")
            break
except Exception as e:
    print(f"❌ Other error: {type(e).__name__}: {e}")