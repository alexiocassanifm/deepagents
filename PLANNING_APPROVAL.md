# Human-in-the-Loop Planning Approval

This document describes the new human-in-the-loop planning approval functionality added to DeepAgents, which allows users to review and approve plans before AI agents execute complex tasks.

## Overview

The planning approval system uses LangGraph's `interrupt()` mechanism to pause agent execution and request human feedback on generated plans. This is particularly useful for documentation generation, where users want to review the structure and approach before the AI proceeds with writing.

## Key Features

- 🛑 **Automatic Plan Interruption**: Agents pause execution to present plans for human review
- ✏️ **Plan Modification**: Users can request changes to plans before execution  
- ✅ **Approval Workflow**: Simple approve/edit/reject options
- 💾 **State Persistence**: Uses LangGraph checkpointing to maintain state across interruptions
- 🔧 **Configurable**: Works with any subagent, configurable per agent
- 🎯 **Integration**: Seamlessly integrates with existing DeepAgents architecture

## Architecture

### Core Components

1. **`planning.py`** - DocumentationPlanner class and planning utilities
2. **`tools.py`** - `review_plan` tool for human-in-the-loop interaction
3. **`state.py`** - Extended state with plan tracking fields
4. **`sub_agent.py`** - Enhanced with `requires_approval` flag support
5. **`graph.py`** - Updated `create_deep_agent` with planning parameters
6. **`mcp_config.py`** - Optional MCP integration for enhanced planning

### Workflow

```mermaid
graph TD
    A[User Request] --> B[Agent Delegates to Subagent]
    B --> C{Subagent requires approval?}
    C -->|Yes| D[Generate Plan]
    C -->|No| H[Execute Directly]
    D --> E[Present Plan via interrupt()]
    E --> F[Human Reviews Plan]
    F --> G{User Decision}
    G -->|Approve| H[Execute with Plan]
    G -->|Edit| I[Modify Plan]
    G -->|Reject| J[Restart Planning]
    I --> E
    H --> K[Complete Task]
    J --> D
```

## Usage

### Basic Setup

```python
from deepagents import create_deep_agent, SubAgent

# Define subagent requiring approval
doc_generator = SubAgent(
    name="doc-generator",
    description="Creates documentation with human approval",
    prompt="Your detailed prompt...",
    requires_approval=True,  # Enable approval requirement
    approval_points=["before_write"]  # Optional: specific approval points
)

# Create agent with planning approval enabled
agent = create_deep_agent(
    tools=your_tools,
    instructions="Your instructions...",
    subagents=[doc_generator],
    enable_planning_approval=True,  # Enable planning features
    checkpointer="memory"  # Required for state persistence
)
```

### Atlas Example

The Atlas agent has been updated to demonstrate this functionality:

```python
# Report generator now requires approval
report_generator = {
    "name": "report-generator",
    "description": "Creates documentation with mandatory plan approval",
    "prompt": "Detailed prompt with planning instructions...",
    "requires_approval": True,
    "approval_points": ["before_write", "plan_review"]
}

# Agent created with planning features
agent = create_deep_agent(
    tools=all_tools,
    instructions=atlas_instructions,
    subagents=[technical_researcher, report_generator, ...],
    enable_planning_approval=True,
    checkpointer="memory"
)
```

## User Interaction Flow

When a subagent with `requires_approval=True` is invoked:

1. **Plan Generation**: The subagent automatically creates a detailed plan
2. **Plan Presentation**: The plan is formatted and presented to the user
3. **User Review**: User sees a structured plan with sections and estimates
4. **User Response**: User can respond with:
   - `approve` - Proceed with the plan as-is
   - `edit: <description>` - Request specific modifications
   - `reject: <reason>` - Reject and restart planning

### Example Interaction

