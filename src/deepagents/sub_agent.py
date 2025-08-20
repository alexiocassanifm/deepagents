from deepagents.prompts import TASK_DESCRIPTION_PREFIX, TASK_DESCRIPTION_SUFFIX
from deepagents.state import DeepAgentState
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from typing_extensions import TypedDict
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.chat_models import init_chat_model
from typing import Annotated, NotRequired, Any
from langgraph.types import Command
import logging

from langgraph.prebuilt import InjectedState

logger = logging.getLogger(__name__)


class SubAgent(TypedDict):
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]
    # Optional per-subagent model configuration
    model_settings: NotRequired[dict[str, Any]]
    requires_approval: NotRequired[bool]
    approval_points: NotRequired[list[str]]


def _create_task_tool(tools, instructions, subagents: list[SubAgent], model, state_schema):
    # Try to create the agent with the original tools first
    try:
        agents = {
            "general-purpose": create_react_agent(model, prompt=instructions, tools=tools)
        }
    except KeyError as e:
        # If there's a KeyError with 'tool_input', try filtering problematic tools
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"KeyError creating sub-agent: {e}. Attempting to filter problematic tools.")
        
        # Filter out potentially problematic wrapped tools
        filtered_tools = []
        for tool_ in tools:
            # Skip wrapped tools that might have corrupted signatures
            if hasattr(tool_, '__wrapped__') or hasattr(tool_, '_wrapper'):
                logger.debug(f"Skipping wrapped tool: {getattr(tool_, 'name', 'unknown')}")
                continue
            filtered_tools.append(tool_)
        
        # Try again with filtered tools
        agents = {
            "general-purpose": create_react_agent(model, prompt=instructions, tools=filtered_tools)
        }
    tools_by_name = {}
    for tool_ in tools:
        # Only wrap if it's a callable but not already a tool
        if callable(tool_) and not isinstance(tool_, BaseTool):
            try:
                # Check if it's already a decorated tool
                if not (hasattr(tool_, 'name') and hasattr(tool_, 'description')):
                    tool_ = tool(tool_)
            except Exception:
                # If conversion fails, just use as-is
                pass
        
        # Store by name if available
        if hasattr(tool_, 'name'):
            tools_by_name[tool_.name] = tool_
    for _agent in subagents:
        if "tools" in _agent:
            _tools = [tools_by_name[t] for t in _agent["tools"] if t in tools_by_name]
        else:
            _tools = [t for t in tools if hasattr(t, 'name')]  # Filter to valid tools
        
        # If the subagent requires approval, add review_plan to its tools
        if _agent.get("requires_approval", False):
            from deepagents.tools import review_plan
            _tools = list(_tools) + [review_plan]
        
        try:
        # Resolve per-subagent model if specified, else fallback to main model
        if "model_settings" in _agent:
            model_config = _agent["model_settings"]
            # Always use get_default_model to ensure all settings are applied
            sub_model = init_chat_model(**model_config)
        else:
            sub_model = model
            agents[_agent["name"]] = create_react_agent(
                sub_model, prompt=_agent["prompt"], tools=_tools, state_schema=state_schema
            )
        except KeyError as e:
            # If creation fails, try without problematic tools
            logger.warning(f"Failed to create sub-agent {_agent['name']}: {e}. Trying with filtered tools.")
            safe_tools = [t for t in _tools if not (hasattr(t, '__wrapped__') or hasattr(t, '_wrapper'))]
            agents[_agent["name"]] = create_react_agent(
                model, prompt=_agent["prompt"], tools=safe_tools, state_schema=state_schema
            )

    other_agents_string = [
        f"- {_agent['name']}: {_agent.get('description', 'Specialized agent')}" for _agent in subagents
    ]

    # Build agent info with approval requirements
    agents_info = {}
    for _agent in subagents:
        agents_info[_agent["name"]] = {
            "requires_approval": _agent.get("requires_approval", False),
            "approval_points": _agent.get("approval_points", [])
        }

    @tool(
        description=TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents_string)
        + TASK_DESCRIPTION_SUFFIX
    )
    async def task(
        description: str,
        subagent_type: str,
        state: Annotated[DeepAgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        if subagent_type not in agents:
            return f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}"
        
        # The subagent will handle its own approval workflow internally
        # No need to pre-approve here - let the subagent use review_plan tool if needed
        
        # Execute the sub-agent
        sub_agent = agents[subagent_type]
        state["messages"] = [{"role": "user", "content": description}]
        result = await sub_agent.ainvoke(state)
        return Command(
            update={
                "files": result.get("files", {}),
                "messages": [
                    ToolMessage(
                        result["messages"][-1].content, tool_call_id=tool_call_id
                    )
                ],
            }
        )

    return task
