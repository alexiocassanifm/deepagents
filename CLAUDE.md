# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `deepagents`, a Python package that implements "deep agents" - AI agents with planning tools, sub-agents, file system access, and detailed prompts. It's built on LangGraph and inspired by Claude Code's architecture.

## Development Commands

### Package Management
- Install dependencies: `pip install -e .`
- Install for development with test dependencies: `pip install -e .[dev]` (if dev extras exist)

### Testing
- No specific test commands are defined in pyproject.toml
- Check for test files in the repository to determine testing approach
- Common Python testing: `python -m pytest` or `python -m unittest`

### Build and Distribution
- Build package: `python -m build`
- Uses setuptools build backend as defined in pyproject.toml

## Architecture

### Core Components

1. **Deep Agent Creation (`graph.py`)**
   - `create_deep_agent()` is the main entry point
   - Combines user tools with built-in tools: `write_todos`, `write_file`, `read_file`, `ls`, `edit_file`
   - Creates a LangGraph ReactAgent with a comprehensive system prompt
   - Default model: "claude-sonnet-4-20250514" (see `model.py`)

2. **Built-in Tools (`tools.py`)**
   - **Todo Management**: `write_todos` - planning and task tracking tool
   - **Mock File System**: `ls`, `read_file`, `write_file`, `edit_file` - operates on LangGraph state, not real filesystem
   - File system is one-level deep (no subdirectories)
   - Files stored in state under "files" key

3. **Sub-Agents (`sub_agent.py`)**
   - Dynamic `task` tool creation for spawning specialized agents
   - General-purpose sub-agent always available
   - Custom sub-agents can be defined with specific tools and prompts
   - Sub-agents use same model and core architecture as main agent

4. **System Prompts (`prompts.py`)**
   - Detailed instructions for todo management (heavily inspired by Claude Code)
   - Task delegation patterns and usage guidelines
   - File editing and tool usage instructions

5. **State Management (`state.py`)**
   - Extends LangGraph's base state with todos and files
   - Todo items have: content, status (pending/in_progress/completed), id

### Key Patterns

- **Planning First**: Agents are prompted to use todo lists for complex tasks
- **Context Quarantine**: Sub-agents isolate work to prevent main context pollution  
- **Mock Filesystem**: Safe file operations without affecting real system
- **LangGraph Integration**: Full compatibility with LangGraph features (streaming, human-in-loop, etc.)

### Dependencies
- Core: `langgraph>=0.2.6`, `langchain-anthropic>=0.1.23`, `langchain>=0.2.14`
- Python 3.11+ required
- Optional: MCP support via `langchain-mcp-adapters`

## Usage Patterns

### Creating Agents
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=[your_tools],
    instructions="Your agent prompt",
    subagents=[...],  # Optional
    model=custom_model  # Optional
)

result = agent.invoke({"messages": [{"role": "user", "content": "task"}]})
```

### File System Access
Pass files in state: `{"messages": [...], "files": {"filename": "content"}}`
Access files after: `result["files"]`

### Sub-agents
Define custom sub-agents with specific tools and prompts for specialized tasks.