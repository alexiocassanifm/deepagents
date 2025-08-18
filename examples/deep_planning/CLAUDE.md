# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the `deep_planning` example from the `deepagents` package - a sophisticated AI agent that implements a structured 4-phase development methodology for complex software development tasks. It transforms vague user requests into implementation-ready plans through autonomous investigation, targeted clarification, structured planning, and task generation.

## Development Commands

### Installation and Setup
```bash
# Install this project as a package in development mode
pip install -e .

# This automatically installs all dependencies including:
# - deepagents (parent package)
# - langgraph-cli[inmem] (LangGraph development server)
# - langchain-mcp-adapters (MCP integration)

# Alternative: Install dependencies manually
# pip install -r requirements.txt
# cd ../.. && pip install -e .
```

### Running the Agent
```bash
# Standalone execution
python src/core/agent_core.py

# LangGraph development server (hot reload)
langgraph dev

# LangGraph cloud deployment
langgraph up
```

### Testing Compatibility
```bash
# Test model compatibility
python tests/test_compatibility.py

# Test prompt optimization
python tests/test_optimization.py
```

## Architecture Overview

### 🏗️ Core Components

1. **Main Agent (`src/core/agent_core.py`)** *(Simplified Architecture)*
   - Entry point that creates optimized deep planning agent with MCP integration
   - Modularized from original 1847-line file to 602 lines
   - Uses `src/core/agent_factory.py` (150 lines) instead of complex 497-line factory
   - Integrates with `src/compatibility/unified_wrapper.py` for consolidated tool wrapping

2. **Optimized Prompt System (`src/config/optimized_prompts.py`)**
   - 91% reduction in main prompt length (650 → 60 lines)
   - Modular prompt templates with dynamic context injection
   - Single responsibility per agent design

3. **Compatibility System (`src/compatibility/model_compatibility.py`, `src/compatibility/tool_compatibility.py`)**
   - Automatic model detection and compatibility fix application
   - Registry of known problematic models (GPT-3.5, LLaMA-based)
   - JSON string → Python list conversion for tool parameters

4. **Phase Configuration (`src/config/prompt_config.py`)**
   - Structured phase definitions with validation criteria
   - Tool categorization and filtering per phase
   - Human interaction points management

5. **Template System (`src/config/prompt_templates.py`)**
   - Dynamic context injection into prompt templates
   - Phase-specific todo generation
   - Context-aware prompt adaptation

6. **Simplified Context Management System (`src/context/context_manager.py`)**
   - Universal token counting with LiteLLM (supports all models: Claude, GPT, LLaMA, etc.)
   - Simple threshold-based compression triggering
   - Real-time accurate token metrics and monitoring
   - Compatible with Claude Code compact-implementation specifications

### 🔄 4-Phase Deep Planning Methodology

1. **🔍 Silent Investigation**
   - Autonomous exploration using MCP tools
   - No user interaction required
   - Outputs: `investigation_findings.md`

2. **💬 Targeted Discussion** 
   - 5-7 focused clarification questions
   - Requirements gathering and validation
   - Outputs: `clarification_questions.md`, `user_responses.md`

3. **📋 Structured Planning**
   - 8-section implementation plan creation
   - Human approval required via `review_plan` tool
   - Outputs: `implementation_plan.md`

4. **⚡ Task Generation**
   - Implementation tasks breakdown
   - Focus chain creation for tracking
   - Outputs: `implementation_tasks.md`, `focus_chain.md`

### 🔧 Model Compatibility System

**Automatic Detection**
- Detects model from environment variables (`DEEPAGENTS_MODEL`, `ANTHROPIC_MODEL`, etc.)
- Applies compatibility fixes based on model registry

**Supported Models**
- Claude 3.5 Sonnet: Excellent (no fixes needed)
- GPT-4 Turbo: Minimal fixes
- GPT-3.5 Turbo: Moderate fixes (JSON string conversion)
- LLaMA-based: Extensive fixes

**Fix Types Applied**
- JSON string → Python list conversion for tool parameters
- Parameter validation and normalization
- Tool call formatting corrections

### 🛠️ MCP Integration

**Fairmind MCP Tools**
- Project discovery: `General_list_projects()`
- Code analysis: `Code_find_relevant_code_snippets()`
- Requirements management: `Studio_list_user_stories()`
- Documentation search: `General_rag_retrieve_documents()`

**Fallback System**
- Demo tools when MCP server unavailable
- Mock data for development and testing

**Universal Token Counting & Management**
- LiteLLM-powered accurate token counting for all supported models
- Simple threshold-based compression without pattern matching
- Real-time context utilization monitoring with precise metrics
- No false positives from pattern matching or noise detection

## Package Structure

This project is structured as a proper Python package with the following benefits:

