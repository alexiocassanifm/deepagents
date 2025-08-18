"""
Simplified Context Manager for DeepAgents - Token Counting and Compression Triggers

This module implements a simplified context management system focused solely on:
- Accurate token counting using LiteLLM (supports all models: Claude, GPT, LLaMA, etc.)
- Simple threshold-based compression triggering
- Essential logging and metrics

All MCP detection, pattern matching, and cleaning strategies have been removed
for maximum simplicity, reliability, and performance.
"""

import json
import time
import logging
import yaml
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pathlib import Path

# Setup logger for context management
context_manager_logger = logging.getLogger('context_manager')

# LiteLLM for universal token counting
try:
    import litellm
    LITELLM_AVAILABLE = True
    context_manager_logger.info("✅ LiteLLM available for accurate token counting")
except ImportError:
    LITELLM_AVAILABLE = False
    context_manager_logger.warning("⚠️ LiteLLM not available, falling back to character estimation")

# Tiktoken for fallback token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    context_manager_logger.warning("⚠️ Tiktoken not available for fallback token counting")


class CompactTrigger(str, Enum):
    """Enumeration of compression trigger reasons."""
    CONTEXT_SIZE = "context_size"
    POST_TOOL = "post_tool"
    MANUAL = "manual"


@dataclass  
class CleaningResult:
    """Stub class for backward compatibility with existing modules."""
    original_size: int = 0
    cleaned_size: int = 0
    strategy_used: str = "none"
    status: str = "disabled"


@dataclass
class ContextMetrics:
    """Simplified context metrics focused on token usage."""
    tokens_used: int
    max_context_window: int
    utilization_percentage: float
    trigger_threshold: float
    post_tool_threshold: float
    
    def should_trigger_compact(self) -> bool:
        """Check if context should trigger compression based on main threshold."""
        return self.utilization_percentage >= self.trigger_threshold
        
    def should_trigger_post_tool(self) -> bool:
        """Check if context should trigger compression after tool calls."""
        return self.utilization_percentage >= self.post_tool_threshold
    
    def is_near_limit(self) -> bool:
        """Check if context is approaching the absolute limit."""
        return self.utilization_percentage >= 90.0


