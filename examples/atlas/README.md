# Atlas - LangChain MCP Codebase Research Agent

Atlas is a specialized deep agent that uses **official LangChain MCP adapters** to perform comprehensive research on existing codebases and generate structured technical documentation.

## Overview

Atlas acts as a tech lead/software architect, using the `langchain-mcp-adapters` library to properly integrate with MCP servers. It combines multiple specialized sub-agents to analyze codebases and produce comprehensive documentation with real-time access to project data.

## Key Features

- **🔌 Official LangChain MCP Integration**: Uses `langchain-mcp-adapters` and `MultiServerMCPClient`
- **📡 Auto-Detection**: Automatically detects and loads MCP tools from fairmind server
- **🔄 Graceful Fallback**: Falls back to demo tools when MCP server unavailable
- **🎯 Multi-Stage Analysis**: Requirements → Architecture → Implementation → Documentation
- **🤖 Sub-Agent Orchestration**: Coordinates specialized agents for different analysis aspects
- **📚 Comprehensive Documentation**: Generates structured markdown reports
- **⚡ Async Support**: Proper async/await patterns for MCP tool loading

## Architecture

### Main Agent: Atlas
- Orchestrates the entire research and documentation workflow
- Manages project selection and coordinates sub-agents
- Generates final documentation deliverables

### Sub-Agents

1. **Technical Researcher** - Deep code analysis and pattern identification
2. **Report Generator** - Transforms findings into structured documentation  
3. **AI Engineer** - Technical recommendations and architectural insights
4. **Prompt Engineer** - Documentation optimization and clarity

## MCP Tools Integration

Atlas uses the fairmind MCP server tools:

- `list_projects()` - Discover available projects
- `get_project_overview()` - Requirements, user stories, tasks
- `get_codebase_structure()` - Repository and directory structures
- `find_code_snippets()` - Semantic code search
- `get_file_content()` - Complete file analysis

## Setup

1. **Install deepagents locally** (from project root):
   ```bash
   cd /Users/alexiocassani/Projects/deepagents
   pip install -e .
   ```

2. **Install additional dependencies**:
   ```bash
   cd examples/atlas
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and fairmind MCP server configuration
   ```

4. **Run with LangGraph**:
   ```bash
   # Standard Atlas agent with MCP integration
   langgraph dev --graph atlas
   
   # Advanced MCP integration example (if needed)
   langgraph dev --graph atlas-mcp
   ```

### MCP Integration Setup

Atlas uses the **official LangChain MCP adapters** with **HTTP streamable transport** for proper integration:

```python
# HTTP streamable MCP connection
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "fairmind": {
        "url": "https://project-context.mindstream.fairmind.ai/mcp/mcp/",
        "transport": "streamable_http",
        "headers": {
            "Authorization": "Bearer your_token_here",
            "Content-Type": "application/json"
        }
    }
})

tools = await client.get_tools()
```

**Environment Variables:**
- `FAIRMIND_MCP_URL`: Fairmind MCP server HTTP endpoint
- `FAIRMIND_MCP_TOKEN`: Your fairmind MCP bearer token  
- `LANGCHAIN_TRACING_V2=true`: Enable LangSmith tracing

**Transport Benefits:**
- 🌐 **HTTP-based**: Works with remote MCP servers
- 🔄 **Streamable**: Supports real-time data streaming
- 🔐 **Authenticated**: Bearer token authentication
- 🚀 **Production-ready**: Suitable for cloud deployments

## Usage Flow

1. **Project Discovery**: Atlas lists available projects from MCP server
2. **Project Selection**: User chooses which project to analyze
3. **Research Phase**: Multi-stage analysis using sub-agents:
   - Business requirements and user stories
   - Technical architecture and code structure
   - Implementation patterns and quality assessment
4. **Documentation Generation**: Creates comprehensive reports:
   - `project_analysis.md` - Complete project overview
   - `technical_report.md` - Deep technical analysis
   - `architecture_overview.md` - System design documentation

## Output Documentation

Atlas generates structured markdown documentation with:

- **Executive Summaries** for complex analyses
- **Technical Architecture** diagrams and descriptions
- **Implementation Analysis** with code examples
- **Recommendations** for improvements
- **Proper Citations** and references

## Example Output Structure

```markdown
# Project Analysis Report

## Executive Summary
- Key findings and insights
- Critical recommendations

## Project Overview
- Business requirements
- User stories and features

## Technical Architecture
- System design patterns
- Technology stack analysis

## Implementation Analysis
- Code quality assessment
- Architectural decisions
- Dependencies and frameworks

## Recommendations
- Technical improvements
- Architecture enhancements
- Development process suggestions
```

## LangGraph Features

Atlas fully utilizes LangGraph capabilities:

- **Parallel Execution**: Sub-agents run concurrently
- **State Management**: Maintains research context
- **Human-in-Loop**: Interactive project selection
- **Streaming**: Real-time progress updates
- **Error Handling**: Robust failure recovery

## Customization

You can extend Atlas by:

- Adding new MCP tool wrappers
- Creating specialized sub-agents
- Customizing documentation templates
- Integrating additional analysis tools

## Dependencies

- `deepagents` - Core agent framework
- `langchain-mcp-adapters` - MCP server integration
- `langgraph` - Agent orchestration
- `langchain-anthropic` - Claude model access

## Notes

This example demonstrates advanced patterns:
- MCP server integration for real codebase access
- Multi-agent orchestration with specialized roles
- Comprehensive documentation generation
- LangGraph's parallel execution capabilities

Perfect for organizations wanting to automatically generate technical documentation and analysis of their codebases.