# MCP Integration with LangGraph

This document explains how to properly configure MCP (Model Context Protocol) servers with DeepAgents using LangGraph's native MCP support.

## ✅ Correct Approach: LangGraph Native MCP

MCP servers should be configured directly in `langgraph.json`, not through Python code. LangGraph automatically loads and makes MCP tools available to agents.

### Configuration

Add MCP servers to your `langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "atlas": "./atlas_agent.py:agent"
  },
  "env": ".env",
  "mcps": {
    "sequential-thinking": {
      "command": "npx", 
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "fairmind": {
      "command": "fairmind-mcp-server",
      "args": ["--port", "8000"]
    }
  }
}
```

### Usage in Agents

No special Python code is needed - MCP tools become automatically available:

```python
from deepagents import create_deep_agent

# MCP tools are automatically loaded by LangGraph
agent = create_deep_agent(
    tools=your_regular_tools,  # Just include your regular tools
    instructions="Your instructions...",
    enable_planning_approval=True,
    checkpointer="memory"
)

# The agent will automatically have access to:
# - mcp__sequential-thinking__sequentialthinking (if configured)
# - Any other MCP tools defined in langgraph.json
```

### Available MCP Tools

When properly configured, agents automatically get access to:

#### Sequential Thinking
- **Tool name**: `mcp__sequential-thinking__sequentialthinking`
- **Purpose**: Step-by-step reasoning for complex problems
- **Setup**: Add the configuration shown above to `langgraph.json`

#### Fairmind (if configured)
- Various project context and analysis tools
- **Setup**: Configure with appropriate credentials in `.env`

## Benefits of This Approach

1. **Simplicity**: No Python code needed for MCP integration
2. **Standard**: Uses LangGraph's official MCP support
3. **Automatic**: Tools are automatically loaded and available
4. **Maintainable**: Configuration is centralized in `langgraph.json`
5. **Reliable**: Leverages LangGraph's tested MCP implementation

## Example with Planning Approval

```python
# atlas_agent.py
from deepagents import create_deep_agent, SubAgent

report_generator = SubAgent(
    name="report-generator",
    description="Creates documentation with planning approval",
    prompt="""You can use mcp__sequential-thinking__sequentialthinking 
    for enhanced reasoning when creating plans...""",
    requires_approval=True
)

agent = create_deep_agent(
    tools=atlas_tools,  # Regular tools only
    instructions=atlas_instructions,
    subagents=[report_generator],
    enable_planning_approval=True,
    checkpointer="memory"
)
```

The agent will automatically have access to both:
- Regular tools from `atlas_tools`
- MCP tools like `mcp__sequential-thinking__sequentialthinking`
- Planning approval tools from `enable_planning_approval=True`

## Troubleshooting

### Tool Not Available
If an MCP tool isn't available:
1. Check `langgraph.json` configuration
2. Ensure the MCP server is properly installed
3. Verify environment variables (if needed)
4. Check LangGraph logs for connection errors

### Sequential Thinking Setup
```bash
# The MCP server is automatically installed when configured
# No manual installation needed - npx handles it automatically
```

### Fairmind Setup
```bash
# Set required environment variables in .env
FAIRMIND_MCP_URL=your_url
FAIRMIND_MCP_TOKEN=your_token
```

## Migration from Previous Approach

If you previously used custom MCP loading code:

### ❌ Old Approach (Don't Use)
```python
from deepagents.mcp_config import get_available_mcp_tools
mcp_tools = get_available_mcp_tools()
agent = create_deep_agent(tools=regular_tools + mcp_tools, ...)
```

### ✅ New Approach (Correct)
```python
from deepagents import create_deep_agent
# Configure MCP in langgraph.json instead
agent = create_deep_agent(tools=regular_tools, ...)
```

The MCP tools will be automatically available through LangGraph's native support.