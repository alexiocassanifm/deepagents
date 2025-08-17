"""
Unified Configuration System for Deep Planning Agent

This module provides a single source of truth for all configuration,
integrating YAML-based settings with Python configurations and environment variables.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

# Import existing configurations to integrate
from .prompt_config import PhaseType, PhaseConfig, ToolCategory, ValidationLevel

logger = logging.getLogger('unified_config')


# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================

@dataclass
class ModelConfig:
    """Model and LLM-specific configuration."""
    default_model: str = "claude-3.5-sonnet"
    max_output_tokens: int = 2500
    temperature: float = 0.1
    top_p: float = 0.95
    enable_compatibility_fixes: bool = True
    model_timeout: float = 120.0
    
    def __post_init__(self):
        """Override with environment variables if present."""
        self.default_model = os.getenv("DEEPAGENTS_MODEL", self.default_model)
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", str(self.max_output_tokens)))
        self.model_timeout = float(os.getenv("MODEL_TIMEOUT", str(self.model_timeout)))


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""
    analysis_cache_duration: int = 60
    max_cleaning_history: int = 100
    auto_check_interval: int = 30
    use_precise_tokenization: bool = True
    fallback_token_estimation: bool = True
    compression_timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Rate limiting
    requests_per_hour: int = 1000
    max_backoff_seconds: float = 300.0
    
    # Cache settings
    cache_ttl: int = 3600
    max_cache_size: int = 1000
    
    def __post_init__(self):
        """Override with environment variables if present."""
        self.compression_timeout = float(os.getenv("COMPRESSION_TIMEOUT", str(self.compression_timeout)))
        self.requests_per_hour = int(os.getenv("RATE_LIMIT", str(self.requests_per_hour)))


@dataclass
class ContextManagementConfig:
    """Context and compression management configuration."""
    max_context_window: int = 200000
    trigger_threshold: float = 0.85
    mcp_noise_threshold: float = 0.6
    post_tool_threshold: float = 0.70
    llm_compression_threshold: float = 0.75
    force_llm_threshold: float = 0.90
    
    # Cleaning settings
    cleaning_enabled: bool = True
    auto_compaction: bool = True
    preserve_essential_fields: bool = True
    
    # Deduplication
    deduplication_enabled: bool = True
    similarity_threshold: float = 0.90
    max_history_for_comparison: int = 50
    
    # MCP-specific limits
    max_projects_fallback: int = 3
    max_snippet_length: int = 5000
    max_stories: int = 0  # 0 = no limit
    max_repositories: int = 0  # 0 = no limit
    
    def __post_init__(self):
        """Override with environment variables if present."""
        self.max_context_window = int(os.getenv("MAX_CONTEXT_WINDOW", str(self.max_context_window)))
        self.trigger_threshold = float(os.getenv("TRIGGER_THRESHOLD", str(self.trigger_threshold)))


@dataclass
class LoggingConfig:
    """Logging and monitoring configuration."""
    log_level: str = "INFO"
    log_file: str = "debug.log"
    collect_metrics: bool = True
    track_cleaning_performance: bool = True
    generate_reports: bool = False
    export_statistics: bool = True
    export_format: str = "json"
    max_log_size: int = 1000
    
    def __post_init__(self):
        """Override with environment variables if present."""
        self.log_level = os.getenv("PYTHON_LOG_LEVEL", self.log_level).upper()
        self.log_file = os.getenv("LOG_FILE", self.log_file)


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) configuration."""
    mcp_url: Optional[str] = None
    mcp_token: Optional[str] = None
    enable_mcp_cleaning: bool = True
    mcp_timeout: float = 30.0
    
    def __post_init__(self):
        """Load from environment variables."""
        self.mcp_url = os.getenv("FAIRMIND_MCP_URL", self.mcp_url)
        self.mcp_token = os.getenv("FAIRMIND_MCP_TOKEN", self.mcp_token)
        self.mcp_timeout = float(os.getenv("MCP_TIMEOUT", str(self.mcp_timeout)))


