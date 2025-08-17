"""
Compatibility utilities for deepagents.

This module provides functions to ensure compatibility with various
LangChain and Pydantic versions, particularly around tool signatures.
"""

import inspect
import logging
from typing import Any, List
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def fix_tool_signatures_safe(tools: List) -> List:
    """
    Fix function signatures for tools that have missing type annotations.
    This specifically handles cases where parameters lack type hints,
    which can cause issues with Pydantic's validate_arguments decorator.
    
    Args:
        tools: List of tools to fix
        
    Returns:
        List of tools with fixed signatures
    """
    if not tools:
        return tools
        
    fixed_tools = []
    
    for tool in tools:
        try:
            # Get the actual function to inspect
            func = None
            if isinstance(tool, BaseTool):
                # For BaseTool instances, get the underlying function
                if hasattr(tool, 'func'):
                    func = tool.func
                elif hasattr(tool, '_run'):
                    func = tool._run
            elif callable(tool):
                func = tool
            
            if func and callable(func):
                # Get function signature
                sig = inspect.signature(func)
                params = sig.parameters
                
                # Check if any parameter lacks annotation
                needs_fix = False
                for param_name, param in params.items():
                    if param.annotation == inspect.Parameter.empty and param_name not in ['self', 'cls']:
                        needs_fix = True
                        break
                
                if needs_fix:
                    # Fix the function's __annotations__ dictionary
                    if not hasattr(func, '__annotations__'):
                        func.__annotations__ = {}
                    
                    for param_name, param in params.items():
                        if param.annotation == inspect.Parameter.empty and param_name not in ['self', 'cls']:
                            # Add Any type hint for missing annotations
                            func.__annotations__[param_name] = Any
                            logger.debug(f"Added type annotation for parameter '{param_name}' in function")
            
        except Exception as e:
            # If we can't fix it, just log and continue
            logger.debug(f"Could not inspect/fix function signatures for tool: {e}")
        
        fixed_tools.append(tool)
    
    return fixed_tools