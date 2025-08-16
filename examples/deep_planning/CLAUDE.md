# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the `deep_planning` example from the `deepagents` package - a sophisticated AI agent that implements a structured 4-phase development methodology for complex software development tasks. It transforms vague user requests into implementation-ready plans through autonomous investigation, targeted clarification, structured planning, and task generation.

## Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install the parent deepagents package in development mode
cd ../.. && pip install -e .
```

### Running the Agent
```bash
# Standalone execution
python deep_planning_agent.py

# LangGraph development server (hot reload)
langgraph dev

# LangGraph cloud deployment
langgraph up
```

### Testing Compatibility
```bash
# Test model compatibility
python test_compatibility.py

# Test prompt optimization
python test_optimization.py
```

## Architecture Overview

### 🏗️ Core Components

1. **Main Agent (`deep_planning_agent.py`)**
   - Entry point that creates optimized deep planning agent with MCP integration
   - Implements compatibility fixes for different LLM models
   - Configures 4-phase orchestration workflow

2. **Optimized Prompt System (`optimized_prompts.py`)**
   - 91% reduction in main prompt length (650 → 60 lines)
   - Modular prompt templates with dynamic context injection
   - Single responsibility per agent design

3. **Compatibility System (`model_compatibility.py`, `tool_compatibility.py`)**
   - Automatic model detection and compatibility fix application
   - Registry of known problematic models (GPT-3.5, LLaMA-based)
   - JSON string → Python list conversion for tool parameters

4. **Phase Configuration (`prompt_config.py`)**
   - Structured phase definitions with validation criteria
   - Tool categorization and filtering per phase
   - Human interaction points management

5. **Template System (`prompt_templates.py`)**
   - Dynamic context injection into prompt templates
   - Phase-specific todo generation
   - Context-aware prompt adaptation

6. **Context Management System (`context_manager.py`, `mcp_cleaners.py`)**
   - Intelligent MCP tool result cleaning with 60-80% noise reduction
   - Automatic context compaction when token limits approached
   - Compatible with Claude Code compact-implementation specifications
   - Real-time context metrics and automatic optimization

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

**Context Cleaning & Noise Reduction**
- Automatic filtering of redundant MCP tool metadata
- Smart preservation of essential data (project_id, names, code text)
- Configurable cleaning strategies per tool type
- Real-time context utilization monitoring

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
- MCP tool cleaning strategies and thresholds
- Auto-compaction triggers and summary templates
- Performance optimization settings
- Tool-specific overrides and custom rules

### LangGraph Configuration (`langgraph.json`)
- Graph definition: `deep_planning_agent.py:agent`
- Dependencies: Local directory (`.`)
- Environment: `.env` file

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

### 🧹 Intelligent Context Management
- Automatic MCP tool result cleaning with configurable strategies
- Real-time context window monitoring and optimization
- Compatible with Claude Code compact-implementation standards
- Preserves essential information while removing noise

## File Structure and Responsibilities

### Core Files
- `deep_planning_agent.py` - Main agent creation and initialization
- `optimized_prompts.py` - Modular prompt templates
- `model_compatibility.py` - Model detection and compatibility profiles
- `tool_compatibility.py` - Tool fixing and wrapping logic

### Configuration Files  
- `prompt_config.py` - Phase definitions and validation rules
- `prompt_templates.py` - Template injection and context generation
- `context_config.yaml` - Context management and cleaning configuration
- `requirements.txt` - Package dependencies
- `langgraph.json` - LangGraph deployment configuration

### Context Management Files
- `context_manager.py` - Core context management and metrics tracking
- `mcp_cleaners.py` - Specialized cleaning strategies for MCP tools
- `mcp_wrapper.py` - Transparent wrapper for automatic tool cleaning
- `compact_integration.py` - Auto-compaction compatible with Claude Code

### Development Files
- `test_compatibility.py` - Model compatibility testing
- `test_optimization.py` - Prompt optimization validation
- `test_context_manager.py` - Context management and cleaning tests
- `legacy_prompts.py` - Original prompts for comparison

## Development Practices

### Adding New Models
1. Create `ModelCompatibilityProfile` in `model_compatibility.py`
2. Define regex patterns for model detection
3. Specify required fixes and compatibility level
4. Register in `default_registry`

### Extending Phases
1. Add new phase to `PhaseType` enum in `prompt_config.py`
2. Create agent configuration in `optimized_prompts.py`
3. Define validation criteria and tool requirements
4. Update orchestrator prompt template

### Adding MCP Tools
1. Extend tool filters in `get_tools_for_phase()`
2. Update tool categories in `ToolCategory` enum
3. Add to relevant phase configurations
4. Create cleaning strategy in `mcp_cleaners.py` if needed
5. Add tool configuration to `context_config.yaml`

### Customizing Context Cleaning
1. Create new `CleaningStrategy` subclass in `mcp_cleaners.py`
2. Implement `can_clean()` and `clean()` methods
3. Register strategy in `create_default_cleaning_strategies()`
4. Add configuration section in `context_config.yaml`
5. Test with realistic data in `test_context_manager.py`

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
- Validate template variables in `prompt_templates.py`
- Check context injection with `inject_dynamic_context()`
- Review phase-specific configurations

### Context Management Issues
- Check `context_config.yaml` for correct strategy configuration
- Monitor context metrics with `get_context_summary()`
- Verify cleaning strategies are registered properly
- Test with `python test_context_manager.py` for validation
- Enable detailed logging: `setup_compatibility_logging(level="DEBUG")`

## Context Management Features

### 🧹 Automatic MCP Cleaning
- **ProjectListCleaner**: Reduces project lists to essential data 
- **CodeSnippetCleaner**: Extracts only code text, removes metadata
- **DocumentCleaner**: Removes headers/footers, preserves content
- **UserStoryListCleaner**: Maintains core story info, removes tracking data 
- **RepositoryListCleaner**: Keeps identifiers, removes detailed metrics

### 📊 Context Monitoring
- Real-time token usage tracking with tiktoken precision
- MCP noise percentage calculation and alerting
- Automatic compaction trigger when thresholds exceeded
- Detailed metrics and reduction statistics
- Integration with Claude Code compact-implementation specs

### ⚙️ Configuration & Customization
- YAML-based configuration for all strategies and thresholds
- Tool-specific overrides and custom rules
- Performance monitoring and analytics
- Graceful fallback when cleaning fails
- Compatible with existing Claude Code workflows

### 🔧 Usage Example
```python
# Basic setup with auto-cleaning
from mcp_wrapper import wrap_existing_mcp_tools
from context_manager import ContextManager

# Wrap your MCP tools
wrapped_tools, wrapper = wrap_existing_mcp_tools(your_mcp_tools)

# Use wrapped tools - cleaning happens automatically
result = wrapped_tools[0]()  # Returns cleaned result

# Monitor performance
stats = wrapper.get_statistics()
print(f"Average reduction: {stats['average_reduction_percentage']}%")
```