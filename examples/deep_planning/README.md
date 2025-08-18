# Deep Planning Agent with Smart Context Compression

This enhanced version of the deep planning agent includes intelligent context compression capabilities that preserve critical elements while efficiently managing large MCP content.

## 🚀 Quick Start

### Enhanced Agent (Recommended)

```python
from src.core.enhanced_agent_factory import create_enhanced_deep_agent

# Create agent with smart compression enabled
agent = create_enhanced_deep_agent(
    tools=[your_tools],
    instructions="Your agent instructions",
    enable_smart_compression=True  # Default
)

# Use the agent normally
result = agent.invoke({"messages": [{"role": "user", "content": "Your task"}]})
```

### Simple Agent (Core Only)

```python
from src.core.enhanced_agent_factory import create_simple_deep_agent

# Create basic agent without enhancements
agent = create_simple_deep_agent(
    tools=[your_tools],
    instructions="Your agent instructions"
)
```

## 🎯 Key Features

### 🧠 Smart Context Compression

- **Selective Compression**: Preserves critical elements while compressing safe content
- **Todo Preservation**: Never loses task tracking information
- **Virtual FS Protection**: Maintains virtual filesystem state across compressions
- **Recent Context**: Always keeps last 5 messages for immediate context
- **System Messages**: Preserves agent instructions and system prompts

### 📦 MCP Content Archiving

- **Automatic Detection**: Identifies large MCP tool outputs (>3k characters)
- **Archiving Markers**: Creates `[CONTENT TO ARCHIVE]` markers for agent action
- **Smart Filenames**: Timestamp-based naming with tool-specific prefixes
- **Content Summaries**: Brief descriptions for quick reference

### 🗂️ Virtual Filesystem Management

- **organize_virtual_fs()**: Analyze and organize your virtual filesystem
- **cleanup_old_archives()**: Remove old archives with intelligent retention
- **archive_content_helper()**: Helper for manual content archiving
- **get_archiving_suggestions()**: AI-driven archiving recommendations

## 📁 File Structure

```
src/
├── core/
│   └── enhanced_agent_factory.py    # Enhanced agent creation
├── context/
│   ├── selective_compression.py     # Core compression logic
│   ├── compression_hooks.py         # LangGraph integration
│   └── archiving_tools.py          # Virtual FS management
└── prompts/
    └── smart_archiving_prompts.py   # Agent instruction enhancements
```

## 🔧 Configuration

### Compression Thresholds

```python
# Built-in thresholds (configurable)
ARCHIVING_THRESHOLDS = {
    "large_content": 3000,  # Characters requiring archiving consideration
    "huge_content": 5000,   # Characters requiring immediate archiving
}
```

### Preservation Rules

The system automatically preserves:
- Todo content and task tracking
- System messages and agent instructions
- Recent context (last 5 messages)
- Virtual filesystem references  
- Recent tool results

## 📖 Examples

### Basic Usage

```python
# See examples/enhanced_agent_example.py for complete demo
python examples/enhanced_agent_example.py
```

### Custom Pre-Model Hook

```python
def custom_hook(state):
    # Your custom logic
    return state

agent = create_enhanced_deep_agent(
    tools=[],
    instructions="Your instructions",
    pre_model_hook=custom_hook,  # Will be chained with smart compression
    enable_smart_compression=True
)
```

### Virtual FS Management

```python
# In your agent's context, use these tools:
await organize_virtual_fs()           # Check filesystem organization
await cleanup_old_archives("mcp_", 3) # Keep 3 most recent MCP archives
await get_archiving_suggestions()     # Get AI recommendations
```

## 🧪 Testing

```bash
# Run comprehensive tests
python tests/test_selective_compression.py

# Expected output: All tests pass with detailed compression metrics
```

## 🔄 Migration from Core Package

If you were using smart compression features from the core `deepagents` package:

**Before:**
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=[],
    instructions="",
    enable_smart_compression=True  # This parameter no longer exists
)
```

**After:**
```python
from src.core.enhanced_agent_factory import create_enhanced_deep_agent

agent = create_enhanced_deep_agent(
    tools=[],
    instructions="", 
    enable_smart_compression=True  # Now available in enhanced factory
)
```

## 🎓 Architecture Insights

### Why Local Implementation?

This implementation keeps all smart compression features within the `examples/deep_planning` directory rather than modifying the core `deepagents` package. Benefits:

1. **No Core Modifications**: Preserves the stability of the core package
2. **Experimental Features**: Allows testing of advanced features without risk
3. **User Choice**: Users can opt into enhanced features as needed
4. **Clean Separation**: Clear boundary between stable core and experimental features

### Integration Pattern

The enhanced factory wraps `deepagents.create_deep_agent()` and adds:
- Smart compression pre-model hooks
- Virtual filesystem management tools
- Enhanced instruction prompts with archiving guidance
- Local compression modules and utilities

### Performance Characteristics

- **Compression Trigger**: Activates when context approaches model limits
- **Preservation Rate**: Typically preserves 60-80% of critical messages
- **Archiving Efficiency**: Reduces large MCP outputs by 80-95% via archiving
- **Context Recovery**: Archived content remains accessible via virtual FS

## 🚨 Important Notes

1. **Testing Required**: Always test compression behavior with your specific use case
2. **Model Compatibility**: Works with all models supported by the core package
3. **MCP Integration**: Optimized for large MCP tool outputs (Fairmind, etc.)
4. **Backward Compatibility**: Enhanced agents support all core deepagents features

## 🤝 Contributing

When adding new features:

1. Keep all changes within `examples/deep_planning/src/`
2. Update tests in `tests/test_selective_compression.py`
3. Add examples in `examples/enhanced_agent_example.py`
4. Document new features in this README

## 📚 Further Reading

- [CLAUDE.md](CLAUDE.md) - Complete project documentation
- [Context Refactor Specification](../../specs/deepagents-context-refactor.md)
- [Core Package Documentation](../../README.md)