```
👤 User: "Create documentation for our API project"

🤖 Agent: "I'll use the report-generator to create that documentation."

📋 Plan Presented:
╭─────────────────────────────────────────╮
│           DOCUMENTATION PLAN            │
├─────────────────────────────────────────┤
│ Title: API Project Documentation        │
│ Sections:                               │
│ 1. API Overview (1-2 pages)            │
│ 2. Authentication (2-3 pages)          │
│ 3. Endpoints (3-5 pages)               │
│ 4. Examples (2-4 pages)                │
│ Total: ~10 pages                        │
╰─────────────────────────────────────────╯

👤 User: "edit: add troubleshooting section"

🤖 Agent: "Plan updated with troubleshooting section. Proceeding with documentation..."
```

## Configuration Options

### Checkpointer Options

```python
# In-memory (for development/testing)
checkpointer="memory"

# PostgreSQL (for production)  
checkpointer="postgres"

# Custom checkpointer
checkpointer=your_custom_checkpointer
```

### SubAgent Configuration

```python
SubAgent(
    name="agent-name",
    description="Agent description", 
    prompt="Detailed prompt",
    requires_approval=True,  # Enable approval requirement
    approval_points=[        # Optional: specific approval points
        "before_write",
        "plan_review", 
        "final_check"
    ]
)
```

## MCP Integration

MCP (Model Context Protocol) servers are configured directly through LangGraph's native MCP support in `langgraph.json`:

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
    }
  }
}
```

### Sequential Thinking

The sequential-thinking MCP server provides advanced step-by-step reasoning capabilities. When configured in `langgraph.json`, it automatically becomes available as the `mcp__sequential-thinking__sequentialthinking` tool.

**Setup:**
1. Add the MCP configuration to `langgraph.json` (as shown above)
2. LangGraph automatically loads and makes the tool available
3. Agents can use sequential thinking for enhanced planning without any code changes

## Testing

Run the test suite:

```bash
# Test planning components
python examples/atlas/test_planning_workflow.py

# Demo the workflow
python examples/atlas/demo_planning_approval.py
```

## Technical Implementation

### Key Classes

- **`Plan`**: Represents an execution plan with sections and metadata
- **`DocumentationPlanner`**: Generates and manages documentation plans
- **`PlanInfo`**: TypedDict for plan state management

### State Management

The `DeepAgentState` has been extended with:

```python
class DeepAgentState(AgentState):
    pending_plans: Annotated[NotRequired[List[PlanInfo]], plan_reducer]
    approved_plan: NotRequired[PlanInfo] 
    current_plan: NotRequired[PlanInfo]
    analysis_results: NotRequired[Dict[str, Any]]
    documentation_requirements: NotRequired[List[str]]
    target_audience: NotRequired[str]
```

### LangGraph Integration

Uses LangGraph's interrupt mechanism:

```python
from langgraph.types import interrupt, Command

# Pause for human input
response = interrupt({
    "type": "plan_review_request",
    "formatted_plan": formatted_plan,
    "options": {"approve": "...", "edit": "...", "reject": "..."}
})

# Resume based on response
if response == "approve":
    return Command(update={"approved_plan": plan})
```

## Benefits

1. **Quality Control**: Human oversight prevents unwanted or incorrect content
2. **Collaboration**: Enables true human-AI collaboration on complex tasks  
3. **Flexibility**: Plans can be modified before execution
4. **Transparency**: Users see exactly what will be created before it happens
5. **Efficiency**: Only requires human input at key decision points

## Future Enhancements

- Plan templates for common document types
- Plan versioning and history
- Integration with external review systems
- Multi-step approval workflows
- Plan analytics and optimization

## Examples

See the `/examples/atlas/` directory for:
- `atlas_agent.py` - Updated Atlas with planning approval
- `test_planning_workflow.py` - Comprehensive test suite
- `demo_planning_approval.py` - Interactive demonstration

This feature enables true human-AI collaboration for complex content generation tasks while maintaining the power and flexibility of the DeepAgents framework.