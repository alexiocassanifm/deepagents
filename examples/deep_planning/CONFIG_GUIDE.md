# 🔧 Configuration Guide - Deep Planning Agent

## Overview

The Deep Planning Agent uses a **unified configuration system** that combines YAML files, Python dataclasses, and environment variables into a single source of truth. This guide explains how to configure and customize the system.

## Configuration Architecture

```
┌─────────────────────────────────────┐
│     Environment Variables           │  (Highest Priority)
├─────────────────────────────────────┤
│     context_config.yaml             │  (User Configuration)
├─────────────────────────────────────┤
│     unified_config.py               │  (Default Values)
└─────────────────────────────────────┘
```

## Quick Start

### Basic Usage

```python
from unified_config import get_config, print_config_summary

# Get complete configuration
config = get_config()

# Print summary
print_config_summary()

# Access specific sections
model_config = config.model
context_config = config.context
performance_config = config.performance
```

### Validate Configuration

```python
from unified_config import validate_config

validation = validate_config()
if validation["status"] == "invalid":
    print("Configuration errors:", validation["errors"])
```

## Configuration Sections

### 1. Model Configuration

Controls LLM model settings and compatibility.

```yaml
# In context_config.yaml (not directly, use env vars)
# Or set environment variables:
DEEPAGENTS_MODEL=claude-3.5-sonnet
MAX_OUTPUT_TOKENS=2500
MODEL_TIMEOUT=120
```

**Parameters:**
- `default_model`: Model to use (default: "claude-3.5-sonnet")
- `max_output_tokens`: Maximum tokens in output (default: 2500)
- `temperature`: Model temperature (default: 0.7)
- `model_timeout`: Timeout in seconds (default: 120.0)

### 2. Context Management

Controls when and how context compression triggers.

```yaml
context_management:
  # Core thresholds
  max_context_window: 200000        # Maximum context size in tokens
  trigger_threshold: 0.85           # Compress at 85% of max window
  mcp_noise_threshold: 0.6          # Trigger if 60% is MCP noise
  
  # LLM compression thresholds
  post_tool_threshold: 0.70         # Check after each tool call
  llm_compression_threshold: 0.75   # Prefer LLM compression above this
  force_llm_threshold: 0.90         # Always use LLM above this
  
  # Features
  cleaning_enabled: true            # Enable MCP result cleaning
  auto_compaction: true            # Enable automatic compression
```

**Threshold Guidelines:**
- **Aggressive compression**: Set thresholds to 0.60-0.70
- **Balanced**: Set thresholds to 0.70-0.80 (default)
- **Conservative**: Set thresholds to 0.80-0.90

### 3. Performance Settings

Controls system performance and optimization.

```yaml
performance:
  # Cache settings
  analysis_cache_duration: 60      # Cache analysis for 60 seconds
  max_cleaning_history: 100        # Keep last 100 operations
  
  # Timing
  auto_check_interval: 30          # Check context every 30 seconds
  compression_timeout: 30.0        # Timeout for compression
  
  # Tokenization
  use_precise_tokenization: true   # Use tiktoken for accuracy
  fallback_token_estimation: true  # Fallback if tiktoken unavailable
```

### 4. Logging & Monitoring

Controls logging verbosity and monitoring features.

```yaml
monitoring:
  # Logging
  log_level: "INFO"                # DEBUG, INFO, WARNING, ERROR
  
  # Metrics
  collect_metrics: true            # Collect performance metrics
  track_cleaning_performance: true # Track cleaning effectiveness
  export_statistics: true          # Export stats to file
  export_format: "json"            # json, yaml, or csv
```

### 5. MCP Integration

Configuration for Model Context Protocol tools.

```yaml
# Set via environment variables:
FAIRMIND_MCP_URL=https://your-mcp-server.com
FAIRMIND_MCP_TOKEN=your_token_here
MCP_TIMEOUT=30

# Or in YAML:
cleaning_strategies:
  ProjectListCleaner:
    max_projects_fallback: 3      # Keep only 3 projects if no target
    
  CodeSnippetCleaner:
    max_snippet_length: 5000       # Limit code snippets to 5000 chars
```

## Environment Variables

