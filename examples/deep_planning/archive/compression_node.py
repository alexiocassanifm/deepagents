"""
Compression Node for LangGraph Integration

This module provides a dedicated compression node that can be inserted into
the LangGraph workflow to automatically compress context before LLM calls.
This approach works better than tool wrapping because it intercepts the flow
at the graph level, ensuring compression happens regardless of tool execution.

Key Features:
- Preventive compression before LLM calls
- Token threshold monitoring
- Integration with existing CompactIntegration
- Compatible with all tool types (MCP, demo, built-in)
"""

import logging
from typing import Dict, Any, Optional, List
from deepagents.state import DeepAgentState

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


class CompressionNode:
    """
    A LangGraph node that performs automatic context compression when needed.
    
    This node can be inserted into any LangGraph workflow to ensure that
    context size stays within model limits by compressing messages before
    they reach the LLM.
    """
    
    def __init__(
        self,
        compact_integration: Optional[Any] = None,
        mcp_wrapper: Optional[Any] = None,
        node_name: str = "compress_context"
    ):
        """
        Initialize the compression node.
        
        Args:
            compact_integration: CompactIntegration instance for compression
            mcp_wrapper: MCP wrapper for additional context management
            node_name: Name for this node (for logging)
        """
        self.compact_integration = compact_integration
        self.mcp_wrapper = mcp_wrapper
        self.node_name = node_name
        self.monitor_logger = logging.getLogger('mcp_context_tracker')
        
        # Load configuration
        self.trigger_config = get_trigger_config() if CONFIG_AVAILABLE else {}
        
        # Track compression statistics
        self.compression_count = 0
        self.total_reductions = []
        
        logger.info(f"✅ Compression node '{node_name}' initialized")
        if compact_integration:
            logger.info("🧠 Compact integration available")
        else:
            logger.warning("⚠️ No compact integration - compression disabled")
    
    async def __call__(self, state: DeepAgentState) -> Dict[str, Any]:
        """
        Process the state and compress if needed.
        
        This is the main entry point called by LangGraph when this node
        is executed in the workflow.
        
        Args:
            state: Current LangGraph state containing messages and other data
            
        Returns:
            Dictionary with updated state (empty if no compression needed)
        """
        return await self.process_compression(state)
    
    async def process_compression(self, state: DeepAgentState) -> Dict[str, Any]:
        """
        Check if compression is needed and perform it if necessary.
        
        Args:
            state: Current state from LangGraph
            
        Returns:
            Updated state dictionary or empty dict if no changes
        """
        if not self.compact_integration:
            # No compression available - pass through
            self.monitor_logger.debug(f"🔄 COMPRESSION NODE PASSTHROUGH - No compact integration")
            return {}
        
        try:
            # Extract messages from state - handle both dict and LangGraph state objects
            messages = []
            if hasattr(state, 'get') and callable(state.get):
                # Dictionary-like state
                messages = state.get("messages", [])
            elif hasattr(state, 'messages'):
                # Attribute-based state
                messages = state.messages
            elif isinstance(state, dict):
                # Direct dictionary access
                messages = state.get("messages", [])
            else:
                # Unknown state format - try to find messages
                for attr_name in ['messages', 'message_list', 'conversation']:
                    if hasattr(state, attr_name):
                        messages = getattr(state, attr_name)
                        break
            
            if not messages:
                self.monitor_logger.debug(f"🔄 COMPRESSION NODE PASSTHROUGH - No messages in state")
                return {}
            
            # 🔍 LOG: Pre-compression analysis
            self.monitor_logger.info(f"🔍 COMPRESSION NODE EVALUATION - Node: {self.node_name}")
            self.monitor_logger.info(f"📊 Current messages count: {len(messages)}")
            
            # Check if compression should be triggered
            should_compress, trigger_type, metrics = self.compact_integration.should_trigger_compaction(messages)
            
            # Context metrics logging
            self.monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
            self.monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
            self.monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
            
            if should_compress:
                self.monitor_logger.info(f"✅ COMPRESSION TRIGGERED - Node: {self.node_name}, Trigger: {trigger_type.value}")
                
                # Perform compression
                compacted_messages, summary = self.compact_integration.perform_automatic_compaction(
                    messages, 
                    {
                        "compression_trigger": "PREVENTIVE_NODE",
                        "node_name": self.node_name,
                        "trigger_type": trigger_type.value
                    }
                )
                
                # Update compression statistics
                self.compression_count += 1
                reduction_percentage = getattr(summary, 'total_reduction_percentage', 0)
                self.total_reductions.append(reduction_percentage)
                
                # Compression Results
                self.monitor_logger.info(f"🟡 COMPRESSION COMPLETED 🗜️")
                self.monitor_logger.info(f"📉 Reduction: {reduction_percentage:.1f}%")
                self.monitor_logger.info(f"📝 Summary Generated: {len(getattr(summary, 'summary_content', '')) if hasattr(summary, 'summary_content') else 0} chars")
                self.monitor_logger.info(f"💾 Messages Reduced: {len(messages)} → {len(compacted_messages)}")
                
                logger.info(f"✅ Context compressed in node: {reduction_percentage:.1f}% reduction")
                
                # Return updated state with compressed messages
                return {
                    "messages": compacted_messages,
                    "compression_applied": True,
                    "compression_reduction": reduction_percentage,
                    "compression_node": self.node_name,
                    "compression_count": self.compression_count
                }
                
            else:
                # No compression needed
                self.monitor_logger.info(f"⏸️ COMPRESSION SKIPPED - Context within limits")
                return {}
                
        except Exception as e:
            logger.error(f"⚠️ Compression node failed: {e}")
            self.monitor_logger.error(f"❌ COMPRESSION NODE ERROR: {e}")
            # Continue without compression to avoid breaking the workflow
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compression statistics for this node.
        
        Returns:
            Dictionary containing compression metrics
        """
        return {
            "node_name": self.node_name,
            "compression_count": self.compression_count,
            "total_reductions": self.total_reductions,
            "average_reduction": sum(self.total_reductions) / len(self.total_reductions) if self.total_reductions else 0,
            "compact_integration_active": self.compact_integration is not None,
            "mcp_wrapper_active": self.mcp_wrapper is not None
        }
    
    def reset_statistics(self):
        """Reset compression statistics."""
        self.compression_count = 0
        self.total_reductions = []
        logger.info(f"📊 Reset statistics for compression node: {self.node_name}")


def create_compression_node(
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None,
    node_name: str = "compress_context"
) -> CompressionNode:
    """
    Factory function to create a compression node.
    
    Args:
        compact_integration: CompactIntegration instance for compression
        mcp_wrapper: MCP wrapper for additional context management
        node_name: Name for this node
        
    Returns:
        Configured CompressionNode instance
    """
    return CompressionNode(
        compact_integration=compact_integration,
        mcp_wrapper=mcp_wrapper,
        node_name=node_name
    )


# Async wrapper function for direct use in LangGraph
async def compress_context_node(
    state: DeepAgentState,
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Direct async function for use as a LangGraph node.
    
    This is a convenience function that creates a temporary CompressionNode
    and processes the state. For better performance, use the CompressionNode
    class directly.
    
    Args:
        state: Current LangGraph state
        compact_integration: CompactIntegration instance
        mcp_wrapper: MCP wrapper instance
        
    Returns:
        Updated state dictionary
    """
    node = CompressionNode(compact_integration, mcp_wrapper, "compress_context_direct")
    return await node.process_compression(state)