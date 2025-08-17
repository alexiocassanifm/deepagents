"""
Optimized LLM Compressor - Integration of PerformanceOptimizer with LLMCompressor

This module bridges the gap between PerformanceOptimizer and LLMCompressor,
providing a seamless integration that adds performance optimization capabilities
to the semantic compression system.

Key Features:
1. Automatic rate limiting and backoff management
2. Intelligent caching of compression results  
3. Performance monitoring and auto-tuning
4. Graceful fallback to standard compression
5. Full compatibility with existing LLMCompressor interface
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from llm_compression import (
    LLMCompressor, 
    CompressionType, 
    CompressionStrategy,
    LLMCompressionResult
)
from performance_optimizer import (
    PerformanceOptimizer,
    RateLimitConfig,
    CacheStrategy,
    PerformanceMetrics
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for optimized compression."""
    enable_caching: bool = True
    cache_strategy: CacheStrategy = CacheStrategy.HYBRID
    enable_rate_limiting: bool = True
    enable_auto_tuning: bool = True
    enable_performance_monitoring: bool = True
    fallback_on_error: bool = True


class OptimizedLLMCompressor(LLMCompressor):
    """
    Enhanced LLM Compressor with integrated performance optimization.
    
    This class extends LLMCompressor to add:
    - Rate limiting and intelligent backoff
    - Result caching for identical compressions
    - Performance monitoring and metrics
    - Auto-tuning based on system performance
    - Graceful error handling and fallback
    """
    
    def __init__(self, 
                 model=None,
                 config: Dict[str, Any] = None,
                 optimization_config: OptimizationConfig = None,
                 rate_limit_config: RateLimitConfig = None):
        """
        Initialize optimized compressor.
        
        Args:
            model: Language model for compression
            config: Standard LLMCompressor configuration
            optimization_config: Performance optimization settings
            rate_limit_config: Rate limiting configuration
        """
        # Initialize base LLMCompressor
        super().__init__(model=model, config=config)
        
        # Set up optimization config
        self.opt_config = optimization_config or OptimizationConfig()
        
        # Initialize performance optimizer if optimization is enabled
        if self._should_use_optimizer():
            self.optimizer = PerformanceOptimizer(
                rate_limit_config=rate_limit_config or RateLimitConfig(),
                cache_strategy=self.opt_config.cache_strategy,
                enable_auto_tuning=self.opt_config.enable_auto_tuning
            )
            logger.info("Performance optimizer initialized for LLM compression")
        else:
            self.optimizer = None
            logger.info("Running without performance optimization")
    
    def _should_use_optimizer(self) -> bool:
        """Check if optimizer should be used."""
        return any([
            self.opt_config.enable_caching,
            self.opt_config.enable_rate_limiting,
            self.opt_config.enable_performance_monitoring
        ])
    
    async def compress_conversation(self,
                                   messages: List[Dict[str, Any]],
                                   compression_type: CompressionType = None,
                                   context: Dict[str, Any] = None) -> LLMCompressionResult:
        """
        Compress conversation with performance optimization.
        
        This method wraps the parent's compress_conversation with:
        - Caching to avoid redundant compressions
        - Rate limiting to prevent API throttling
        - Performance monitoring for metrics
        - Auto-tuning for optimal throughput
        
        Args:
            messages: Messages to compress
            compression_type: Type of compression to apply
            context: Additional context for compression
            
        Returns:
            Compression result with performance metrics
        """
        # If optimizer is not enabled, fall back to standard compression
        if not self.optimizer:
            return await super().compress_conversation(
                messages, compression_type, context
            )
        
        try:
            # Create compression config for caching
            compression_config = {
                "type": compression_type.value if compression_type else "auto",
                "strategy": self.config.strategy.value,
                "context": context
            }
            
            # Use optimizer's optimized_compress method
            result = await self.optimizer.optimized_compress(
                compressor_func=self._create_compression_wrapper(compression_type, context),
                messages=messages,
                config=compression_config
            )
            
            # Convert result to LLMCompressionResult if needed
            if isinstance(result, dict) and not isinstance(result, LLMCompressionResult):
                result = self._dict_to_compression_result(result)
            
            # Add performance metrics if monitoring is enabled
            if self.opt_config.enable_performance_monitoring:
                result = self._add_performance_metrics(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized compression failed: {e}")
            
            # Fallback to standard compression if configured
            if self.opt_config.fallback_on_error:
                logger.info("Falling back to standard compression")
                return await super().compress_conversation(
                    messages, compression_type, context
                )
            else:
                raise
    
    def _create_compression_wrapper(self, 
                                   compression_type: Optional[CompressionType],
                                   context: Optional[Dict[str, Any]]):
        """
        Create a wrapper function for the compression operation.
        
        This wrapper is needed because PerformanceOptimizer expects
        a callable that takes (messages, config) and returns a result.
        """
        async def wrapper(messages: List[Dict[str, Any]], 
                         config: Dict[str, Any]) -> Dict[str, Any]:
            # Call parent's compress_conversation
            result = await super(OptimizedLLMCompressor, self).compress_conversation(
                messages=messages,
                compression_type=compression_type,
                context=context
            )
            
            # Convert LLMCompressionResult to dict for optimizer
            if isinstance(result, LLMCompressionResult):
                return {
                    "success": result.success,
                    "compressed_messages": result.compressed_messages,
                    "tokens_before": result.tokens_before,
                    "tokens_after": result.tokens_after,
                    "reduction_percentage": result.reduction_percentage,
                    "compression_type": result.compression_type,
                    "processing_time": result.processing_time,
                    "error": result.error
                }
            return result
        
        return wrapper
    
    def _dict_to_compression_result(self, data: Dict[str, Any]) -> LLMCompressionResult:
        """Convert dictionary result back to LLMCompressionResult."""
        return LLMCompressionResult(
            success=data.get("success", False),
            compressed_messages=data.get("compressed_messages", []),
            tokens_before=data.get("tokens_before", 0),
            tokens_after=data.get("tokens_after", 0),
            reduction_percentage=data.get("reduction_percentage", 0.0),
            compression_type=data.get("compression_type", "unknown"),
            processing_time=data.get("processing_time", 0.0),
            error=data.get("error")
        )
    
    def _add_performance_metrics(self, result: LLMCompressionResult) -> LLMCompressionResult:
        """Add performance metrics to compression result."""
        if self.optimizer:
            metrics = self.optimizer.monitor.get_current_performance()
            
            # Add metrics to result metadata
            if not hasattr(result, 'metadata'):
                result.metadata = {}
            
            result.metadata['performance'] = {
                'avg_compression_time': metrics.avg_compression_time,
                'avg_token_throughput': metrics.avg_token_throughput,
                'cache_stats': self.optimizer.cache.get_stats(),
                'performance_level': self.optimizer.monitor.get_performance_level().value
            }
        
        return result
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary with performance metrics, cache stats, and system health
        """
        if not self.optimizer:
            return {"status": "optimizer_disabled"}
        
        return self.optimizer.get_comprehensive_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the optimized compression system.
        
        Returns:
            Health status with any identified issues
        """
        if not self.optimizer:
            return {
                "status": "healthy",
                "optimizer": "disabled",
                "message": "Running without optimization"
            }
        
        return await self.optimizer.health_check()
    
    def clear_cache(self):
        """Clear the compression cache."""
        if self.optimizer and self.optimizer.cache:
            self.optimizer.cache.memory_cache.clear()
            self.optimizer.cache.access_times.clear()
            logger.info("Compression cache cleared")
    
    def adjust_rate_limits(self, requests_per_minute: int = None, 
                          requests_per_hour: int = None):
        """
        Dynamically adjust rate limits.
        
        Args:
            requests_per_minute: New per-minute limit
            requests_per_hour: New per-hour limit
        """
        if self.optimizer and self.optimizer.rate_limiter:
            if requests_per_minute:
                self.optimizer.rate_limiter.config.requests_per_minute = requests_per_minute
            if requests_per_hour:
                self.optimizer.rate_limiter.config.requests_per_hour = requests_per_hour
            
            logger.info(f"Rate limits adjusted: {requests_per_minute}/min, {requests_per_hour}/hour")


def create_optimized_compressor(model=None,
                               enable_all_optimizations: bool = True,
                               **kwargs) -> OptimizedLLMCompressor:
    """
    Factory function to create an optimized compressor with sensible defaults.
    
    Args:
        model: Language model to use
        enable_all_optimizations: Enable all optimization features
        **kwargs: Additional configuration options
        
    Returns:
        Configured OptimizedLLMCompressor instance
    """
    if enable_all_optimizations:
        opt_config = OptimizationConfig(
            enable_caching=True,
            cache_strategy=CacheStrategy.HYBRID,
            enable_rate_limiting=True,
            enable_auto_tuning=True,
            enable_performance_monitoring=True,
            fallback_on_error=True
        )
    else:
        opt_config = OptimizationConfig()
    
    # Load rate limit config from unified config if available
    try:
        from unified_config import get_performance_config
        perf_config = get_performance_config()
        rate_config = RateLimitConfig(
            requests_per_minute=20,
            requests_per_hour=perf_config.requests_per_hour,
            backoff_multiplier=perf_config.backoff_factor,
            max_backoff_seconds=perf_config.max_backoff_seconds
        )
    except ImportError:
        rate_config = RateLimitConfig()
    
    return OptimizedLLMCompressor(
        model=model,
        optimization_config=opt_config,
        rate_limit_config=rate_config,
        **kwargs
    )