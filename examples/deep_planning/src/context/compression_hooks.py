"""
Compression Hooks for LangGraph Integration

This module provides compression hooks that can be used with LangGraph's
create_react_agent pre_model_hook parameter for automatic context compression.

Key Features:
- Clean integration with create_react_agent
- Preserves all original agent functionality  
- Automatic compression before LLM calls
- Compatible with existing CompactIntegration
"""

import logging
from typing import Dict, Any, Optional, Callable
from deepagents.state import DeepAgentState

# Setup logger for compression hooks
logger = logging.getLogger(__name__)

# Import dependencies if available
try:
    from .compact_integration import CompactIntegration
    COMPACT_AVAILABLE = True
except ImportError:
    COMPACT_AVAILABLE = False
    logger.warning("⚠️ Compact integration not available")


def create_compression_hook(
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None,
    model_name: Optional[str] = None
) -> Callable[[DeepAgentState], DeepAgentState]:
    """
    Create a compression hook for use with create_react_agent's pre_model_hook.
    
    This hook will be called before each LLM invocation and can compress
    the message history if needed, keeping the agent within token limits.
    
    Args:
        compact_integration: CompactIntegration instance for compression
        mcp_wrapper: MCP wrapper for additional context management  
        model_name: Model name for accurate LiteLLM token counting
        
    Returns:
        Hook function compatible with pre_model_hook parameter
    """
    
    # Create monitor logger for detailed compression tracking
    monitor_logger = logging.getLogger('mcp_context_tracker')
    
    def compression_hook(state: DeepAgentState) -> DeepAgentState:
        """
        Pre-model hook that compresses messages if needed.
        
        This function is called by LangGraph before each LLM call and has
        the opportunity to modify the state, including compressing messages.
        
        Args:
            state: Current LangGraph state
            
        Returns:
            Modified state with potentially compressed messages
        """
        # TIMING DEBUG: Log exact timestamp when hook is called
        import time
        hook_start_time = time.time()
        timestamp_str = time.strftime('%H:%M:%S', time.localtime(hook_start_time))
        monitor_logger.info(f"⏰ PRE_MODEL_HOOK CALLED AT: {timestamp_str}.{int((hook_start_time % 1) * 1000):03d}")
        
        # DEBUGGING: Log exactly what we received
        state_type = type(state).__name__
        monitor_logger.info(f"🔍 COMPRESSION HOOK CALLED - State type: {state_type}")
        
        # Early defensive check: if state is not the expected type, return unchanged
        if not isinstance(state, dict):
            if hasattr(state, '__class__'):
                monitor_logger.warning(f"⚠️ UNEXPECTED STATE TYPE: {state_type} - returning unchanged")
                monitor_logger.warning(f"   Available attributes: {[attr for attr in dir(state) if not attr.startswith('_')][:10]}")
            return {}
        
        if not compact_integration:
            # No compression available - return empty dict (no state changes)
            monitor_logger.debug("🔄 COMPRESSION HOOK PASSTHROUGH - No compact integration")
            return {}
        
        try:
            # Extract messages from state - handle both dict and object states
            messages = []
            
            monitor_logger.info(f"🔬 EXTRACTING MESSAGES - State type confirmed: {type(state).__name__}")
            
            # First, check if it's a dictionary (most common case)
            if isinstance(state, dict):
                monitor_logger.info(f"🔍 Processing dict state with keys: {list(state.keys())}")
                try:
                    messages = state.get("messages", [])
                    monitor_logger.info(f"✅ Dict access successful, found {len(messages)} messages")
                except Exception as e:
                    monitor_logger.error(f"❌ Dict access failed: {e}")
                    raise
                    
            elif hasattr(state, 'messages'):
                monitor_logger.info(f"🔍 Processing object state with messages attribute")
                try:
                    messages = state.messages
                    monitor_logger.info(f"✅ Attribute access successful, found {len(messages)} messages")
                except Exception as e:
                    monitor_logger.error(f"❌ Attribute access failed: {e}")
                    raise
                    
            else:
                # If state is neither dict nor has messages, try to find messages in other attributes
                # This handles edge cases and unexpected input types
                monitor_logger.warning(f"🔍 Unexpected state path: {type(state).__name__}")
                for attr_name in ['messages', 'message_list', 'conversation']:
                    if hasattr(state, attr_name):
                        messages = getattr(state, attr_name)
                        monitor_logger.info(f"🔍 Found messages in {attr_name}: {len(messages)} messages")
                        break
                
                # If no messages found and state is not a dict, return unchanged
                if not messages:
                    monitor_logger.warning(f"⚠️ Cannot extract messages from state type: {type(state).__name__}")
                    return state
            
            if not messages:
                monitor_logger.debug("🔄 COMPRESSION HOOK PASSTHROUGH - No messages in state")
                return state
            
            # 🔍 LOG: Pre-compression analysis
            monitor_logger.info(f"🔍 PRE-MODEL HOOK EVALUATION - Checking compression need")
            monitor_logger.info(f"📊 Current messages count: {len(messages)}")
            
            # Check if compression should be triggered using simplified context manager
            # Pass model_name to get accurate token counting with LiteLLM
            should_compress, trigger_type, metrics = compact_integration.should_trigger_compaction(
                messages, 
                trigger_type="standard",
                model_name=model_name,
                tools=None  # Tools will be handled by LiteLLM automatically
            )
            
            # Context metrics logging
            monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
            monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
            monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
            
            if should_compress:
                monitor_logger.info(f"✅ PRE-MODEL COMPRESSION TRIGGERED - Trigger: {trigger_type.value}")
                
                # Perform compression
                compacted_messages, summary = compact_integration.perform_automatic_compaction(
                    messages, 
                    {
                        "compression_trigger": "PRE_MODEL_HOOK",
                        "trigger_type": trigger_type.value
                    }
                )
                
                # Log compression metadata  
                compression_metadata = {
                    "compression_applied": True,
                    "compression_reduction": getattr(summary, 'total_reduction_percentage', 0),
                    "compression_trigger": "PRE_MODEL_HOOK",
                    "compression_type": trigger_type.value
                }
                monitor_logger.debug(f"📊 Compression metadata: {compression_metadata}")
                
                # Compression Results
                reduction_percentage = getattr(summary, 'total_reduction_percentage', 0)
                monitor_logger.info(f"🟡 PRE-MODEL COMPRESSION COMPLETED 🗜️")
                monitor_logger.info(f"📉 Reduction: {reduction_percentage:.1f}%")
                monitor_logger.info(f"📝 Summary Generated: {len(getattr(summary, 'summary_content', '')) if hasattr(summary, 'summary_content') else 0} chars")
                monitor_logger.info(f"💾 Messages Reduced: {len(messages)} → {len(compacted_messages)}")
                
                logger.info(f"✅ Context compressed via pre-model hook: {reduction_percentage:.1f}% reduction")
                
                # Return state update for LangGraph v2 format
                # This will permanently update the messages in the graph state
                monitor_logger.info(f"📦 Returning state update with {len(compacted_messages)} compressed messages")
                return {"messages": compacted_messages}
                
            else:
                # No compression needed
                monitor_logger.info(f"⏸️ PRE-MODEL COMPRESSION SKIPPED - Context within limits")
                
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            
            logger.error(f"⚠️ Compression hook failed: {error_type}: {error_msg}")
            monitor_logger.error(f"❌ PRE-MODEL HOOK ERROR: {error_type}: {error_msg}")
            monitor_logger.error(f"🔍 State type at error: {type(state).__name__}")
            monitor_logger.error(f"📋 Stack trace: {stack_trace}")
            
            # If this is the specific error we're debugging, add extra info
            if 'get' in error_msg and 'HumanMessage' in error_msg:
                monitor_logger.error("🚨 FOUND THE PROBLEMATIC ERROR!")
                monitor_logger.error(f"   State object: {state}")
                monitor_logger.error(f"   State type: {type(state)}")
                monitor_logger.error(f"   State dir: {dir(state)}")
            
            # Continue without compression to avoid breaking the workflow
            # Return empty dict for LangGraph v2 (no state changes)
            return {}
        
        # Default: no compression needed, return empty state update
        return {}
    
    logger.info("✅ Compression hook created for pre_model_hook integration")
    return compression_hook


def create_passthrough_hook() -> Callable[[DeepAgentState], DeepAgentState]:
    """
    Create a passthrough hook that does nothing.
    
    This can be used when compression is not available but the
    pre_model_hook parameter is still expected.
    
    Returns:
        Passthrough hook function
    """
    def passthrough_hook(state: DeepAgentState) -> DeepAgentState:
        """Passthrough hook that returns state unchanged."""
        return state
    
    return passthrough_hook


def get_hook_statistics(hook_function: Callable) -> Dict[str, Any]:
    """
    Get statistics from a compression hook if available.
    
    Args:
        hook_function: The hook function to get stats from
        
    Returns:
        Dictionary containing hook statistics or empty dict
    """
    try:
        # Try to access internal statistics if the hook has them
        if hasattr(hook_function, '__closure__') and hook_function.__closure__:
            for cell in hook_function.__closure__:
                if hasattr(cell.cell_contents, 'get_statistics'):
                    return cell.cell_contents.get_statistics()
        return {"hook_type": "compression", "statistics_available": False}
    except Exception:
        return {"hook_type": "unknown", "statistics_available": False}