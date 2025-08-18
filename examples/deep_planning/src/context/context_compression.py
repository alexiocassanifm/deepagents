"""
Context Compression Module for Deep Planning Agent

This module provides context compression and compaction functionality to manage
token limits and optimize conversation context. It includes automatic triggering,
compression hooks, and metrics tracking.

Key Features:
- Automatic context compaction when thresholds are exceeded
- Integration with MCP wrapper for noise reduction
- Compression hooks for post-tool execution
- Metrics tracking and reporting
- Async and sync compression support
"""

import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# Setup logger for compression operations
logger = logging.getLogger(__name__)

# Import dependencies if available
try:
    from .compact_integration import CompactIntegration
    from .compact_integration import EnhancedCompactIntegration
    COMPACT_AVAILABLE = True
except ImportError:
    COMPACT_AVAILABLE = False
    logger.warning("⚠️ Compact integration not available")

try:
    from ..config.config_loader import get_trigger_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logger.warning("⚠️ Config loader not available")


def check_and_compact_if_needed(
    messages: List[Dict[str, Any]], 
    context: Dict[str, Any] = None,
    compact_integration: Optional[Any] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Check if automatic compaction is needed and perform it if necessary.
    
    Args:
        messages: Current conversation messages
        context: Additional context for compaction
        compact_integration: CompactIntegration instance
    
    Returns:
        Tuple of (compacted_messages, compaction_summary)
    """
    if compact_integration is None:
        # No compaction available, return original messages
        logger.info(f"⏸️ COMPACTION CHECK SKIPPED - No compact_integration available")
        return messages, None
    
    try:
        # 🔍 LOG: General compaction check
        logger.info(f"🔍 GENERAL COMPACTION CHECK - Evaluating {len(messages)} messages for compaction need")
        
        # Check if compaction should be triggered
        should_compact, trigger_type, metrics = compact_integration.should_trigger_compaction(messages)
        
        if should_compact:
            logger.info(f"📦 Context compaction triggered: {trigger_type.value}")
            logger.info(f"📊 Context metrics: {metrics.utilization_percentage:.1f}% utilization (simplified context management)")
            
            # Perform automatic compaction
            compacted_messages, summary = compact_integration.perform_automatic_compaction(messages, context)
            
            logger.info(f"✅ Context compacted: {summary.total_reduction_percentage:.1f}% reduction")
            logger.info(f"📝 Summary: {len(summary.summary_content)} chars generated")
            
            return compacted_messages, summary.summary_content
        else:
            # No compaction needed
            return messages, None
            
    except Exception as e:
        logger.error(f"⚠️ Compaction check failed: {e}")
        # Return original messages if compaction fails
        return messages, None


def get_compaction_metrics(
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Get current compaction system metrics.
    
    Args:
        compact_integration: CompactIntegration instance
        mcp_wrapper: MCP wrapper instance for statistics
        
    Returns:
        Dictionary containing compaction metrics or None
    """
    if compact_integration is None:
        return None
    
    try:
        metrics = {
            "compaction_history_count": len(compact_integration.compact_history),
            "last_compaction": None,
            "total_reductions": [],
            "mcp_wrapper_stats": None
        }
        
        if compact_integration.compact_history:
            metrics["last_compaction"] = compact_integration.compact_history[-1].timestamp
            metrics["total_reductions"] = [s.total_reduction_percentage for s in compact_integration.compact_history]
        
        if mcp_wrapper:
            metrics["mcp_wrapper_stats"] = mcp_wrapper.get_statistics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"⚠️ Failed to get compaction metrics: {e}")
        return None


