"""
Enhanced Token Tracking Hooks for Debugging OpenRouter Discrepancies

This module provides comprehensive token tracking and logging to identify
discrepancies between internal token counting and OpenRouter's reported usage.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Callable, List
from deepagents.state import DeepAgentState

# Setup logger for token tracking
logger = logging.getLogger(__name__)
token_tracker_logger = logging.getLogger('token_tracker')

try:
    import litellm
    from langchain_core.messages import BaseMessage
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("⚠️ LiteLLM not available for token counting")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("⚠️ Tiktoken not available for token counting")


def count_tokens_multiple_methods(
    messages: List[Dict[str, Any]], 
    model_name: str = "z-ai/glm-4.5"
) -> Dict[str, int]:
    """
    Count tokens using multiple methods to compare accuracy.
    
    Returns:
        Dictionary with token counts from different methods
    """
    results = {}
    
    # Method 1: LiteLLM token counting
    if LITELLM_AVAILABLE:
        try:
            # Convert messages to proper format for token counting
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append(msg)
                elif hasattr(msg, 'dict'):
                    formatted_messages.append(msg.dict())
                else:
                    # Try to extract content if it's a LangChain message
                    formatted_messages.append({
                        "role": getattr(msg, 'type', 'user'),
                        "content": str(msg.content) if hasattr(msg, 'content') else str(msg)
                    })
            
            results['litellm'] = litellm.token_counter(
                model=model_name,
                messages=formatted_messages
            )
        except Exception as e:
            logger.warning(f"LiteLLM token counting failed: {e}")
            results['litellm'] = -1
    
    # Method 2: Tiktoken (fallback)
    if TIKTOKEN_AVAILABLE:
        try:
            # Use GPT-4 encoding as fallback
            encoding = tiktoken.encoding_for_model("gpt-4")
            total_tokens = 0
            
            for msg in messages:
                content = ""
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                elif hasattr(msg, 'content'):
                    content = str(msg.content)
                else:
                    content = str(msg)
                    
                total_tokens += len(encoding.encode(content))
            
            results['tiktoken'] = total_tokens
        except Exception as e:
            logger.warning(f"Tiktoken counting failed: {e}")
            results['tiktoken'] = -1
    
    # Method 3: Character-based estimation
    try:
        total_chars = 0
        for msg in messages:
            content = ""
            if isinstance(msg, dict):
                content = msg.get('content', '')
            elif hasattr(msg, 'content'):
                content = str(msg.content)
            else:
                content = str(msg)
            total_chars += len(content)
        
        # Rough estimation: 4 characters per token
        results['char_estimate'] = total_chars // 4
    except Exception as e:
        logger.warning(f"Character estimation failed: {e}")
        results['char_estimate'] = -1
    
    return results


def log_message_details(messages: List[Any], prefix: str = "") -> None:
    """Log detailed information about messages for debugging."""
    token_tracker_logger.info(f"{prefix}📝 MESSAGE ANALYSIS:")
    token_tracker_logger.info(f"{prefix}  Total messages: {len(messages)}")
    
    for i, msg in enumerate(messages[:5]):  # Log first 5 messages
        try:
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content
                token_tracker_logger.info(f"{prefix}  Message {i+1}: {role} - {len(content)} chars - '{content_preview}'")
            elif hasattr(msg, 'content') and hasattr(msg, 'type'):
                content = str(msg.content)
                content_preview = content[:100] + "..." if len(content) > 100 else content
                token_tracker_logger.info(f"{prefix}  Message {i+1}: {msg.type} - {len(content)} chars - '{content_preview}'")
            else:
                str_msg = str(msg)
                preview = str_msg[:100] + "..." if len(str_msg) > 100 else str_msg
                token_tracker_logger.info(f"{prefix}  Message {i+1}: {type(msg).__name__} - '{preview}'")
        except Exception as e:
            token_tracker_logger.warning(f"{prefix}  Message {i+1}: Error analyzing - {e}")
    
    if len(messages) > 5:
        token_tracker_logger.info(f"{prefix}  ... and {len(messages) - 5} more messages")


def create_enhanced_token_tracking_hook(
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None,
    model_name: Optional[str] = "z-ai/glm-4.5"
) -> Callable[[DeepAgentState], DeepAgentState]:
    """
    Create an enhanced compression hook with comprehensive token tracking.
    
    This hook logs detailed information about:
    1. What we think we're sending (pre-compression)
    2. What we actually send after compression
    3. Token counts from multiple methods
    4. Full payload analysis
    
    Args:
        compact_integration: CompactIntegration instance for compression
        mcp_wrapper: MCP wrapper for additional context management  
        model_name: Model name for accurate token counting
        
    Returns:
        Hook function compatible with pre_model_hook parameter
    """
    
    # Create dedicated logger for comprehensive tracking
    monitor_logger = logging.getLogger('enhanced_token_tracker')
    
    def enhanced_compression_hook(state: DeepAgentState) -> DeepAgentState:
        """Enhanced pre-model hook with comprehensive token tracking."""
        
        # TIMING DEBUG: Log exact timestamp when hook is called
        hook_start_time = time.time()
        timestamp_str = time.strftime('%H:%M:%S', time.localtime(hook_start_time))
        monitor_logger.info(f"⏰ ENHANCED_HOOK CALLED AT: {timestamp_str}.{int((hook_start_time % 1) * 1000):03d}")
        
        # Log what we received
        state_type = type(state).__name__
        monitor_logger.info(f"🔍 ENHANCED TOKEN TRACKING - State type: {state_type}")
        
        # Extract messages
        messages = []
        if isinstance(state, dict):
            messages = state.get("messages", [])
            monitor_logger.info(f"📝 Found {len(messages)} messages in dict state")
            
            # Log all state keys for debugging
            monitor_logger.info(f"🔑 State keys: {list(state.keys())}")
        elif hasattr(state, 'messages'):
            messages = state.messages
            monitor_logger.info(f"📝 Found {len(messages)} messages in object state")
        
        if not messages:
            monitor_logger.info("⏸️ No messages to track, returning state unchanged")
            return state
        
        # === PRE-COMPRESSION ANALYSIS ===
        monitor_logger.info("🔬 PRE-COMPRESSION ANALYSIS")
        
        # Count tokens using multiple methods
        token_counts = count_tokens_multiple_methods(messages, model_name)
        monitor_logger.info(f"🧮 PRE-COMPRESSION TOKEN COUNTS:")
        for method, count in token_counts.items():
            if count > 0:
                monitor_logger.info(f"  {method}: {count:,} tokens")
            else:
                monitor_logger.info(f"  {method}: FAILED")
        
        # Log message details
        log_message_details(messages, "PRE-COMPRESSION ")
        
        # === COMPRESSION LOGIC ===
        compressed_state = state
        compression_applied = False
        
        if compact_integration:
            try:
                # Check if compression should be triggered
                should_compress, trigger_type, metrics = compact_integration.should_trigger_compaction(
                    messages, 
                    trigger_type="standard",
                    model_name=model_name,
                    tools=None
                )
                
                monitor_logger.info(f"🎯 COMPRESSION DECISION:")
                monitor_logger.info(f"  Should compress: {should_compress}")
                monitor_logger.info(f"  Trigger type: {trigger_type.value if should_compress else 'None'}")
                monitor_logger.info(f"  Context utilization: {metrics.utilization_percentage:.1f}%")
                monitor_logger.info(f"  Token count (internal): {metrics.tokens_used:,}")
                
                if should_compress:
                    # Apply compression
                    compressed_messages = compact_integration.compress_messages(
                        messages,
                        compression_ratio=0.5  # Compress to 50% of original
                    )
                    
                    # Update state with compressed messages
                    if isinstance(compressed_state, dict):
                        compressed_state = compressed_state.copy()
                        compressed_state["messages"] = compressed_messages
                    elif hasattr(compressed_state, 'messages'):
                        # Create new state object with compressed messages
                        compressed_state = type(compressed_state)(**{
                            **compressed_state.__dict__,
                            'messages': compressed_messages
                        })
                    
                    compression_applied = True
                    messages = compressed_messages  # Update for post-compression analysis
                    
            except Exception as e:
                monitor_logger.error(f"❌ COMPRESSION ERROR: {e}")
                # Continue with original state
        
        # === POST-COMPRESSION ANALYSIS ===
        if compression_applied:
            monitor_logger.info("🗜️ POST-COMPRESSION ANALYSIS")
            
            # Count tokens again after compression
            post_token_counts = count_tokens_multiple_methods(messages, model_name)
            monitor_logger.info(f"🧮 POST-COMPRESSION TOKEN COUNTS:")
            for method, count in post_token_counts.items():
                if count > 0:
                    pre_count = token_counts.get(method, 0)
                    reduction = ((pre_count - count) / pre_count * 100) if pre_count > 0 else 0
                    monitor_logger.info(f"  {method}: {count:,} tokens (reduced by {reduction:.1f}%)")
                else:
                    monitor_logger.info(f"  {method}: FAILED")
            
            # Log compressed message details
            log_message_details(messages, "POST-COMPRESSION ")
        
        # === FINAL PAYLOAD LOGGING ===
        monitor_logger.info("📤 FINAL PAYLOAD BEING SENT TO LLM:")
        monitor_logger.info(f"  Model: {model_name}")
        monitor_logger.info(f"  Message count: {len(messages)}")
        
        # Log the actual payload structure that will be sent
        try:
            # Create a sample of what the API call will look like
            api_payload_sample = {
                "model": model_name,
                "messages": messages[:3] if len(messages) > 3 else messages,  # First 3 messages as sample
                "temperature": 0.1,
                "max_tokens": 64000
            }
            
            payload_str = json.dumps(api_payload_sample, indent=2, default=str)
            # Truncate if too long
            if len(payload_str) > 2000:
                payload_str = payload_str[:2000] + "\n... (truncated)"
            
            monitor_logger.info(f"📋 SAMPLE API PAYLOAD:\n{payload_str}")
            
        except Exception as e:
            monitor_logger.warning(f"Could not serialize payload sample: {e}")
        
        # === SUMMARY ===
        best_token_count = next((count for count in [
            token_counts.get('litellm', 0),
            token_counts.get('tiktoken', 0),
            token_counts.get('char_estimate', 0)
        ] if count > 0), 0)
        
        monitor_logger.info(f"🎯 HOOK SUMMARY:")
        monitor_logger.info(f"  Compression applied: {compression_applied}")
        monitor_logger.info(f"  Final message count: {len(messages)}")
        monitor_logger.info(f"  Expected token count: {best_token_count:,}")
        monitor_logger.info(f"  Model: {model_name}")
        
        return compressed_state
    
    return enhanced_compression_hook


def create_passthrough_token_tracking_hook() -> Callable[[DeepAgentState], DeepAgentState]:
    """
    Create a passthrough hook that only tracks tokens without compression.
    Useful for debugging when you want to see token counts without interference.
    """
    
    monitor_logger = logging.getLogger('passthrough_token_tracker')
    
    def passthrough_hook(state: DeepAgentState) -> DeepAgentState:
        """Passthrough hook that only logs token information."""
        
        hook_start_time = time.time()
        timestamp_str = time.strftime('%H:%M:%S', time.localtime(hook_start_time))
        monitor_logger.info(f"⏰ PASSTHROUGH_HOOK CALLED AT: {timestamp_str}.{int((hook_start_time % 1) * 1000):03d}")
        
        # Extract messages
        messages = []
        if isinstance(state, dict):
            messages = state.get("messages", [])
        elif hasattr(state, 'messages'):
            messages = state.messages
        
        if messages:
            # Count tokens and log
            token_counts = count_tokens_multiple_methods(messages, "z-ai/glm-4.5")
            monitor_logger.info(f"📊 PASSTHROUGH TOKEN COUNTS (no compression):")
            for method, count in token_counts.items():
                if count > 0:
                    monitor_logger.info(f"  {method}: {count:,} tokens")
        
        # Always return state unchanged
        return state
    
    return passthrough_hook