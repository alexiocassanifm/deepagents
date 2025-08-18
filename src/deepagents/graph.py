from deepagents.sub_agent import _create_task_tool, SubAgent
from deepagents.model import get_default_model, get_model
from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
from deepagents.state import DeepAgentState
from typing import Sequence, Union, Callable, Any, TypeVar, Type, Optional
from langchain_core.tools import BaseTool
from langchain_core.language_models import LanguageModelLike

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

StateSchema = TypeVar("StateSchema", bound=DeepAgentState)
StateSchemaType = Type[StateSchema]

base_prompt = """You have access to a number of standard tools

## `write_todos`

You have access to the `write_todos` tools to help you manage and plan tasks. Use these tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.
These tools are also EXTREMELY helpful for planning tasks, and for breaking down larger complex tasks into smaller steps. If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable.

It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.
## `task`

- When doing web search, prefer to use the `task` tool in order to reduce context usage."""


def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    enable_planning_approval: bool = False,
    checkpointer: Optional[Union[str, Any]] = None,
    pre_model_hook: Optional[Callable] = None,
):
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    and then four file editing tools: write_file, ls, read_file, edit_file.

    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have. Will go in
            the system prompt.
        model: The model to use.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
                - (optional) `requires_approval` (bool): Whether this subagent requires plan approval
                - (optional) `approval_points` (list): Specific points where approval is needed
        state_schema: The schema of the deep agent. Should subclass from DeepAgentState
        enable_planning_approval: Whether to enable human-in-the-loop planning approval
        checkpointer: Checkpointer to use for state persistence. Can be:
            - "memory": Use InMemorySaver 
            - "postgres": Use PostgresSaver (requires configuration)
            - Custom checkpointer instance
            - None: No checkpointing (disables human-in-the-loop features)
        pre_model_hook: Optional function to process state before each LLM call.
            Useful for context compression, message filtering, or preprocessing.
            Function should take DeepAgentState and return modified DeepAgentState.
    """
    prompt = instructions + base_prompt
    built_in_tools = [write_todos, write_file, read_file, ls, edit_file]
    
    # Add planning approval tool if enabled
    if enable_planning_approval:
        built_in_tools.append(review_plan)
        prompt += "\n\n## Planning and Approval\n\nYou have access to the `review_plan` tool for human-in-the-loop approval of plans. Use this when working on complex tasks that benefit from human review before execution."
    
    if model is None:
        model = get_default_model()
    else:
        model = get_model(model)
    state_schema = state_schema or DeepAgentState
    
    task_tool = _create_task_tool(
        list(tools) + built_in_tools,
        instructions,
        subagents or [],
        model,
        state_schema
    )
    all_tools = built_in_tools + list(tools) + [task_tool]
    
    # Detect if running under LangGraph API
    import os
    import sys
    
    # More comprehensive detection for LangGraph API environment
    is_langgraph_api = (
        os.getenv("LANGGRAPH_API_DEPLOYMENT") or 
        os.getenv("LANGGRAPH_ENV") or 
        os.getenv("LANGGRAPH_API") or
        os.getenv("UVICORN_HOST") or
        # Check if langgraph dev server is running
        any("langgraph" in arg and ("dev" in arg or "up" in arg) for arg in sys.argv) or
        # Check current working directory for langgraph project structure
        os.path.exists("langgraph.json") or
        # Check if we're being imported by langgraph API
        any("langgraph" in module for module in sys.modules.keys() if "api" in module or "server" in module)
    )
    
    # Set up checkpointer only if NOT running under LangGraph API
    actual_checkpointer = None
    if checkpointer is not None and not is_langgraph_api:
        if checkpointer == "memory":
            actual_checkpointer = InMemorySaver()
        elif checkpointer == "postgres":
            # Import here to avoid dependency issues if not used
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                actual_checkpointer = PostgresSaver()
            except ImportError:
                print("Warning: PostgresSaver not available. Install with: pip install langgraph-checkpoint-postgres")
                actual_checkpointer = InMemorySaver()
        else:
            # Assume it's a custom checkpointer instance
            actual_checkpointer = checkpointer
    elif checkpointer is not None and is_langgraph_api:
        print("🌐 Running under LangGraph API - using platform-managed persistence")
    
    # Create the agent - when under LangGraph API, completely omit checkpointer parameter
    if is_langgraph_api:
        agent = create_react_agent(
            model,
            prompt=prompt,
            tools=all_tools,
            state_schema=state_schema,
            pre_model_hook=pre_model_hook
        )
    else:
        agent = create_react_agent(
            model,
            prompt=prompt,
            tools=all_tools,
            state_schema=state_schema,
            checkpointer=actual_checkpointer,
            pre_model_hook=pre_model_hook
        )
    
    return agent
