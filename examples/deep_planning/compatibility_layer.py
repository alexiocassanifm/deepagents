"""
Compatibility Layer for Type Annotations and Pydantic/LangChain Integration

This module provides comprehensive type annotation fixes and patches to ensure
compatibility between different versions of Pydantic, LangChain, and other
dependencies. It centralizes all type-related workarounds and patches.

Key Features:
- Type annotation imports with fallbacks
- Pydantic component initialization
- Global type availability setup
- Module patching for deep compatibility
- Model compatibility detection and fixes
"""

import logging
import sys
import builtins
from typing import Any, Dict, List, Optional

# Setup logger for compatibility operations
logger = logging.getLogger(__name__)

def setup_type_patches():
    """
    Apply comprehensive type annotation patches for Pydantic/LangChain compatibility.
    This function sets up all necessary type aliases and patches modules to ensure
    compatibility across different versions of dependencies.
    
    Returns:
        bool: True if patches were successfully applied, False otherwise
    """
    try:
        # Import type annotations with fallback
        try:
            from typing import Annotated, Optional, Callable, Awaitable
        except ImportError:
            from typing_extensions import Annotated, Optional, Callable, Awaitable
        
        # Import all necessary Pydantic components
        try:
            from pydantic import BaseModel, Field, SkipValidation
            from pydantic.fields import FieldInfo
            from pydantic.dataclasses import dataclass as pydantic_dataclass
            from pydantic._internal._typing_extra import eval_type_lenient
            from pydantic.json_schema import GenerateJsonSchema
            from pydantic_core import core_schema, SchemaValidator
            
            # Create ArgsSchema type alias if missing
            ArgsSchema = type("ArgsSchema", (BaseModel,), {})
            
        except ImportError as e:
            logger.warning(f"Could not import Pydantic components: {e}")
            # Create basic fallbacks
            ArgsSchema = type("ArgsSchema", (), {})
            SkipValidation = type("SkipValidation", (), {})
            BaseModel = None
            Field = None
            FieldInfo = None
        
        # Make all types available globally
        builtins.Annotated = Annotated
        builtins.ArgsSchema = ArgsSchema
        builtins.SkipValidation = locals().get('SkipValidation', type("SkipValidation", (), {}))
        builtins.Optional = Optional
        builtins.Callable = Callable
        builtins.Any = Any
        builtins.Awaitable = Awaitable
        builtins.tool_input = Any
        
        # Update global namespace
        globals().update({
            'Annotated': Annotated,
            'ArgsSchema': ArgsSchema,
            'SkipValidation': locals().get('SkipValidation', type("SkipValidation", (), {})),
            'Optional': Optional,
            'Callable': Callable,
            'Any': Any,
            'Awaitable': Awaitable,
            'tool_input': Any,
            'BaseModel': BaseModel,
            'Field': Field,
            'FieldInfo': FieldInfo
        })
        
        # Patch typing module
        import typing
        typing.Annotated = Annotated
        typing.ArgsSchema = ArgsSchema
        typing.SkipValidation = locals().get('SkipValidation', type("SkipValidation", (), {}))
        typing.Optional = Optional
        typing.Callable = Callable
        typing.Any = Any
        typing.Awaitable = Awaitable
        typing.tool_input = Any
        
        # Define modules to patch
        module_patches = {
            'deepagents.tools': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
            'deepagents.sub_agent': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'], 
            'deepagents.state': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
            'langchain_core.tools.base': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
            'langchain_core.tools.convert': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
            'langchain_core.tools.structured': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
            'pydantic.deprecated.decorator': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input']
        }
        
        # Apply patches to modules
        apply_module_patches(module_patches)
        
        logger.info("Type patches successfully applied")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply type patches: {e}")
        return False


def apply_module_patches(module_patches: Dict[str, List[str]]):
    """
    Apply type patches to specified modules.
    
    Args:
        module_patches: Dictionary mapping module names to list of attributes to patch
    """
    for module_name, attrs in module_patches.items():
        try:
            import importlib
            if module_name in sys.modules:
                module = sys.modules[module_name]
                for attr in attrs:
                    if not hasattr(module, attr):
                        setattr(module, attr, globals().get(attr, Any))
                logger.debug(f"Patched module {module_name} with attributes: {attrs}")
        except Exception as e:
            # Log but don't fail - some modules may not be available
            logger.debug(f"Note: Could not patch {module_name}: {e}")


def get_compatibility_info() -> Dict[str, Any]:
    """
    Get information about current compatibility setup.
    
    Returns:
        Dictionary containing compatibility information
    """
    info = {
        "python_version": sys.version,
        "patches_applied": hasattr(builtins, 'ArgsSchema'),
        "typing_module_patched": hasattr(sys.modules.get('typing', {}), 'ArgsSchema'),
        "pydantic_available": 'pydantic' in sys.modules,
        "langchain_available": 'langchain_core' in sys.modules,
    }
    
    # Check for specific type availability
    type_checks = ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Awaitable']
    info['available_types'] = {t: hasattr(builtins, t) for t in type_checks}
    
    return info


def print_compatibility_report():
    """
    Print a detailed compatibility report to help with debugging.
    """
    info = get_compatibility_info()
    
    print("\n" + "="*60)
    print("COMPATIBILITY LAYER REPORT")
    print("="*60)
    print(f"Python Version: {info['python_version'].split()[0]}")
    print(f"Patches Applied: {'✅' if info['patches_applied'] else '❌'}")
    print(f"Typing Module Patched: {'✅' if info['typing_module_patched'] else '❌'}")
    print(f"Pydantic Available: {'✅' if info['pydantic_available'] else '❌'}")
    print(f"LangChain Available: {'✅' if info['langchain_available'] else '❌'}")
    
    print("\nAvailable Types:")
    for type_name, available in info['available_types'].items():
        status = '✅' if available else '❌'
        print(f"  {type_name}: {status}")
    
    print("="*60 + "\n")


def ensure_compatibility():
    """
    Ensure compatibility by applying patches if not already applied.
    This is a convenience function that can be called multiple times safely.
    
    Returns:
        bool: True if compatibility is ensured, False otherwise
    """
    if not hasattr(builtins, 'ArgsSchema'):
        logger.info("Applying compatibility patches...")
        return setup_type_patches()
    else:
        logger.debug("Compatibility patches already applied")
        return True


# Auto-apply patches on import if needed
if __name__ != "__main__":
    ensure_compatibility()