### 📦 **Package Configuration**
- **`pyproject.toml`**: Modern Python package configuration with metadata and dependencies
- **`setup.py`**: Backwards compatibility for older tools
- **Development Mode**: Install with `pip install -e .` for immediate code changes
- **Dependency Management**: Automatic installation of all required packages

### 🔧 **Import System**
- **Module Imports**: Uses `src.core.agent_core:agent` format for LangGraph
- **Relative Imports**: Clean internal imports with `from ..module import`
- **Package Discovery**: Automatic Python package detection and loading
- **IDE Support**: Better autocomplete, type checking, and debugging

### ✅ **Advantages**
- **LangGraph Compatibility**: No import errors when loading agents
- **Python Standards**: Follows official Python packaging guidelines
- **Distribution Ready**: Can be easily shared or deployed
- **Testing Support**: Proper test discovery and execution
- **Development Workflow**: Seamless development with immediate updates

## Configuration

### Environment Variables
```bash
# Model selection
DEEPAGENTS_MODEL="claude-3.5-sonnet"  # Default

# MCP server configuration (optional)
FAIRMIND_MCP_URL="https://project-context.mindstream.fairmind.ai/mcp/mcp/"
FAIRMIND_MCP_TOKEN="your_token_here"
```

### Context Management Configuration (`context_config.yaml`)
- Simple token-based compression triggers and thresholds
- LiteLLM configuration for universal model support
- Essential logging and monitoring settings
- Performance optimization with accurate token counting

### LangGraph Configuration (`langgraph.json`)
- Graph definition: `src.core.agent_core:agent` (module import format)
- Dependencies: Local directory (`.`)
- Environment: `.env` file
- Package-based imports: Uses Python module imports instead of file paths

## Key Design Patterns

### 🎯 Orchestration vs Execution
- Main agent orchestrates, sub-agents execute
- Clear separation of responsibilities
- Phase transition validation

### 📋 Todo Management Integration  
- Todo tracking across all phases
- Context-aware todo generation
- Progress visibility and validation

### 🔄 Dynamic Context Injection
- Template variables for phase-specific prompts
- State-aware context generation
- Tool categorization per phase

### 🛡️ Compatibility First Design
- Model-agnostic tool calling
- Automatic fix application
- Graceful fallback handling

### 🧹 Simplified Context Management
- Universal token counting with LiteLLM for all models
- Simple threshold-based compression triggering
- Real-time context window monitoring with accurate metrics
- Compatible with Claude Code compact-implementation standards

## File Structure and Responsibilities

### 📁 Directory Structure
```
# Package Configuration
pyproject.toml            # Modern Python package configuration
setup.py                  # Backwards compatibility setup
langgraph.json            # LangGraph deployment with module imports
requirements.txt          # Legacy dependency file (optional)

src/
├── core/                 # Core agent functionality
│   ├── agent_core.py     # Main agent creation and orchestration (602 lines)
│   ├── agent_factory.py  # Simplified agent factory (150 lines)
│   └── phase_orchestration.py # Phase management and transitions
│
├── config/               # Configuration and prompts
│   ├── prompt_config.py  # Phase definitions and validation rules
│   ├── prompt_templates.py # Template injection and context generation
│   ├── optimized_prompts.py # Modular prompt templates
│   ├── config_loader.py  # Configuration loading utilities
│   └── unified_config.py # Unified configuration management
│
├── compatibility/        # Model and tool compatibility
│   ├── model_compatibility.py # Model detection and compatibility profiles
│   ├── tool_compatibility.py  # Tool fixing and wrapping logic
│   ├── compatibility_layer.py # Main compatibility interface
│   └── unified_wrapper.py     # Consolidated tool wrapping
│
├── context/              # Context management
│   ├── context_manager.py     # Simplified token counting and compression triggers
│   ├── context_compression.py # Context compression utilities
│   ├── compression_hooks.py   # LangGraph pre_model_hook integration
│   ├── compact_integration.py # Auto-compaction integration
│   └── llm_compression.py     # LLM-based compression strategies
│
├── integrations/mcp/     # MCP integration
│   ├── mcp_integration.py # Main MCP tool initialization
│   ├── mcp_wrapper.py     # Transparent MCP tool wrapper
│   └── mcp_cleaners.py    # Specialized MCP cleaning strategies
│
└── utils/                # Utilities and helpers
    ├── debug_tools.py         # Debugging utilities
    ├── performance_optimizer.py # Performance optimization
    ├── validation_chains.py    # Validation utilities
    └── logging_setup.py        # Logging configuration

config/                   # Configuration files
└── context_config.yaml   # Context management configuration

tests/                    # Test suite
├── test_compatibility.py    # Model compatibility testing
├── test_optimization.py     # Prompt optimization validation
├── test_context_manager.py  # Context management tests
└── [other test files]       # Additional test modules

docs/                     # Documentation
├── CLAUDE.md            # This file - project documentation
├── README.md            # Project overview and setup
├── CONFIG_GUIDE.md      # Configuration guide
└── [other docs]         # Additional documentation

examples/                 # Usage examples
└── integration_example.py # Example integration usage

scripts/                  # Utility scripts
├── monitor_logs.sh      # Log monitoring script
└── watch_my_logs.sh     # Real-time log watching

logs/                     # Log files (gitignored)
└── context_detailed.log # Detailed context logs

archive/                  # Legacy/deprecated files
└── [backup files]       # Archived implementations
```

