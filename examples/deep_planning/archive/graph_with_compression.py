"""
Custom LangGraph with Compression Node

This module provides a custom StateGraph implementation that includes automatic
context compression before LLM calls. This replaces the standard create_react_agent
with a more controllable graph that can prevent context overflow errors.

Key Features:
- Preventive compression before every LLM call
- Compatible with all existing deepagents functionality
- Maintains ReAct agent behavior
- Integrates with existing CompactIntegration system
"""

import logging
from typing import Dict, Any, List, Optional, Union, Sequence, Callable, TypeVar, Type
from deepagents.state import DeepAgentState
from langchain_core.tools import BaseTool
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

# Import compression node
from ..context.compression_node import CompressionNode, create_compression_node

# Setup logger
logger = logging.getLogger(__name__)

StateSchema = TypeVar("StateSchema", bound=DeepAgentState)
StateSchemaType = Type[StateSchema]


class CompressedReactAgent:
    """
    A custom ReAct agent with integrated compression node.
    
    This class creates a StateGraph that includes automatic context compression
    before every LLM call, preventing context overflow errors while maintaining
    all the functionality of a standard ReAct agent.
    """
    
    def __init__(
        self,
        model: LanguageModelLike,
        tools: List[BaseTool],
        prompt: str,
        state_schema: Optional[StateSchemaType] = None,
        checkpointer: Optional[Any] = None,
        compact_integration: Optional[Any] = None,
        mcp_wrapper: Optional[Any] = None
    ):
        """
        Initialize the compressed ReAct agent.
        
        Args:
            model: Language model to use
            tools: List of tools available to the agent
            prompt: System prompt for the agent
            state_schema: State schema (defaults to DeepAgentState)
            checkpointer: Optional checkpointer for persistence
            compact_integration: CompactIntegration for compression
            mcp_wrapper: MCP wrapper for context management
        """
        self.model = model
        self.tools = tools
        self.prompt = prompt
        self.state_schema = state_schema or DeepAgentState
        self.checkpointer = checkpointer
        
        # Create compression node
        self.compression_node = create_compression_node(
            compact_integration=compact_integration,
            mcp_wrapper=mcp_wrapper,
            node_name="compress_context"
        )
        
        # Create tool node
        self.tool_node = ToolNode(tools)
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info("✅ Compressed ReAct agent initialized")
        logger.info(f"🧠 Compression: {'✅ Enabled' if compact_integration else '❌ Disabled'}")
        logger.info(f"🛠️ Tools: {len(tools)} available")
    
    def _build_graph(self) -> Any:
        """
        Build the StateGraph with compression integration.
        
        Returns:
            Compiled StateGraph with compression node
        """
        # Create the graph
        workflow = StateGraph(self.state_schema)
        
        # Add nodes
        workflow.add_node("compress_context", self.compression_node)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self.tool_node)
        
        # Set entry point - always start with compression
        workflow.set_entry_point("compress_context")
        
        # Add edges
        workflow.add_edge("compress_context", "agent")
        
        # Add conditional edges from agent
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        # Add edge from tools back to compression (for next iteration)
        workflow.add_edge("tools", "compress_context")
        
        # Detect if running under LangGraph API
        import os
        import sys
        
        is_langgraph_api = (
            os.getenv("LANGGRAPH_API_DEPLOYMENT") or 
            os.getenv("LANGGRAPH_ENV") or 
            os.getenv("LANGGRAPH_API") or
            os.getenv("UVICORN_HOST") or
            any("langgraph" in arg and (("dev" in arg) or ("up" in arg)) for arg in sys.argv) or
            os.path.exists("langgraph.json") or
            any("langgraph" in module for module in sys.modules.keys() if "api" in module or "server" in module)
        )
        
        # Compile the graph - omit checkpointer for LangGraph API
        if is_langgraph_api:
            logger.info("🌐 LangGraph API detected - using platform-managed persistence")
            compiled_graph = workflow.compile()
        else:
            compiled_graph = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("🏗️ StateGraph compiled with compression integration")
        logger.info("🔄 Flow: compress_context → agent → [tools → compress_context] → END")
        
        return compiled_graph
    
    async def _call_model(self, state: DeepAgentState) -> Dict[str, Any]:
        """
        Call the language model with the current state.
        
        This method prepares the messages and calls the LLM. The compression
        node has already processed the context at this point.
        
        Args:
            state: Current state containing messages and other data
            
        Returns:
            Updated state with model response
        """
        messages = state.get("messages", [])
        
        # Add system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            system_message = SystemMessage(content=self.prompt)
            messages = [system_message] + messages
        
        # Call the model
        try:
            logger.debug(f"🤖 Calling model with {len(messages)} messages")
            response = await self.model.ainvoke(messages)
            
            # Add the response to messages
            updated_messages = messages + [response]
            
            return {"messages": updated_messages}
            
        except Exception as e:
            logger.error(f"❌ Model call failed: {e}")
            # Add error message and end conversation
            error_message = AIMessage(content=f"Error: {str(e)}")
            return {"messages": messages + [error_message]}
    
    def _should_continue(self, state: DeepAgentState) -> str:
        """
        Determine if the agent should continue with tool calls or end.
        
        Args:
            state: Current state
            
        Returns:
            "continue" if tools should be called, "end" otherwise
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        # Check if the last message has tool calls
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        
        return "end"
    
    def invoke(self, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoke the agent synchronously.
        
        Args:
            input_data: Input data containing messages
            config: Optional configuration
            
        Returns:
            Final state with agent response
        """
        return self.graph.invoke(input_data, config)
    
    async def ainvoke(self, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoke the agent asynchronously.
        
        Args:
            input_data: Input data containing messages
            config: Optional configuration
            
        Returns:
            Final state with agent response
        """
        return await self.graph.ainvoke(input_data, config)
    
    def stream(self, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Stream agent execution.
        
        Args:
            input_data: Input data containing messages
            config: Optional configuration
            
        Yields:
            State updates during execution
        """
        yield from self.graph.stream(input_data, config)
    
    async def astream(self, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Stream agent execution asynchronously.
        
        Args:
            input_data: Input data containing messages
            config: Optional configuration
            
        Yields:
            State updates during execution
        """
        async for event in self.graph.astream(input_data, config):
            yield event
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """
        Get compression statistics from the compression node.
        
        Returns:
            Dictionary with compression metrics
        """
        return self.compression_node.get_statistics()


def create_compressed_react_agent(
    model: Union[str, LanguageModelLike],
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    prompt: str,
    state_schema: Optional[StateSchemaType] = None,
    checkpointer: Optional[Union[str, Any]] = None,
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None
) -> CompressedReactAgent:
    """
    Create a ReAct agent with integrated compression node.
    
    This function creates a custom StateGraph that includes automatic context
    compression before every LLM call, preventing context overflow while
    maintaining standard ReAct agent functionality.
    
    Args:
        model: Language model to use
        tools: List of tools available to the agent
        prompt: System prompt for the agent
        state_schema: State schema (defaults to DeepAgentState)
        checkpointer: Optional checkpointer for persistence
        compact_integration: CompactIntegration for compression
        mcp_wrapper: MCP wrapper for context management
        
    Returns:
        CompressedReactAgent instance with integrated compression
    """
    # Handle model parameter
    if isinstance(model, str):
        from deepagents.model import get_model
        model = get_model(model)
    
    # Handle checkpointer parameter
    actual_checkpointer = None
    if checkpointer == "memory":
        actual_checkpointer = InMemorySaver()
    elif checkpointer == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            actual_checkpointer = PostgresSaver()
        except ImportError:
            logger.warning("PostgresSaver not available, using InMemorySaver")
            actual_checkpointer = InMemorySaver()
    elif checkpointer is not None:
        actual_checkpointer = checkpointer
    
    # Create the agent
    agent = CompressedReactAgent(
        model=model,
        tools=list(tools),
        prompt=prompt,
        state_schema=state_schema,
        checkpointer=actual_checkpointer,
        compact_integration=compact_integration,
        mcp_wrapper=mcp_wrapper
    )
    
    logger.info("🚀 Compressed ReAct agent created successfully")
    
    return agent


def create_compression_compatible_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list = None,
    state_schema: Optional[StateSchemaType] = None,
    enable_planning_approval: bool = False,
    checkpointer: Optional[Union[str, Any]] = None,
    compact_integration: Optional[Any] = None,
    mcp_wrapper: Optional[Any] = None,
    **kwargs
) -> CompressedReactAgent:
    """
    Create a deep agent compatible with compression but using custom graph.
    
    This function provides the same interface as create_deep_agent but uses
    the compressed graph implementation for better context management.
    
    Args:
        tools: Additional tools for the agent
        instructions: System prompt instructions
        model: Language model to use
        subagents: List of subagents (not used in this implementation)
        state_schema: State schema
        enable_planning_approval: Whether to enable planning approval
        checkpointer: Checkpointer for state persistence
        compact_integration: CompactIntegration for compression
        mcp_wrapper: MCP wrapper for context management
        **kwargs: Additional arguments
        
    Returns:
        CompressedReactAgent with built-in tools and compression
    """
    # Import built-in tools
    from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
    
    # Build prompt
    base_prompt = """You have access to a number of standard tools

## `write_todos`

You have access to the `write_todos` tools to help you manage and plan tasks. Use these tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress.
These tools are also EXTREMELY helpful for planning tasks, and for breaking down larger complex tasks into smaller steps. If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable.

It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.
## `task`

- When doing web search, prefer to use the `task` tool in order to reduce context usage."""
    
    prompt = instructions + base_prompt
    built_in_tools = [write_todos, write_file, read_file, ls, edit_file]
    
    # Add planning approval tool if enabled
    if enable_planning_approval:
        built_in_tools.append(review_plan)
        prompt += "\\n\\n## Planning and Approval\\n\\nYou have access to the `review_plan` tool for human-in-the-loop approval of plans. Use this when working on complex tasks that benefit from human review before execution."
    
    # Handle model
    if model is None:
        from deepagents.model import get_default_model
        model = get_default_model()
    elif isinstance(model, str):
        from deepagents.model import get_model
        model = get_model(model)
    
    # TODO: Implement subagents support (for now, just note that they're not used)
    if subagents:
        logger.warning("⚠️ Subagents not yet implemented in compressed graph - ignoring")
    
    # Combine tools
    all_tools = built_in_tools + list(tools)
    
    # Create the compressed agent
    agent = create_compressed_react_agent(
        model=model,
        tools=all_tools,
        prompt=prompt,
        state_schema=state_schema or DeepAgentState,
        checkpointer=checkpointer,
        compact_integration=compact_integration,
        mcp_wrapper=mcp_wrapper
    )
    
    logger.info("✅ Compression-compatible deep agent created")
    logger.info(f"🛠️ Total tools: {len(all_tools)} (built-in: {len(built_in_tools)}, external: {len(tools)})")
    
    return agent