Environment variables override all other settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEEPAGENTS_MODEL` | LLM model to use | claude-3.5-sonnet |
| `MAX_OUTPUT_TOKENS` | Max output tokens | 2500 |
| `MODEL_TIMEOUT` | Model timeout (seconds) | 120 |
| `MAX_CONTEXT_WINDOW` | Max context size | 200000 |
| `TRIGGER_THRESHOLD` | Compression trigger | 0.85 |
| `COMPRESSION_TIMEOUT` | Compression timeout | 30 |
| `PYTHON_LOG_LEVEL` | Log level | INFO |
| `LOG_FILE` | Log file path | debug.log |
| `FAIRMIND_MCP_URL` | MCP server URL | None |
| `FAIRMIND_MCP_TOKEN` | MCP auth token | None |
| `RATE_LIMIT` | Requests per hour | 1000 |

## Common Configurations

### Development Mode

```yaml
# Maximum verbosity and frequent checks
monitoring:
  log_level: "DEBUG"
  
performance:
  auto_check_interval: 10
  
context_management:
  trigger_threshold: 0.95  # Avoid compression during dev
```

### Production Mode

```yaml
# Optimized for performance
monitoring:
  log_level: "WARNING"
  generate_reports: false
  
performance:
  auto_check_interval: 60
  use_precise_tokenization: true
  
context_management:
  trigger_threshold: 0.75
  auto_compaction: true
  deduplication_enabled: true
```

### High-Volume Mode

```yaml
# Aggressive compression for high token usage
context_management:
  max_context_window: 50000
  trigger_threshold: 0.60
  post_tool_threshold: 0.50
  force_llm_threshold: 0.80
  
deduplication:
  enabled: true
  similarity_threshold: 0.85
```

## Programmatic Configuration

### Loading Custom Configuration

```python
from unified_config import reload_config, get_config

# Load from specific YAML file
reload_config("custom_config.yaml")

# Get updated config
config = get_config()
```

### Runtime Updates

```python
from unified_config import set_config_value, get_config_value

# Update specific value
set_config_value("context.trigger_threshold", 0.70)

# Get specific value
threshold = get_config_value("context.trigger_threshold", default=0.85)
```

### Export Configuration

```python
from unified_config import export_config

# Export current config to file
export_config("current_config.yaml", format="yaml")
export_config("current_config.json", format="json")
```

## Validation Rules

The configuration system validates settings automatically:

### Required Relationships
- `post_tool_threshold` < `trigger_threshold`
- `llm_compression_threshold` < `force_llm_threshold`
- All thresholds must be between 0.0 and 1.0

### Performance Warnings
- `auto_check_interval` > 300: May reduce responsiveness
- `compression_timeout` < 10: May cause timeouts
- `max_output_tokens` > 4096: May exceed model limits

## Migration from Old Config

If migrating from the old config_loader system:

```python
# Old way
from config_loader import get_trigger_config
config = get_trigger_config()

# New way (backwards compatible)
from unified_config import get_trigger_config
config = get_trigger_config()

# Or use new unified approach
from unified_config import get_context_config
config = get_context_config()
```

## Troubleshooting

### Configuration Not Loading

```python
from unified_config import validate_config, print_config_summary

# Check validation
validation = validate_config()
print("Status:", validation["status"])
print("Errors:", validation["errors"])
print("Warnings:", validation["warnings"])

# Print full config
print_config_summary()
```

### Environment Variables Not Working

```bash
# Check if variables are set
echo $DEEPAGENTS_MODEL
echo $MAX_CONTEXT_WINDOW

# Export them properly
export DEEPAGENTS_MODEL="gpt-4"
export MAX_CONTEXT_WINDOW="100000"
```

### Performance Issues

If experiencing slow performance:

1. Check compression timeouts:
   ```yaml
   performance:
     compression_timeout: 60  # Increase if timeouts occur
   ```

2. Adjust thresholds:
   ```yaml
   context_management:
     trigger_threshold: 0.70  # Lower for more frequent compression
   ```

3. Enable caching:
   ```yaml
   performance:
     analysis_cache_duration: 120  # Cache for 2 minutes
   ```

## Best Practices

1. **Start with defaults** - The default configuration is well-balanced
2. **Use environment variables** for deployment-specific settings
3. **Validate after changes** - Always run validation after config changes
4. **Monitor metrics** - Enable metrics to understand system behavior
5. **Test threshold changes** - Test compression thresholds with real workloads

## Configuration Schema Reference

For complete schema details, see the dataclasses in `unified_config.py`:
- `ModelConfig`: Model and LLM settings
- `ContextManagementConfig`: Context and compression settings
- `PerformanceConfig`: Performance optimization settings
- `LoggingConfig`: Logging and monitoring settings
- `MCPConfig`: MCP integration settings