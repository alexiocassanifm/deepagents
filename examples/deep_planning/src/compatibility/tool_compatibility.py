"""
Tool Compatibility Layer for DeepAgents

This module provides compatibility fixes for different LLM models that may send
tool parameters in unexpected formats. It acts as a wrapper layer that intercepts
and corrects tool calls before they reach the original deepagents tools.

Key Features:
- Automatic JSON string to Python list conversion for write_todos
- Model-specific compatibility fixes
- Logging for debugging tool call issues
- Zero modifications to original deepagents code
"""

import json
import logging
from typing import Any, Dict, List, Union, Callable
from functools import wraps
from langchain_core.tools import BaseTool, tool
from langchain_core.tools.base import ToolException

# Configure logging for compatibility layer
compatibility_logger = logging.getLogger("deepagents.compatibility")


class ToolCompatibilityError(Exception):
    """Raised when tool compatibility fixes fail."""
    pass


def safe_json_parse(value: Any) -> Any:
    """
    Safely parse a value that might be a JSON string.
    
    Args:
        value: The value to parse - can be string, list, dict, etc.
        
    Returns:
        Parsed value or original value if parsing fails/not needed
    """
    if not isinstance(value, str):
        return value
    
    # Quick check - if it doesn't look like JSON, return as-is
    if not (value.strip().startswith(('[', '{')) and value.strip().endswith((']', '}'))):
        return value
    
    try:
        parsed = json.loads(value)
        compatibility_logger.info(f"Successfully parsed JSON string: {value[:100]}...")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        compatibility_logger.warning(f"Failed to parse potential JSON string: {e}")
        return value


def validate_todo_structure(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and normalize todo structure for write_todos tool.
    
    Args:
        todos: List of todo items to validate
        
    Returns:
        Validated and normalized todo list
        
    Raises:
        ToolCompatibilityError: If todos structure is invalid
    """
    if not isinstance(todos, list):
        raise ToolCompatibilityError(f"todos must be a list, got {type(todos)}")
    
    validated_todos = []
    for i, todo in enumerate(todos):
        if not isinstance(todo, dict):
            raise ToolCompatibilityError(f"Todo item {i} must be a dict, got {type(todo)}")
        
        # Ensure required fields
        if "content" not in todo:
            raise ToolCompatibilityError(f"Todo item {i} missing required 'content' field")
        
        if "status" not in todo:
            todo["status"] = "pending"  # Default status
            
        # Validate status values
        valid_statuses = ["pending", "in_progress", "completed"]
        if todo["status"] not in valid_statuses:
            compatibility_logger.warning(
                f"Todo item {i} has invalid status '{todo['status']}', "
                f"defaulting to 'pending'. Valid statuses: {valid_statuses}"
            )
            todo["status"] = "pending"
        
        # Add id if missing
        if "id" not in todo:
            todo["id"] = f"todo_{i+1}"
        
        validated_todos.append(todo)
    
    return validated_todos


def create_write_todos_wrapper(original_write_todos_tool: BaseTool) -> BaseTool:
    """
    Create a compatibility wrapper for the write_todos tool.
    
    This wrapper intercepts calls to write_todos and handles common format issues:
    - JSON strings passed as todos parameter
    - Missing or invalid todo structure
    - Model-specific serialization issues
    
    Args:
        original_write_todos_tool: The original write_todos tool from deepagents
        
    Returns:
        Wrapped tool with compatibility fixes
    """
    
    @tool(description=original_write_todos_tool.description)
    async def write_todos_compatible(todos: Union[List[Dict[str, Any]], str], **kwargs) -> Any:
        """
        Compatibility wrapper for write_todos that handles various input formats.
        
        Args:
            todos: List of todo items or JSON string representation
            **kwargs: Additional arguments passed to original tool
            
        Returns:
            Result from original write_todos tool
        """
        try:
            # Log the incoming input for debugging
            compatibility_logger.debug(f"write_todos called with type: {type(todos)}, value: {str(todos)[:200]}...")
            
            # Handle JSON string input
            if isinstance(todos, str):
                compatibility_logger.info("Detected JSON string input for write_todos, attempting to parse...")
                todos = safe_json_parse(todos)
                
                if isinstance(todos, str):
                    # Still a string after parsing attempt - this is an error
                    raise ToolCompatibilityError(
                        f"write_todos received string input that couldn't be parsed as JSON: {todos[:100]}..."
                    )
            
            # Validate and normalize the todos structure
            validated_todos = validate_todo_structure(todos)
            
            # Log successful conversion
            compatibility_logger.info(f"Successfully processed {len(validated_todos)} todos for write_todos")
            
            # Call the original tool with validated data
            return await original_write_todos_tool.ainvoke({"todos": validated_todos, **kwargs})
            
        except Exception as e:
            # Log the error for debugging
            compatibility_logger.error(f"write_todos compatibility error: {e}")
            compatibility_logger.error(f"Original input: {todos}")
            
            # Re-raise as ToolException for proper handling by langchain
            raise ToolException(f"write_todos compatibility fix failed: {e}")
    
    # Copy metadata from original tool
    write_todos_compatible.name = original_write_todos_tool.name
    write_todos_compatible.description = original_write_todos_tool.description
    
    return write_todos_compatible


def apply_tool_compatibility_fixes(tools: List[Any], model_name: str = None) -> List[Any]:
    """
    Apply compatibility fixes to a list of tools.
    
    Args:
        tools: List of tools to apply fixes to (can be BaseTool or callable)
        model_name: Optional model name for model-specific fixes
        
    Returns:
        List of tools with compatibility fixes applied
    """
    fixed_tools = []
    fixes_applied = []
    
    for tool in tools:
        # Handle both BaseTool objects and callable functions
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        
        if tool_name == "write_todos":
            # Apply write_todos compatibility fix
            fixed_tool = create_write_todos_wrapper(tool)
            fixed_tools.append(fixed_tool)
            fixes_applied.append("write_todos")
            compatibility_logger.info("Applied write_todos compatibility fix")
        else:
            # No fix needed, keep original tool
            fixed_tools.append(tool)
    
    if fixes_applied:
        compatibility_logger.info(f"Applied compatibility fixes for: {', '.join(fixes_applied)}")
    else:
        compatibility_logger.debug("No compatibility fixes needed for provided tools")
    
    return fixed_tools


def setup_compatibility_logging(level: str = "INFO") -> None:
    """
    Setup logging for the compatibility layer.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper())
    compatibility_logger.setLevel(log_level)
    
    # Create console handler if not already exists
    if not compatibility_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        compatibility_logger.addHandler(handler)
    
    compatibility_logger.info(f"Tool compatibility logging setup with level: {level}")


# Example usage and testing functions
if __name__ == "__main__":
    # Test the compatibility functions
    
    # Test JSON string parsing
    test_json_string = '[{"content": "Test todo", "status": "pending"}]'
    parsed = safe_json_parse(test_json_string)
    print(f"Parsed JSON: {parsed}")
    
    # Test todo validation
    test_todos = [
        {"content": "Valid todo", "status": "pending"},
        {"content": "Todo without status"},  # Will get default status
        {"content": "Todo with invalid status", "status": "invalid"}  # Will be corrected
    ]
    
    validated = validate_todo_structure(test_todos)
    print(f"Validated todos: {validated}")