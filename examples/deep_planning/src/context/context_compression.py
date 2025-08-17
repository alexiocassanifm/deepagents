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
        return messages, None
    
    try:
        # Check if compaction should be triggered
        should_compact, trigger_type, metrics = compact_integration.should_trigger_compaction(messages)
        
        if should_compact:
            logger.info(f"📦 Context compaction triggered: {trigger_type.value}")
            logger.info(f"📊 Context metrics: {metrics.utilization_percentage:.1f}% utilization, {metrics.mcp_noise_percentage:.1f}% MCP noise")
            
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


def wrap_agent_with_compression_hooks(
    agent: Any,
    hook_manager: Optional[Any] = None,
    enhanced_compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> Any:
    """
    Wrap the agent with automatic POST_TOOL compression hooks.
    
    Intercepts agent execution to trigger compression after tool calls.
    
    Args:
        agent: The agent to wrap
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
    
    # Store original invoke methods
    original_invoke = agent.invoke
    original_ainvoke = agent.ainvoke if hasattr(agent, 'ainvoke') else None
    
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
                
                if should_compress:
                    logger.info(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression synchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        compacted_messages, summary = loop.run_until_complete(
                            enhanced_compact_integration.perform_automatic_compaction(
                                result.get('messages', []), 
                                {"hook_trigger": "POST_TOOL"}
                            )
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
                        
                    finally:
                        loop.close()
                        
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
                # Check if compression needed
                should_compress, trigger_type, metrics = await enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
                if should_compress:
                    logger.info(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression
                    compacted_messages, summary = await enhanced_compact_integration.perform_automatic_compaction(
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
    
    # Replace methods with wrapped versions
    agent.invoke = wrapped_invoke
    if original_ainvoke:
        agent.ainvoke = wrapped_ainvoke
    
    logger.info("✅ Agent wrapped with compression hooks")
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