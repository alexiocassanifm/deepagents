"""
Enhanced agent factory with smart compression capabilities for deep planning.

This factory wraps the core deepagents.create_deep_agent() function to add
smart compression features without modifying the core package.
"""

from typing import Sequence, Union, Callable, Any, Optional
from langchain_core.tools import BaseTool
from langchain_core.language_models import LanguageModelLike

# Import core deepagents functionality
from deepagents import create_deep_agent
from deepagents.sub_agent import SubAgent
from deepagents.state import DeepAgentState

# Import local smart compression modules  
from ..context.selective_compression import create_smart_compression_hook
from ..context.archiving_tools import get_archiving_tools
from ..prompts.smart_archiving_prompts import enhance_agent_instructions


def create_enhanced_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent] = None,
    state_schema: Optional[type] = None,
    enable_planning_approval: bool = False,
    checkpointer: Optional[Union[str, Any]] = None,
    pre_model_hook: Optional[Callable] = None,
    enable_smart_compression: bool = True,
):
    """
    Create an enhanced deep agent with smart compression capabilities.
    
    This is a wrapper around deepagents.create_deep_agent() that adds intelligent
    context compression, MCP content archiving, and virtual FS management tools.
    
    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have. Will go in
            the system prompt.
        model: The model to use.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `requires_approval` (bool): Whether this subagent requires plan approval
                - (optional) `approval_points` (list): Specific points where approval is needed
        state_schema: The schema of the deep agent. Should subclass from DeepAgentState
        enable_planning_approval: Whether to enable human-in-the-loop planning approval
        checkpointer: Checkpointer to use for state persistence. Can be:
            - "memory": Use InMemorySaver 
            - "postgres": Use PostgresSaver (requires configuration)
            - Custom checkpointer instance
            - None: No checkpointing (disables human-in-the-loop features)
        pre_model_hook: Optional function to process state before each LLM call.
            Useful for context compression, message filtering, or preprocessing.
            Function should take DeepAgentState and return modified DeepAgentState.
        enable_smart_compression: Enable intelligent selective compression that preserves
            critical elements (todos, virtual FS, system messages) while archiving large
            MCP content. Automatically enhances instructions and adds virtual FS tools.
            
    Returns:
        A LangGraph agent with enhanced capabilities
    """
    enhanced_instructions = instructions
    enhanced_tools = list(tools)
    enhanced_pre_model_hook = pre_model_hook
    
    # Add smart compression capabilities if enabled
    if enable_smart_compression:
        try:
            # Enhance instructions with archiving prompts
            enhanced_instructions = enhance_agent_instructions(instructions)
            
            # Add virtual FS management tools
            archiving_tools = get_archiving_tools()
            enhanced_tools.extend(archiving_tools)
            
            # Create smart compression hook if no pre_model_hook provided
            if pre_model_hook is None:
                enhanced_pre_model_hook = create_smart_compression_hook()
            else:
                # Chain the existing hook with smart compression
                original_hook = pre_model_hook
                smart_hook = create_smart_compression_hook()
                
                def chained_hook(state):
                    # Apply original hook first
                    state = original_hook(state) or state
                    # Then apply smart compression
                    compression_updates = smart_hook(state)
                    if compression_updates:
                        # Merge updates
                        for key, value in compression_updates.items():
                            state[key] = value
                    return state
                
                enhanced_pre_model_hook = chained_hook
                
        except ImportError as e:
            print(f"⚠️ Warning: Smart compression not fully available: {e}")
            print("   Some compression features may be limited.")
    
    # Create the agent using the core deepagents factory
    agent = create_deep_agent(
        tools=enhanced_tools,
        instructions=enhanced_instructions,
        model=model,
        subagents=subagents,
        state_schema=state_schema,
        enable_planning_approval=enable_planning_approval,
        checkpointer=checkpointer,
        pre_model_hook=enhanced_pre_model_hook
    )
    
    return agent


def create_simple_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    **kwargs
):
    """
    Create a simple deep agent without smart compression (direct core wrapper).
    
    This is a convenience function that directly calls deepagents.create_deep_agent()
    without any enhancements, for users who want the basic functionality.
    
    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have.
        model: The model to use.
        **kwargs: All other arguments passed through to create_deep_agent()
        
    Returns:
        A basic LangGraph agent without enhancements
    """
    return create_deep_agent(
        tools=tools,
        instructions=instructions,
        model=model,
        **kwargs
    )


# Convenience aliases for backwards compatibility
enhanced_deep_agent = create_enhanced_deep_agent
simple_deep_agent = create_simple_deep_agent


def get_compression_features_info():
    """
    Get information about available smart compression features.
    
    Returns:
        Dict with information about compression capabilities and requirements
    """
    info = {
        "smart_compression_available": True,
        "features": [
            "Selective message compression preserving todos and system messages",
            "MCP content archiving with [CONTENT TO ARCHIVE] markers", 
            "Virtual filesystem management tools",
            "Automatic large content detection and archiving suggestions",
            "Context-aware compression with preservation rules"
        ],
        "archiving_tools": [
            "organize_virtual_fs() - Analyze and organize virtual filesystem",
            "cleanup_old_archives() - Remove old archive files with retention",
            "archive_content_helper() - Helper for archiving large content",
            "get_archiving_suggestions() - Analyze context for archiving opportunities"
        ],
        "preservation_rules": [
            "Always preserve todo content and task tracking",
            "Always preserve system messages and agent instructions",
            "Always preserve recent context (last 5 messages)",
            "Always preserve virtual filesystem references",
            "Always preserve recent tool results"
        ],
        "archiving_thresholds": {
            "large_content": "3,000 characters (archiving consideration)",
            "huge_content": "5,000 characters (immediate archiving)"
        }
    }
    
    try:
        from ..context.selective_compression import SelectiveCompressor
        from ..context.archiving_tools import get_archiving_tools
        from ..prompts.smart_archiving_prompts import enhance_agent_instructions
        
        archiving_tools = get_archiving_tools()
        info["archiving_tools_count"] = len(archiving_tools)
        info["selective_compressor_available"] = True
        
    except ImportError as e:
        info["smart_compression_available"] = False
        info["import_error"] = str(e)
        info["note"] = "Some compression features may not be available due to missing dependencies"
    
    return info


if __name__ == "__main__":
    # Demo usage
    print("Enhanced Deep Agent Factory")
    print("=" * 40)
    
    # Show available compression features
    features = get_compression_features_info()
    print(f"Smart compression available: {features['smart_compression_available']}")
    print(f"Archiving tools: {features.get('archiving_tools_count', 'Unknown')}")
    
    if features['smart_compression_available']:
        print("\nAvailable features:")
        for feature in features['features']:
            print(f"  - {feature}")
        
        print("\nAvailable archiving tools:")
        for tool in features['archiving_tools']:
            print(f"  - {tool}")
    else:
        print(f"Import error: {features.get('import_error', 'Unknown')}")