class ContextManager:
    """
    Simplified Context Manager for token-based compression triggering.
    
    Focuses exclusively on:
    - Accurate token counting with LiteLLM
    - Simple threshold comparisons
    - Essential metrics and logging
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with simplified configuration."""
        self.config = config if config else self._load_config()
        
        # Generate session ID for compatibility with CompactSummary
        from datetime import datetime
        self.session_id = f"simplified_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Cache for analysis results to avoid repeated token counting
        self._analysis_cache = {}
        self._last_analysis_time = 0
        
        context_manager_logger.info("🚀 Simplified ContextManager initialized")
        context_manager_logger.info(f"📏 Max context window: {self.config['max_context_window']:,} tokens")
        context_manager_logger.info(f"🎯 Trigger threshold: {self.config['trigger_threshold']:.1%}")
        context_manager_logger.info(f"🔧 Post-tool threshold: {self.config['post_tool_threshold']:.1%}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load simplified configuration from YAML file."""
        config_path = Path(__file__).parent.parent.parent / "config" / "context_config.yaml"
        
        try:
            with open(config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            # Extract essential context management settings
            context_config = config_data.get('context_management', {})
            performance_config = config_data.get('performance', {})
            
            return {
                'max_context_window': context_config.get('max_context_window', 50000),
                'trigger_threshold': context_config.get('trigger_threshold', 0.25) * 100,  # Convert to percentage
                'post_tool_threshold': context_config.get('post_tool_threshold', 0.20) * 100,  # Convert to percentage
                'auto_compaction': context_config.get('auto_compaction', True),
                'logging_enabled': context_config.get('logging_enabled', True),
                'use_litellm_tokenization': performance_config.get('use_litellm_tokenization', True),
                'fallback_token_estimation': performance_config.get('fallback_token_estimation', True),
                'analysis_cache_duration': performance_config.get('analysis_cache_duration', 60)
            }
        except Exception as e:
            context_manager_logger.warning(f"⚠️ Could not load config, using defaults: {e}")
            return {
                'max_context_window': 50000,
                'trigger_threshold': 25.0,
                'post_tool_threshold': 20.0,
                'auto_compaction': True,
                'logging_enabled': True,
                'use_litellm_tokenization': True,
                'fallback_token_estimation': True,
                'analysis_cache_duration': 60
            }
    
    def count_tokens(self, messages: List[Dict[str, Any]], model_name: str = None, tools: List = None) -> int:
        """
        Count tokens using LiteLLM for maximum accuracy across all models.
        
        Args:
            messages: List of LangChain message dictionaries
            model_name: Model name for LiteLLM (e.g., 'claude-sonnet-4-20250514')
            tools: Optional list of tools available to the model
            
        Returns:
            int: Accurate token count that will be sent to the LLM
        """
        if not messages:
            return 0
            
        try:
            # Use LiteLLM for accurate token counting if available and model provided
            if LITELLM_AVAILABLE and model_name and self.config.get('use_litellm_tokenization', True):
                context_manager_logger.debug(f"🎯 Using LiteLLM token counting for model: {model_name}")
                
                # Convert LangChain messages to format expected by LiteLLM
                litellm_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        # Handle different message formats
                        if 'content' in msg and 'type' in msg:
                            # LangChain format
                            role = 'user' if msg['type'] == 'human' else 'assistant' if msg['type'] == 'ai' else msg.get('role', 'user')
                            litellm_messages.append({'role': role, 'content': str(msg['content'])})
                        elif 'role' in msg and 'content' in msg:
                            # Direct API format
                            litellm_messages.append({'role': msg['role'], 'content': str(msg['content'])})
                
                if litellm_messages:
                    try:
                        token_count = litellm.token_counter(
                            model=model_name,
                            messages=litellm_messages,
                            tools=tools
                        )
                        context_manager_logger.debug(f"📊 LiteLLM raw token count: {token_count:,} tokens")
                        
                        # Apply correction factor for GLM-4.5 based on observed data
                        if 'glm-4.5' in model_name.lower() or 'z-ai' in model_name.lower():
                            # Observed: We count 15,445, OpenRouter counts 9,454 = 0.612 ratio
                            correction_factor = 0.65  # Conservative correction
                            corrected_count = int(token_count * correction_factor)
                            context_manager_logger.info(f"🎯 GLM-4.5 token correction: {token_count:,} → {corrected_count:,} (factor: {correction_factor})")
                            return corrected_count
                        else:
                            return token_count
                            
                    except Exception as e:
                        context_manager_logger.warning(f"⚠️ LiteLLM token counting failed for {model_name}: {e}")
                        # Fall through to tiktoken fallback
            
            # Fallback to tiktoken if available
            if TIKTOKEN_AVAILABLE:
                context_manager_logger.debug("🔄 Falling back to tiktoken estimation")
                encoding = tiktoken.encoding_for_model("gpt-4")  # Universal encoding
                total_chars = sum(len(json.dumps(msg, default=str)) for msg in messages)
                token_count = len(encoding.encode(json.dumps(messages, default=str)))
                context_manager_logger.debug(f"📊 Tiktoken estimated count: {token_count:,} tokens")
                return token_count
            
            # Final fallback: character-based estimation
            if self.config.get('fallback_token_estimation', True):
                context_manager_logger.debug("⚠️ Using character-based token estimation (chars/4)")
                total_chars = sum(len(json.dumps(msg, default=str)) for msg in messages)
                token_count = total_chars // 4  # Rough approximation
                context_manager_logger.debug(f"📊 Character-based estimated count: {token_count:,} tokens")
                return token_count
            
            context_manager_logger.error("❌ No token counting method available")
            return 0
            
        except Exception as e:
            context_manager_logger.error(f"❌ Token counting failed: {e}")
            # Emergency fallback
            if self.config.get('fallback_token_estimation', True):
                total_chars = sum(len(json.dumps(msg, default=str)) for msg in messages)
                return total_chars // 4
            return 0
    
    def analyze_context(self, messages: List[Dict[str, Any]], model_name: str = None, tools: List = None) -> ContextMetrics:
        """
        Analyze context and return simplified metrics based on token count.
        
        Args:
            messages: List of conversation messages
            model_name: Model name for accurate token counting
            tools: Optional list of available tools
            
        Returns:
            ContextMetrics: Simple metrics with token usage and trigger status
        """
        # Check cache first to avoid repeated analysis
        current_time = time.time()
        cache_key = hash(json.dumps(messages, default=str, sort_keys=True))
        
        if (cache_key in self._analysis_cache and 
            current_time - self._last_analysis_time < self.config.get('analysis_cache_duration', 60)):
            context_manager_logger.debug("📋 Using cached analysis results")
            return self._analysis_cache[cache_key]
        
        # Count tokens using LiteLLM or fallback methods
        total_tokens = self.count_tokens(messages, model_name, tools)
        
        # Calculate utilization percentage
        max_window = self.config["max_context_window"]
        utilization = (total_tokens / max_window * 100) if max_window > 0 else 0
        
        # Create metrics
        metrics = ContextMetrics(
            tokens_used=total_tokens,
            max_context_window=max_window,
            utilization_percentage=round(utilization, 1),
            trigger_threshold=self.config["trigger_threshold"],
            post_tool_threshold=self.config["post_tool_threshold"]
        )
        
        # Log analysis results
        if self.config.get('logging_enabled', True):
            context_manager_logger.info(f"📊 Context Analysis: {len(messages)} messages, "
                                       f"{total_tokens:,} tokens ({metrics.utilization_percentage:.1f}% utilization)")
            context_manager_logger.info(f"🎯 Compression needed: "
                                       f"{'YES' if metrics.should_trigger_compact() else 'NO'} "
                                       f"(trigger at {metrics.trigger_threshold:.1f}%)")
        
        # Cache results
        self._analysis_cache[cache_key] = metrics
        self._last_analysis_time = current_time
        
        # Limit cache size
        if len(self._analysis_cache) > 10:
            oldest_key = min(self._analysis_cache.keys())
            del self._analysis_cache[oldest_key]
        
        return metrics
    
    def should_trigger_compaction(self, messages: List[Dict[str, Any]], trigger_type: str = "standard", 
                                model_name: str = None, tools: List = None) -> Tuple[bool, CompactTrigger, ContextMetrics]:
        """
        Determine if compression should be triggered based on context analysis.
        
        Args:
            messages: List of conversation messages
            trigger_type: Type of trigger check ("standard" or "post_tool")
            model_name: Model name for token counting
            tools: Optional list of tools
            
        Returns:
            Tuple of (should_compress, trigger_reason, metrics)
        """
        metrics = self.analyze_context(messages, model_name, tools)
        
        if trigger_type == "post_tool":
            should_compress = metrics.should_trigger_post_tool()
            trigger_reason = CompactTrigger.POST_TOOL
        else:
            should_compress = metrics.should_trigger_compact()
            trigger_reason = CompactTrigger.CONTEXT_SIZE
        
        if should_compress and self.config.get('logging_enabled', True):
            context_manager_logger.info(f"🚨 COMPRESSION TRIGGERED: {trigger_reason.value} "
                                       f"({metrics.utilization_percentage:.1f}% > {metrics.trigger_threshold:.1f}%)")
        
        return should_compress, trigger_reason, metrics
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context manager state."""
        return {
            "config": {
                "max_context_window": self.config["max_context_window"],
                "trigger_threshold": f"{self.config['trigger_threshold']:.1f}%",
                "post_tool_threshold": f"{self.config['post_tool_threshold']:.1f}%",
                "litellm_available": LITELLM_AVAILABLE,
                "tiktoken_available": TIKTOKEN_AVAILABLE
            },
            "cache_stats": {
                "cached_analyses": len(self._analysis_cache),
                "last_analysis": datetime.fromtimestamp(self._last_analysis_time).isoformat() if self._last_analysis_time else None
            }
        }


def create_context_manager(config: Dict[str, Any] = None) -> ContextManager:
    """
    Factory function to create a simplified ContextManager instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        ContextManager: Configured context manager instance
    """
    return ContextManager(config)