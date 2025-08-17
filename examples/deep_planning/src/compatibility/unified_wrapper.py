"""
Unified Wrapper - Consolidated tool wrapping for MCP cleaning and compression hooks

This module combines the functionality of mcp_wrapper.py and context_hooks.py
into a single, streamlined wrapper system. It reduces complexity from 3 separate
wrapper layers to 1 unified interface.

Key Features:
- MCP tool result cleaning
- LLM compression hooks
- Single point of configuration
- Simplified API for tool wrapping
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from dataclasses import dataclass

# Import existing components
from ..context.context_manager import ContextManager
from ..integrations.mcp.mcp_cleaners import create_default_cleaning_strategies

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class UnifiedConfig:
    """Configuration for unified wrapper."""
    enable_mcp_cleaning: bool = True
    enable_compression_hooks: bool = True
    compression_threshold: float = 0.75
    mcp_noise_threshold: float = 0.60
    post_tool_threshold: float = 0.70


class UnifiedWrapper:
    """
    Unified wrapper that combines MCP cleaning and compression hooks.
    
    This simplifies the architecture by providing a single wrapper
    for all tool enhancement needs.
    """
    
    def __init__(
        self, 
        context_manager: ContextManager,
        llm_compressor: Optional[Any] = None,
        config: Optional[UnifiedConfig] = None
    ):
        """
        Initialize unified wrapper.
        
        Args:
            context_manager: Context manager for tracking
            llm_compressor: Optional LLM compressor for hooks
            config: Configuration options
        """
        self.context_manager = context_manager
        self.llm_compressor = llm_compressor
        self.config = config or UnifiedConfig()
        
        # Initialize cleaning strategies for MCP
        self.cleaning_strategies = create_default_cleaning_strategies()
        
        # Track wrapped tools
        self.wrapped_tools = {}
        self.stats = {
            "total_calls": 0,
            "cleaned_calls": 0,
            "compressed_calls": 0,
            "total_reduction_percentage": 0.0
        }
    
    def wrap_tool(self, tool: Any, tool_name: Optional[str] = None) -> Any:
        """
        Wrap a single tool with unified functionality.
        
        Args:
            tool: Tool to wrap
            tool_name: Optional name for the tool
            
        Returns:
            Wrapped tool with cleaning and compression
        """
        if not tool_name:
            tool_name = self._extract_tool_name(tool)
        
        # Check if already wrapped
        if tool_name in self.wrapped_tools:
            return self.wrapped_tools[tool_name]
        
        # Create wrapped version
        if callable(tool):
            wrapped = self._wrap_callable(tool, tool_name)
        elif hasattr(tool, 'run') or hasattr(tool, '__call__'):
            wrapped = self._wrap_tool_object(tool, tool_name)
        else:
            # Can't wrap, return original
            return tool
        
        # Store and return
        self.wrapped_tools[tool_name] = wrapped
        return wrapped
    
    def wrap_tools(self, tools: List[Any]) -> List[Any]:
        """
        Wrap multiple tools at once.
        
        Args:
            tools: List of tools to wrap
            
        Returns:
            List of wrapped tools
        """
        return [self.wrap_tool(tool) for tool in tools]
    
    def _wrap_callable(self, func: Callable, tool_name: str) -> Callable:
        """Wrap a callable tool."""
        
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            # Pre-execution tracking
            self.stats["total_calls"] += 1
            
            # Execute original function
            result = func(*args, **kwargs)
            
            # Apply MCP cleaning if enabled
            if self.config.enable_mcp_cleaning and self._is_mcp_tool(tool_name):
                result = self._clean_mcp_result(result, tool_name)
                self.stats["cleaned_calls"] += 1
            
            # Check for compression trigger if enabled
            if self.config.enable_compression_hooks and self.llm_compressor:
                if self._should_compress():
                    self._trigger_compression()
                    self.stats["compressed_calls"] += 1
            
            return result
        
        return wrapped_func
    
    def _wrap_tool_object(self, tool: Any, tool_name: str) -> Any:
        """Wrap a tool object with run or __call__ method."""
        
        class WrappedTool:
            def __init__(self, original_tool, wrapper):
                self.original = original_tool
                self.wrapper = wrapper
                self.name = tool_name
                
                # Copy attributes from original
                for attr in dir(original_tool):
                    if not attr.startswith('_') and attr not in ['run', '__call__']:
                        try:
                            setattr(self, attr, getattr(original_tool, attr))
                        except:
                            pass
            
            def run(self, *args, **kwargs):
                # Use wrapper's callable wrapping logic
                wrapped_method = self.wrapper._wrap_callable(
                    self.original.run if hasattr(self.original, 'run') else self.original.__call__,
                    self.name
                )
                return wrapped_method(*args, **kwargs)
            
            def __call__(self, *args, **kwargs):
                return self.run(*args, **kwargs)
        
        return WrappedTool(tool, self)
    
    def _extract_tool_name(self, tool: Any) -> str:
        """Extract tool name from various tool types."""
        if hasattr(tool, 'name'):
            return tool.name
        elif hasattr(tool, '__name__'):
            return tool.__name__
        else:
            return str(tool)
    
    def _is_mcp_tool(self, tool_name: str) -> bool:
        """Check if tool is an MCP tool."""
        mcp_prefixes = [
            'General_', 'Studio_', 'Code_',
            'mcp__', 'fairmind__'
        ]
        return any(tool_name.startswith(prefix) for prefix in mcp_prefixes)
    
    def _clean_mcp_result(self, result: Any, tool_name: str) -> Any:
        """Apply MCP cleaning to tool result."""
        try:
            # Find appropriate cleaning strategy
            for strategy in self.cleaning_strategies:
                if strategy.can_clean(tool_name, result):
                    cleaning_result = strategy.clean(result)
                    if cleaning_result.success:
                        logger.debug(f"Cleaned {tool_name}: {cleaning_result.reduction_percentage:.1f}% reduction")
                        return cleaning_result.cleaned_data
            
            # No strategy found, return original
            return result
            
        except Exception as e:
            logger.warning(f"Failed to clean {tool_name}: {e}")
            return result
    
    def _should_compress(self) -> bool:
        """Check if compression should be triggered."""
        if not self.context_manager:
            return False
        
        try:
            metrics = self.context_manager.get_current_metrics()
            return (
                metrics.utilization_percentage > self.config.compression_threshold or
                metrics.mcp_noise_percentage > self.config.mcp_noise_threshold
            )
        except:
            return False
    
    def _trigger_compression(self):
        """Trigger LLM compression."""
        if self.llm_compressor:
            logger.info("Triggering LLM compression via unified wrapper")
            # Compression logic would be called here
            # This is a placeholder for the actual compression trigger
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get wrapper statistics."""
        return {
            **self.stats,
            "wrapped_tools_count": len(self.wrapped_tools),
            "wrapped_tool_names": list(self.wrapped_tools.keys())
        }