## Development Practices

### Adding New Models
1. Create `ModelCompatibilityProfile` in `src/compatibility/model_compatibility.py`
2. Define regex patterns for model detection
3. Specify required fixes and compatibility level
4. Register in `default_registry`

### Extending Phases
1. Add new phase to `PhaseType` enum in `src/config/prompt_config.py`
2. Create agent configuration in `src/config/optimized_prompts.py`
3. Define validation criteria and tool requirements
4. Update orchestrator prompt template

### Adding MCP Tools
1. Extend tool filters in `get_tools_for_phase()`
2. Update tool categories in `ToolCategory` enum
3. Add to relevant phase configurations
4. Create cleaning strategy in `src/integrations/mcp/mcp_cleaners.py` if needed
5. Add tool configuration to `config/context_config.yaml`

### Customizing Context Management
1. Adjust token thresholds in `config/context_config.yaml`
2. Modify `trigger_threshold` for general compression (default: 25%)
3. Adjust `post_tool_threshold` for post-tool compression (default: 20%)
4. Configure `max_context_window` for your model's limits
5. Test with realistic scenarios to validate thresholds

## Troubleshooting

### MCP Connection Issues
- Agent falls back to demo tools automatically
- Check `FAIRMIND_MCP_TOKEN` environment variable
- Verify MCP server URL accessibility

### Tool Compatibility Errors
- Enable DEBUG logging: `setup_compatibility_logging(level="DEBUG")`
- Check model detection in console output
- Verify fix application in logs

### Prompt Template Issues
- Validate template variables in `src/config/prompt_templates.py`
- Check context injection with `inject_dynamic_context()`
- Review phase-specific configurations

### Context Management Issues
- Check `config/context_config.yaml` for correct threshold configuration
- Monitor token usage with simplified context metrics
- Verify LiteLLM is installed for accurate token counting
- Test with different models to ensure universal compatibility
- Enable detailed logging: `setup_compatibility_logging(level="DEBUG")`

### Package and Import Issues
- **Relative Import Errors**: Make sure package is installed with `pip install -e .`
- **Module Not Found**: Verify package installation and `src/` directory structure
- **LangGraph Import Errors**: Check `langgraph.json` uses module format `src.core.agent_core:agent`
- **Development Changes**: Reinstall package if structure changes: `pip install -e . --force-reinstall`
- **IDE Issues**: Restart IDE after package installation for proper recognition

## Context Management Features

### 🎯 Universal Token Counting
- **LiteLLM Integration**: Accurate token counting for all supported models (Claude, GPT, LLaMA, etc.)
- **Triple Fallback System**: LiteLLM → Tiktoken → Character estimation for maximum compatibility
- **Real-time Metrics**: Precise token usage and context window utilization
- **Model Agnostic**: Works seamlessly with any model supported by LiteLLM

### 📊 Simplified Monitoring
- Real-time token usage tracking with LiteLLM precision
- Simple threshold-based compression triggering
- Automatic compression when context limits approached
- Clean metrics without false positives from pattern matching
- Integration with Claude Code compact-implementation specs

### ⚙️ Streamlined Configuration
- YAML-based configuration with essential settings only
- Simple thresholds: trigger_threshold and post_tool_threshold
- Performance optimization with caching and fallback systems
- Compatible with existing Claude Code workflows
- Focus on what matters: token limits and compression

### 🔧 Usage Example
```python
# Import the main agent (after installing package with pip install -e .)
from src.core.agent_core import agent

# Basic setup with simplified context management
from src.context.context_manager import ContextManager

# Create context manager with LiteLLM token counting
context_manager = ContextManager()

# Monitor token usage for any model
messages = [{"role": "user", "content": "Your task"}]
metrics = context_manager.analyze_context(
    messages, 
    model_name="claude-sonnet-4-20250514"  # Works with any LiteLLM supported model
)

print(f"Token usage: {metrics.tokens_used:,} tokens ({metrics.utilization_percentage:.1f}%)")
print(f"Compression needed: {'Yes' if metrics.should_trigger_compact() else 'No'}")

# Use the main agent - compression happens automatically via pre_model_hook
initial_state = {"messages": messages}
result = agent.invoke(initial_state)
```