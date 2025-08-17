"""
Debug script to identify which tool has the problematic signature.
"""

import sys
import os
import inspect
from typing import get_type_hints

# Add paths
sys.path.insert(0, '../../src')
sys.path.insert(0, '.')

# Apply compatibility patches
from ..compatibility.compatibility_layer import ensure_compatibility
ensure_compatibility()

# Import MCP integration to get the actual tools
from ..integrations.mcp.mcp_integration import initialize_deep_planning_mcp_tools

# Get the tools that would be passed to the agent
deep_planning_tools, mcp_wrapper, mcp_client = initialize_deep_planning_mcp_tools()

print(f"Total tools: {len(deep_planning_tools)}")
print("=" * 60)

# Check each tool
for i, tool in enumerate(deep_planning_tools):
    print(f"\n{i+1}. Tool: {getattr(tool, 'name', 'unknown')}")
    
    # Try to get the underlying function
    func = None
    if hasattr(tool, 'func'):
        func = tool.func
    elif hasattr(tool, '_run'):
        func = tool._run
    elif callable(tool):
        func = tool
    
    if func:
        try:
            # Try to get signature
            sig = inspect.signature(func)
            print(f"   Parameters: {list(sig.parameters.keys())}")
            
            # Check for missing annotations
            for param_name, param in sig.parameters.items():
                if param.annotation == inspect.Parameter.empty and param_name not in ['self', 'cls']:
                    print(f"   ⚠️ Missing annotation: {param_name}")
            
            # Try to get type hints (this is where the error might occur)
            try:
                hints = get_type_hints(func)
                print(f"   Type hints: {list(hints.keys())}")
            except Exception as e:
                print(f"   ❌ Error getting type hints: {e}")
                
        except Exception as e:
            print(f"   Error inspecting: {e}")
    else:
        print("   Could not get underlying function")

print("\n" + "=" * 60)
print("Checking built-in tools...")
print("=" * 60)

from deepagents.tools import write_todos, write_file, read_file, ls, edit_file
built_in_tools = [write_todos, write_file, read_file, ls, edit_file]

for tool in built_in_tools:
    print(f"\nTool: {getattr(tool, 'name', 'unknown')}")
    
    # Try to get the underlying function
    func = None
    if hasattr(tool, 'func'):
        func = tool.func
    elif hasattr(tool, '_run'):
        func = tool._run
    elif callable(tool):
        func = tool
    
    if func:
        try:
            sig = inspect.signature(func)
            print(f"   Parameters: {list(sig.parameters.keys())}")
            
            # Check for tool_input specifically
            if 'tool_input' in sig.parameters:
                print(f"   ⚠️ FOUND 'tool_input' parameter!")
                
        except Exception as e:
            print(f"   Error: {e}")