def create_unified_wrapper(
    context_manager: ContextManager,
    llm_compressor: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> UnifiedWrapper:
    """
    Factory function to create a unified wrapper.
    
    Args:
        context_manager: Context manager for tracking
        llm_compressor: Optional LLM compressor
        config: Optional configuration dict
        
    Returns:
        Configured UnifiedWrapper instance
    """
    if config:
        wrapper_config = UnifiedConfig(**config)
    else:
        wrapper_config = UnifiedConfig()
    
    return UnifiedWrapper(
        context_manager=context_manager,
        llm_compressor=llm_compressor,
        config=wrapper_config
    )


def wrap_tools_unified(
    tools: List[Any],
    context_manager: ContextManager,
    llm_compressor: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> tuple[List[Any], UnifiedWrapper]:
    """
    Convenience function to wrap a list of tools.
    
    Args:
        tools: Tools to wrap
        context_manager: Context manager
        llm_compressor: Optional LLM compressor
        config: Optional configuration
        
    Returns:
        Tuple of (wrapped_tools, wrapper_instance)
    """
    wrapper = create_unified_wrapper(context_manager, llm_compressor, config)
    wrapped_tools = wrapper.wrap_tools(tools)
    
    logger.info(f"Unified wrapper created: {len(wrapped_tools)} tools wrapped")
    return wrapped_tools, wrapper