def wrap_tools_with_compression_hooks(
    tools: List[Any],
    enhanced_compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> List[Any]:
    """
    Wrap tools with automatic POST_TOOL compression hooks.
    
    This approach works correctly with LangGraph since tools are called directly
    by the agent nodes. We create new tools that access the LangGraph state
    and can perform compression after tool execution.
    
    Args:
        tools: List of tools to wrap
        enhanced_compact_integration: EnhancedCompactIntegration instance
        mcp_wrapper: MCP wrapper for context management
        
    Returns:
        List of wrapped tools with compression hooks
    """
    if enhanced_compact_integration is None:
        logger.warning("No enhanced compact integration available, returning unwrapped tools")
        return tools
    
    # Import here to avoid circular imports
    from langchain_core.tools import tool
    from langgraph.prebuilt import InjectedState
    from typing import Annotated
    
    wrapped_tools = []
    wrapped_count = 0  # Track successfully wrapped tools
    monitor_logger = logging.getLogger('mcp_context_tracker')
    
    # Get trigger config for this scope
    trigger_config = get_trigger_config() if CONFIG_AVAILABLE else {}
    
    for orig_tool in tools:
        tool_name = getattr(orig_tool, 'name', getattr(orig_tool, '__name__', 'Unknown'))
        tool_description = getattr(orig_tool, 'description', f"Wrapped version of {tool_name}")
        
        # Store both the tool and the callable for flexible access
        original_tool = orig_tool
        
        # More robust tool detection - handle Pydantic v2 StructuredTool objects
        func_type = None
        original_func = None
        
        # Try to get func attribute (for tools with .func)
        try:
            func_attr = getattr(orig_tool, 'func', None)
            if func_attr and callable(func_attr):
                original_func = func_attr
                func_type = 'func'
        except Exception:
            pass
        
        # Try to get invoke method (for LangChain and MCP tools)
        if not original_func:
            try:
                invoke_method = getattr(orig_tool, 'invoke', None)
                if invoke_method and callable(invoke_method):
                    original_func = invoke_method
                    func_type = 'invoke'
            except Exception:
                pass
        
        # Fallback to direct callable
        if not original_func:
            try:
                if callable(orig_tool):
                    original_func = orig_tool
                    func_type = 'callable'
            except Exception:
                pass
        
        # If we still can't find a callable, skip wrapping
        if not original_func or not func_type:
            logger.warning(f"⚠️ Cannot wrap tool {tool_name} - no callable found, using original")
            wrapped_tools.append(orig_tool)
            continue
        
        def create_wrapped_tool_func(orig_tool_obj, orig_func, func_type, tool_nm):
            """Create wrapper function with state access for compression."""
            
            # Create a new tool function that has access to LangGraph state
            async def wrapped_tool_with_state(*args, **kwargs):
                """Wrapped tool with POST_TOOL compression via state access."""
                
                # Extract state if present in kwargs (LangGraph injects it)
                state = None
                
                # Method 1: Look for explicit state parameter
                if 'state' in kwargs:
                    state = kwargs['state']
                    monitor_logger.debug(f"Found explicit state parameter for {tool_nm}")
                
                # Method 2: Look for parameters that look like LangGraph state
                if state is None:
                    for key, value in kwargs.items():
                        # Check if this looks like a LangGraph state object
                        if (hasattr(value, 'get') and 
                            isinstance(value, dict) and 
                            'messages' in value):
                            state = value
                            monitor_logger.debug(f"Found state-like parameter '{key}' for {tool_nm}")
                            break
                
                # Method 3: Look in args for state-like objects
                if state is None:
                    for i, arg in enumerate(args):
                        if (hasattr(arg, 'get') and 
                            isinstance(arg, dict) and 
                            'messages' in arg):
                            state = arg
                            monitor_logger.debug(f"Found state-like arg at position {i} for {tool_nm}")
                            break
                
                # Execute original tool based on its type
                try:
                    if func_type == 'invoke':
                        # This is a LangChain tool - call tool.invoke(input)
                        # Prepare input data from args and kwargs
                        if len(args) == 1 and isinstance(args[0], dict):
                            # Direct input dict
                            input_data = args[0]
                        elif len(args) == 1 and isinstance(args[0], str):
                            # String input - wrap in dict  
                            input_data = {"input": args[0]}
                        elif kwargs:
                            # Use kwargs as input (this is the most common case for LangGraph)
                            input_data = kwargs
                        else:
                            # Empty input
                            input_data = {}
                        
                        monitor_logger.debug(f"Calling {tool_nm} with input: {input_data}")
                        
                        # StructuredTool and most LangChain tools are async
                        # Always use await for LangChain tools to be safe
                        result = await orig_tool_obj.invoke(input_data)
                    
                    elif func_type == 'func':
                        # This tool has a .func attribute
                        if asyncio.iscoroutinefunction(orig_func):
                            result = await orig_func(*args, **kwargs)
                        else:
                            result = orig_func(*args, **kwargs)
                    
                    elif func_type == 'callable':
                        # Direct callable
                        if asyncio.iscoroutinefunction(orig_func):
                            result = await orig_func(*args, **kwargs)
                        else:
                            result = orig_func(*args, **kwargs)
                    else:
                        raise ValueError(f"Unknown function type: {func_type}")
                        
                except Exception as e:
                    logger.error(f"❌ Tool {tool_nm} execution failed: {e}")
                    monitor_logger.error(f"Tool execution error - Type: {func_type}, Args: {len(args)}, Kwargs: {list(kwargs.keys())}")
                    monitor_logger.error(f"Input data prepared: {locals().get('input_data', 'N/A')}")
                    raise
                
                # Perform POST_TOOL compression check if we have state access
                if state is not None:
                    try:
                        monitor_logger.info(f"🔧 TOOL EXECUTION COMPLETED: {tool_nm}")
                        
                        # Get current messages from state
                        current_messages = state.get('messages', [])
                        if current_messages:
                            monitor_logger.info(f"📊 Current context: {len(current_messages)} messages")
                            
                            # Check if compression should trigger
                            should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(current_messages)
                            
                            # Context metrics logging
                            monitor_logger.info(f"🔍 POST_TOOL HOOK EVALUATION - Tool: {tool_nm}")
                            monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
                            monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
                            monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
                            
                            if should_compress:
                                monitor_logger.info(f"✅ POST_TOOL COMPRESSION TRIGGERED - Tool: {tool_nm}, Trigger: {trigger_type.value}")
                                
                                # Perform compression
                                compacted_messages, summary = enhanced_compact_integration.perform_automatic_compaction(
                                    current_messages, 
                                    {"hook_trigger": "POST_TOOL", "tool_name": tool_nm}
                                )
                                
                                # Update state with compressed messages
                                state['messages'] = compacted_messages
                                state['compression_applied'] = True
                                state['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                                
                                monitor_logger.info(f"🟡 POST_TOOL COMPRESSION COMPLETED")
                                monitor_logger.info(f"📉 Reduction: {getattr(summary, 'total_reduction_percentage', 0):.1f}%")
                                monitor_logger.info(f"💾 Messages: {len(current_messages)} → {len(compacted_messages)}")
                                
                            else:
                                monitor_logger.info(f"⏸️ POST_TOOL COMPRESSION SKIPPED - Context within limits")
                        else:
                            monitor_logger.warning(f"⚠️ No messages found in state for tool: {tool_nm}")
                            
                    except Exception as e:
                        logger.error(f"⚠️ POST_TOOL compression failed for tool {tool_nm}: {e}")
                        # Continue without compression
                else:
                    monitor_logger.warning(f"⚠️ No state access for tool {tool_nm} - compression check skipped")
                
                return result
            
            return wrapped_tool_with_state
        
        # Create the wrapped function
        wrapped_func = create_wrapped_tool_func(original_tool, original_func, func_type, tool_name)
        
        # Try to wrap the tool - use more defensive approach
        wrapped_successfully = False
        
        try:
            # For tools with invoke method (LangChain/MCP tools)
            if func_type == 'invoke':
                # Try to check if invoke is accessible
                invoke_method = getattr(orig_tool, 'invoke', None)
                if invoke_method:
                    # Create a new invoke method that includes compression hooks
                    async def new_invoke(input_data, config=None):
                        return await wrapped_func(input_data)
                    
                    # Try to replace the invoke method
                    try:
                        orig_tool.invoke = new_invoke
                        wrapped_tools.append(orig_tool)
                        logger.info(f"🔗 Tool wrapped in-place (invoke): {tool_name}")
                        wrapped_successfully = True
                        wrapped_count += 1
                    except Exception as replace_error:
                        logger.warning(f"⚠️ Cannot replace invoke method for {tool_name}: {replace_error}")
                
            elif func_type == 'func':
                # For tools with func attribute
                try:
                    def sync_wrapper(*args, **kwargs):
                        # Note: This is rarely used with modern tools
                        logger.warning(f"Sync wrapper called for {tool_name} - using asyncio.run")
                        return asyncio.run(wrapped_func(*args, **kwargs))
                    
                    orig_tool.func = sync_wrapper
                    wrapped_tools.append(orig_tool)
                    logger.info(f"🔗 Tool wrapped in-place (func-sync): {tool_name}")
                    wrapped_successfully = True
                    wrapped_count += 1
                except Exception as func_error:
                    logger.warning(f"⚠️ Cannot replace func for {tool_name}: {func_error}")
            
            # If wrapping failed, fall back to original tool
            if not wrapped_successfully:
                logger.warning(f"⚠️ Cannot wrap tool {tool_name}, using original (fallback)")
                wrapped_tools.append(orig_tool)
                
        except Exception as e:
            logger.error(f"❌ Failed to wrap tool {tool_name}: {e}")
            # Always fallback to original tool to avoid breaking the system
            wrapped_tools.append(orig_tool)
            logger.warning(f"⚠️ Using unwrapped tool: {tool_name} (exception fallback)")
    
    # Use the wrapped_count we tracked during processing
    total_count = len(wrapped_tools)
    
    logger.info(f"✅ {total_count} tools processed ({wrapped_count} successfully wrapped, {total_count - wrapped_count} using fallback)")
    print(f"🔗 Tool wrapping summary: {wrapped_count}/{total_count} tools wrapped with compression hooks")
    
    if wrapped_count > 0:
        print(f"✅ POST_TOOL compression hooks will fire from {wrapped_count} wrapped tools")
    else:
        print(f"⚠️ No tools could be wrapped - compression hooks may not fire from individual tools")
        print(f"💡 Consider implementing alternative compression trigger mechanisms")
    
    return wrapped_tools


def wrap_agent_with_compression_hooks(
    agent: Any,
    hook_manager: Optional[Any] = None,
    enhanced_compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> Any:
    """
    Wrap the agent with automatic POST_TOOL compression hooks.
    
    This now works by wrapping the LangGraph CompiledStateGraph methods that are actually called.
    
    Args:
        agent: The agent to wrap (CompiledStateGraph)
        hook_manager: Context hook manager (optional)
        enhanced_compact_integration: EnhancedCompactIntegration instance
        mcp_wrapper: MCP wrapper for context management
        
    Returns:
        Wrapped agent with compression hooks
    """
    if enhanced_compact_integration is None:
        logger.warning("No enhanced compact integration available, returning unwrapped agent")
        return agent
    
    # Get trigger config for this scope
    trigger_config = get_trigger_config() if CONFIG_AVAILABLE else {}
    
    # Check if this is a LangGraph CompiledStateGraph
    agent_type = type(agent).__name__
    logger.info(f"🔍 Agent type detected: {agent_type}")
    
    # For LangGraph CompiledStateGraph, we need to wrap different methods
    if hasattr(agent, 'stream') and hasattr(agent, 'invoke'):
        # Store original methods for LangGraph
        original_invoke = agent.invoke
        original_stream = agent.stream
        original_ainvoke = getattr(agent, 'ainvoke', None)
        original_astream = getattr(agent, 'astream', None)
        
        logger.info("🔧 Wrapping LangGraph CompiledStateGraph methods")
    else:
        # Fallback for other agent types
        original_invoke = getattr(agent, 'invoke', None)
        original_ainvoke = getattr(agent, 'ainvoke', None)
        logger.info("🔧 Wrapping standard agent methods")
    
    def wrapped_invoke(input_data, config=None, **kwargs):
        """Synchronous wrapper with POST_TOOL hook."""
        # Pre-LLM call token tracking
        input_messages = input_data.get('messages', []) if isinstance(input_data, dict) else []
        pre_token_count = len(str(input_messages)) // 4  # Rough estimate
        
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 LLM CALL STARTING 🚀")
        monitor_logger.info(f"📊 Context Window Tokens (est.): {pre_token_count:,}")
        monitor_logger.info(f"💬 Input Messages Count: {len(input_messages)}")
        
        # Execute original invoke
        result = original_invoke(input_data, config, **kwargs)
        
        # Post-LLM call analysis
        result_messages = result.get('messages', []) if isinstance(result, dict) else []
        post_token_count = len(str(result_messages)) // 4  # Rough estimate
        monitor_logger.info(f"🟢 LLM CALL COMPLETED ✅")
        monitor_logger.info(f"📈 Output Messages Count: {len(result_messages)}")
        monitor_logger.info(f"📊 Total Tokens After (est.): {post_token_count:,}")
        
        # Trigger POST_TOOL hook after execution
        if isinstance(result, dict) and 'messages' in result:
            try:
                # 🔍 LOG: POST_TOOL hook evaluation
                monitor_logger.info(f"🔍 POST_TOOL HOOK EVALUATION - Checking compression need after tool execution")
                
                # Check if compression needed
                should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
                # Context Management Status
                monitor_logger.info(f"🔴 CONTEXT MANAGEMENT CHECK 🧠")
                monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
                monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
                monitor_logger.info(f"🧹 MCP Cleaning Status: {'Active' if mcp_wrapper and hasattr(mcp_wrapper, 'context_manager') else 'None'}")
                monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
                
                # 🔍 LOG: Detailed POST_TOOL decision
                if should_compress:
                    monitor_logger.info(f"✅ POST_TOOL COMPRESSION WILL PROCEED - Trigger: {trigger_type.value}")
                else:
                    monitor_logger.info(f"⏸️ POST_TOOL COMPRESSION SKIPPED - Context within acceptable limits")
                
                if should_compress:
                    logger.info(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression using sync method
                    compacted_messages, summary = enhanced_compact_integration.perform_automatic_compaction(
                        result.get('messages', []), 
                        {"hook_trigger": "POST_TOOL"}
                    )
                    
                    # Update result with compressed context
                    result['messages'] = compacted_messages
                    result['compression_applied'] = True
                    result['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                    
                    # Compression Results
                    monitor_logger.info(f"🟡 COMPRESSION COMPLETED 🗜️")
                    monitor_logger.info(f"📉 Reduction: {getattr(summary, 'total_reduction_percentage', 0):.1f}%")
                    monitor_logger.info(f"📝 Summary Generated: {len(getattr(summary, 'summary_content', '')) if hasattr(summary, 'summary_content') else 0} chars")
                    monitor_logger.info(f"💾 Messages Reduced: {len(result_messages)} → {len(compacted_messages)}")
                    logger.info(f"✅ Context compressed: {getattr(summary, 'total_reduction_percentage', 0):.1f}% reduction")
                        
            except Exception as e:
                logger.error(f"⚠️ POST_TOOL compression failed: {e}")
                # Continue without compression
        
        return result
    
    async def wrapped_ainvoke(input_data, config=None, **kwargs):
        """Asynchronous wrapper with POST_TOOL hook."""
        # Pre-LLM call token tracking (async)
        input_messages = input_data.get('messages', []) if isinstance(input_data, dict) else []
        pre_token_count = len(str(input_messages)) // 4  # Rough estimate
        
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 ASYNC LLM CALL STARTING 🚀")
        monitor_logger.info(f"📊 Context Window Tokens (est.): {pre_token_count:,}")
        monitor_logger.info(f"💬 Input Messages Count: {len(input_messages)}")
        
        # Execute original ainvoke
        result = await original_ainvoke(input_data, config, **kwargs)
        
        # Post-LLM call analysis (async)
        result_messages = result.get('messages', []) if isinstance(result, dict) else []
        post_token_count = len(str(result_messages)) // 4  # Rough estimate
        monitor_logger.info(f"🟢 ASYNC LLM CALL COMPLETED ✅")
        monitor_logger.info(f"📈 Output Messages Count: {len(result_messages)}")
        monitor_logger.info(f"📊 Total Tokens After (est.): {post_token_count:,}")
        
        # Trigger POST_TOOL hook after execution
        if isinstance(result, dict) and 'messages' in result:
            try:
                # 🔍 LOG: ASYNC POST_TOOL hook evaluation
                monitor_logger.info(f"🔍 ASYNC POST_TOOL HOOK EVALUATION - Checking compression need after async tool execution")
                
                # Check if compression needed
                should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
                # 🔍 LOG: Async POST_TOOL decision
                if should_compress:
                    monitor_logger.info(f"✅ ASYNC POST_TOOL COMPRESSION WILL PROCEED - Trigger: {trigger_type.value}")
                else:
                    monitor_logger.info(f"⏸️ ASYNC POST_TOOL COMPRESSION SKIPPED - Context within acceptable limits")
                
                if should_compress:
                    logger.info(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression using sync method (no await needed)
                    compacted_messages, summary = enhanced_compact_integration.perform_automatic_compaction(
                        result.get('messages', []), 
                        {"hook_trigger": "POST_TOOL"}
                    )
                    
                    # Update result with compressed context
                    result['messages'] = compacted_messages
                    result['compression_applied'] = True
                    result['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                    
                    logger.info(f"✅ Context compressed: {getattr(summary, 'total_reduction_percentage', 0):.1f}% reduction")
                    
            except Exception as e:
                logger.error(f"⚠️ POST_TOOL compression failed: {e}")
                # Continue without compression
        
        return result

    def wrapped_stream(input_data, config=None, **kwargs):
        """Stream wrapper with POST_TOOL hook."""
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 LANGRAPH STREAM STARTING 🚀")
        
        # Execute original stream
        for event in original_stream(input_data, config, **kwargs):
            # Check if this is a final event with messages
            if hasattr(event, 'get') and 'messages' in event.get('output', {}):
                result_messages = event.get('output', {}).get('messages', [])
                
                # Trigger compression check after stream completes
                try:
                    monitor_logger.info(f"🔍 POST_STREAM HOOK EVALUATION - Checking compression need")
                    
                    # Check if compression needed
                    should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                        result_messages
                    )
                    
                    # Context Management Status
                    monitor_logger.info(f"🔴 CONTEXT MANAGEMENT CHECK 🧠")
                    monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
                    monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
                    monitor_logger.info(f"🧹 MCP Cleaning Status: {'Active' if mcp_wrapper and hasattr(mcp_wrapper, 'context_manager') else 'None'}")
                    monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
                    
                    if should_compress:
                        monitor_logger.info(f"✅ POST_STREAM COMPRESSION WILL PROCEED - Trigger: {trigger_type.value}")
                        
                        # Perform compression using sync method
                        compacted_messages, summary = enhanced_compact_integration.perform_automatic_compaction(
                            result_messages, 
                            {"hook_trigger": "POST_STREAM"}
                        )
                        
                        # Update event with compressed context (if possible)
                        if 'output' in event and 'messages' in event['output']:
                            event['output']['messages'] = compacted_messages
                            event['output']['compression_applied'] = True
                            event['output']['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                        
                        monitor_logger.info(f"🟡 STREAM COMPRESSION COMPLETED 🗜️")
                        monitor_logger.info(f"📉 Reduction: {getattr(summary, 'total_reduction_percentage', 0):.1f}%")
                    else:
                        monitor_logger.info(f"⏸️ POST_STREAM COMPRESSION SKIPPED - Context within acceptable limits")
                    
                except Exception as e:
                    logger.error(f"⚠️ POST_STREAM compression failed: {e}")
            
            yield event
        
        monitor_logger.info(f"🟢 LANGRAPH STREAM COMPLETED ✅")

    async def wrapped_astream(input_data, config=None, **kwargs):
        """Async stream wrapper with POST_TOOL hook."""
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 ASYNC LANGRAPH STREAM STARTING 🚀")
        
        # Execute original async stream
        async for event in original_astream(input_data, config, **kwargs):
            # Check if this is a final event with messages
            if hasattr(event, 'get') and 'messages' in event.get('output', {}):
                result_messages = event.get('output', {}).get('messages', [])
                
                # Trigger compression check after stream completes
                try:
                    monitor_logger.info(f"🔍 ASYNC POST_STREAM HOOK EVALUATION - Checking compression need")
                    
                    # Check if compression needed
                    should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                        result_messages
                    )
                    
                    if should_compress:
                        monitor_logger.info(f"✅ ASYNC POST_STREAM COMPRESSION TRIGGERED - Trigger: {trigger_type.value}")
                        
                        # Perform compression
                        compacted_messages, summary = enhanced_compact_integration.perform_automatic_compaction(
                            result_messages, 
                            {"hook_trigger": "ASYNC_POST_STREAM"}
                        )
                        
                        # Update event with compressed context
                        if 'output' in event and 'messages' in event['output']:
                            event['output']['messages'] = compacted_messages
                            event['output']['compression_applied'] = True
                        
                        monitor_logger.info(f"🟡 ASYNC STREAM COMPRESSION COMPLETED 🗜️")
                    
                except Exception as e:
                    logger.error(f"⚠️ ASYNC POST_STREAM compression failed: {e}")
            
            yield event
    
    # Replace methods with wrapped versions
    agent.invoke = wrapped_invoke
    if hasattr(agent, 'stream'):
        agent.stream = wrapped_stream
    if original_ainvoke:
        agent.ainvoke = wrapped_ainvoke
    if hasattr(agent, 'astream') and original_astream:
        agent.astream = wrapped_astream
    
    logger.info("✅ Agent wrapped with compression hooks (invoke + stream methods)")
    return agent


def get_compression_status(
    compact_integration: Optional[Any] = None,
    enhanced_compact_integration: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Get current compression system status.
    
    Args:
        compact_integration: CompactIntegration instance
        enhanced_compact_integration: EnhancedCompactIntegration instance
        
    Returns:
        Dictionary containing compression status
    """
    status = {
        "compact_available": COMPACT_AVAILABLE,
        "config_available": CONFIG_AVAILABLE,
        "compact_integration_active": compact_integration is not None,
        "enhanced_integration_active": enhanced_compact_integration is not None,
        "compression_history": [],
        "last_compression": None
    }
    
    if compact_integration and hasattr(compact_integration, 'compact_history'):
        status["compression_history"] = len(compact_integration.compact_history)
        if compact_integration.compact_history:
            last = compact_integration.compact_history[-1]
            status["last_compression"] = {
                "timestamp": last.timestamp,
                "reduction": getattr(last, 'total_reduction_percentage', 0)
            }
    
    return status


def print_compression_status(
    compact_integration: Optional[Any] = None,
    enhanced_compact_integration: Optional[Any] = None
):
    """
    Print compression system status for debugging.
    
    Args:
        compact_integration: CompactIntegration instance
        enhanced_compact_integration: EnhancedCompactIntegration instance
    """
    status = get_compression_status(compact_integration, enhanced_compact_integration)
    
    print("\n" + "="*60)
    print("CONTEXT COMPRESSION STATUS")
    print("="*60)
    print(f"Compact Integration Available: {'✅' if status['compact_available'] else '❌'}")
    print(f"Config Loader Available: {'✅' if status['config_available'] else '❌'}")
    print(f"Compact Integration Active: {'✅' if status['compact_integration_active'] else '❌'}")
    print(f"Enhanced Integration Active: {'✅' if status['enhanced_integration_active'] else '❌'}")
    
    if status['compression_history']:
        print(f"Compression History: {status['compression_history']} compressions")
        if status['last_compression']:
            print(f"Last Compression: {status['last_compression']['reduction']:.1f}% reduction")
    else:
        print("Compression History: None")
    
    print("="*60 + "\n")