@dataclass
class UnifiedConfig:
    """Complete unified configuration."""
    model: ModelConfig = field(default_factory=ModelConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    context: ContextManagementConfig = field(default_factory=ContextManagementConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    
    # Phase configurations (loaded from prompt_config)
    phases: Dict[PhaseType, PhaseConfig] = field(default_factory=dict)
    
    # Custom overrides from YAML
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration metadata
    config_version: str = "2.0"
    config_source: str = "unified"
    
    def merge_yaml_config(self, yaml_path: str):
        """Merge settings from YAML file."""
        if not os.path.exists(yaml_path):
            logger.warning(f"YAML config not found: {yaml_path}")
            return
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            # Merge context management settings
            if 'context_management' in yaml_data:
                ctx = yaml_data['context_management']
                self.context.max_context_window = ctx.get('max_context_window', self.context.max_context_window)
                self.context.trigger_threshold = ctx.get('trigger_threshold', self.context.trigger_threshold)
                self.context.mcp_noise_threshold = ctx.get('mcp_noise_threshold', self.context.mcp_noise_threshold)
                self.context.post_tool_threshold = ctx.get('post_tool_threshold', self.context.post_tool_threshold)
                self.context.llm_compression_threshold = ctx.get('llm_compression_threshold', self.context.llm_compression_threshold)
                self.context.force_llm_threshold = ctx.get('force_llm_threshold', self.context.force_llm_threshold)
                self.context.cleaning_enabled = ctx.get('cleaning_enabled', self.context.cleaning_enabled)
                self.context.auto_compaction = ctx.get('auto_compaction', self.context.auto_compaction)
            
            # Merge performance settings
            if 'performance' in yaml_data:
                perf = yaml_data['performance']
                self.performance.analysis_cache_duration = perf.get('analysis_cache_duration', self.performance.analysis_cache_duration)
                self.performance.max_cleaning_history = perf.get('max_cleaning_history', self.performance.max_cleaning_history)
                self.performance.auto_check_interval = perf.get('auto_check_interval', self.performance.auto_check_interval)
                self.performance.use_precise_tokenization = perf.get('use_precise_tokenization', self.performance.use_precise_tokenization)
            
            # Merge deduplication settings
            if 'deduplication' in yaml_data:
                dedup = yaml_data['deduplication']
                self.context.deduplication_enabled = dedup.get('enabled', self.context.deduplication_enabled)
                self.context.similarity_threshold = dedup.get('similarity_threshold', self.context.similarity_threshold)
                self.context.max_history_for_comparison = dedup.get('max_history_for_comparison', self.context.max_history_for_comparison)
            
            # Merge monitoring settings
            if 'monitoring' in yaml_data:
                mon = yaml_data['monitoring']
                self.logging.collect_metrics = mon.get('collect_metrics', self.logging.collect_metrics)
                self.logging.track_cleaning_performance = mon.get('track_cleaning_performance', self.logging.track_cleaning_performance)
                self.logging.log_level = mon.get('log_level', self.logging.log_level)
                self.logging.export_statistics = mon.get('export_statistics', self.logging.export_statistics)
            
            # Store cleaning strategies and other custom settings
            if 'cleaning_strategies' in yaml_data:
                self.custom_settings['cleaning_strategies'] = yaml_data['cleaning_strategies']
            
            # Store any tool-specific overrides
            if 'tool_overrides' in yaml_data:
                self.custom_settings['tool_overrides'] = yaml_data['tool_overrides']
            
            logger.info(f"✅ Merged configuration from {yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to merge YAML config: {e}")
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return validation report."""
        report = {
            "status": "valid",
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Validate context thresholds
        if not 0.0 < self.context.trigger_threshold < 1.0:
            report["errors"].append("trigger_threshold must be between 0.0 and 1.0")
        
        if not 0.0 < self.context.mcp_noise_threshold < 1.0:
            report["errors"].append("mcp_noise_threshold must be between 0.0 and 1.0")
        
        # Check threshold relationships
        if self.context.post_tool_threshold >= self.context.trigger_threshold:
            report["warnings"].append("post_tool_threshold >= trigger_threshold may cause frequent compressions")
        
        if self.context.llm_compression_threshold > self.context.force_llm_threshold:
            report["warnings"].append("llm_compression_threshold > force_llm_threshold is illogical")
        
        # Performance checks
        if self.performance.auto_check_interval > 300:
            report["warnings"].append("auto_check_interval > 5 minutes may reduce responsiveness")
        
        if self.performance.compression_timeout < 10:
            report["warnings"].append("compression_timeout < 10 seconds may cause timeouts")
        
        # Model checks
        if self.model.max_output_tokens > 4096:
            report["warnings"].append("max_output_tokens > 4096 may exceed model limits")
        
        # Recommendations
        if self.context.max_context_window > 100000:
            report["recommendations"].append("Consider using aggressive compression for large context windows")
        
        if not self.context.deduplication_enabled and self.context.max_context_window < 50000:
            report["recommendations"].append("Enable deduplication for better context efficiency")
        
        # Set final status
        if report["errors"]:
            report["status"] = "invalid"
        elif report["warnings"]:
            report["status"] = "valid_with_warnings"
        
        return report
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model": asdict(self.model),
            "performance": asdict(self.performance),
            "context": asdict(self.context),
            "logging": asdict(self.logging),
            "mcp": asdict(self.mcp),
            "custom_settings": self.custom_settings,
            "config_version": self.config_version,
            "config_source": self.config_source
        }
    
    def print_summary(self):
        """Print configuration summary."""
        print("\n" + "="*60)
        print("🔧 UNIFIED CONFIGURATION SUMMARY")
        print("="*60)
        
        print(f"\n📊 Configuration Version: {self.config_version}")
        print(f"📁 Configuration Source: {self.config_source}")
        
        print("\n🤖 MODEL SETTINGS:")
        print(f"   Model: {self.model.default_model}")
        print(f"   Max Tokens: {self.model.max_output_tokens}")
        print(f"   Timeout: {self.model.model_timeout}s")
        
        print("\n📏 CONTEXT MANAGEMENT:")
        print(f"   Max Window: {self.context.max_context_window:,} tokens")
        print(f"   Trigger: {self.context.trigger_threshold:.0%}")
        print(f"   MCP Noise: {self.context.mcp_noise_threshold:.0%}")
        print(f"   LLM Compression: {self.context.llm_compression_threshold:.0%}")
        
        print("\n⚡ PERFORMANCE:")
        print(f"   Cache Duration: {self.performance.analysis_cache_duration}s")
        print(f"   Auto Check: {self.performance.auto_check_interval}s")
        print(f"   Compression Timeout: {self.performance.compression_timeout}s")
        
        print("\n📝 LOGGING:")
        print(f"   Log Level: {self.logging.log_level}")
        print(f"   Log File: {self.logging.log_file}")
        print(f"   Metrics: {self.logging.collect_metrics}")
        
        if self.mcp.mcp_url:
            print("\n🔌 MCP:")
            print(f"   URL: {self.mcp.mcp_url}")
            print(f"   Cleaning: {self.mcp.enable_mcp_cleaning}")
        
        print("="*60)


# ============================================================================
# SINGLETON CONFIGURATION MANAGER
# ============================================================================

class ConfigurationManager:
    """Singleton manager for unified configuration."""
    
    _instance = None
    _config: Optional[UnifiedConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.reload()
    
    def reload(self, yaml_path: Optional[str] = None):
        """Reload configuration from all sources."""
        # Create base configuration with defaults
        self._config = UnifiedConfig()
        
        # Determine YAML path
        if yaml_path is None:
            possible_paths = [
                "context_config.yaml",
                os.path.join(os.path.dirname(__file__), "context_config.yaml"),
                "examples/deep_planning/context_config.yaml"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    yaml_path = path
                    break
        
        # Merge YAML configuration if found
        if yaml_path and os.path.exists(yaml_path):
            self._config.merge_yaml_config(yaml_path)
        
        # Load phase configurations from prompt_config
        try:
            from .prompt_config import PHASE_CONFIGS
            self._config.phases = PHASE_CONFIGS
        except ImportError:
            logger.warning("Could not import phase configurations")
        
        # Validate configuration
        validation = self._config.validate()
        if validation["status"] == "invalid":
            logger.error(f"Configuration validation failed: {validation['errors']}")
        elif validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(f"Configuration warning: {warning}")
        
        logger.info(f"✅ Configuration loaded and validated: {validation['status']}")
    
    @property
    def config(self) -> UnifiedConfig:
        """Get current configuration."""
        if self._config is None:
            self.reload()
        return self._config
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path."""
        parts = path.split('.')
        value = self.config.to_dict()
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, path: str, value: Any):
        """Set configuration value by dot-separated path."""
        parts = path.split('.')
        if not parts:
            return
        
        # Navigate to the parent
        obj = self.config
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return
        
        # Set the value
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
    
    def print_summary(self):
        """Print configuration summary."""
        self.config.print_summary()
    
    def validate(self) -> Dict[str, Any]:
        """Validate current configuration."""
        return self.config.validate()
    
    def export(self, path: str, format: str = "yaml"):
        """Export configuration to file."""
        config_dict = self.config.to_dict()
        
        if format == "yaml":
            with open(path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        elif format == "json":
            import json
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration exported to {path}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Create singleton instance
_manager = ConfigurationManager()

def get_config() -> UnifiedConfig:
    """Get unified configuration."""
    return _manager.config

def get_model_config() -> ModelConfig:
    """Get model configuration."""
    return _manager.config.model

def get_context_config() -> ContextManagementConfig:
    """Get context management configuration."""
    return _manager.config.context

def get_performance_config() -> PerformanceConfig:
    """Get performance configuration."""
    return _manager.config.performance

def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return _manager.config.logging

def get_mcp_config() -> MCPConfig:
    """Get MCP configuration."""
    return _manager.config.mcp

def get_config_value(path: str, default: Any = None) -> Any:
    """Get configuration value by path."""
    return _manager.get(path, default)

def set_config_value(path: str, value: Any):
    """Set configuration value by path."""
    _manager.set(path, value)

def reload_config(yaml_path: Optional[str] = None):
    """Reload configuration from sources."""
    _manager.reload(yaml_path)

def validate_config() -> Dict[str, Any]:
    """Validate current configuration."""
    return _manager.validate()

def print_config_summary():
    """Print configuration summary."""
    _manager.print_summary()

def export_config(path: str, format: str = "yaml"):
    """Export configuration to file."""
    _manager.export(path, format)


# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

# For compatibility with existing code that uses old config_loader
def get_trigger_config():
    """Backwards compatibility for old trigger config."""
    ctx = get_context_config()
    return {
        "max_context_window": ctx.max_context_window,
        "trigger_threshold": ctx.trigger_threshold,
        "mcp_noise_threshold": ctx.mcp_noise_threshold,
        "post_tool_threshold": ctx.post_tool_threshold,
        "llm_compression_threshold": ctx.llm_compression_threshold,
        "force_llm_threshold": ctx.force_llm_threshold,
        "deduplication_enabled": ctx.deduplication_enabled,
        "similarity_threshold": ctx.similarity_threshold
    }

def get_context_management_config():
    """Backwards compatibility for old context management config."""
    return get_context_config().__dict__

def get_full_config():
    """Backwards compatibility for old full config."""
    return get_config()