"""
Deep Planning Agent - Structured 4-Phase Development Process with MCP Integration

This agent implements a methodical approach to complex software development tasks:

1. **Silent Investigation** - Autonomous exploration using MCP tools
2. **Targeted Discussion** - Clarifying questions and requirements gathering  
3. **Structured Planning** - Comprehensive plan document creation with 8 sections
4. **Task Generation** - Breaking down the plan into actionable tasks

Key Features:
- Integration with Fairmind MCP tools for real-time project analysis
- Todo management throughout all phases for progress tracking
- Human-in-the-loop plan approval before execution
- Structured plan validation with required sections
- Sub-agent orchestration for specialized analysis
"""

import asyncio
import os
import logging
from typing import Dict, Any, List, Optional, Literal, Tuple
from deepagents import create_deep_agent

# Comprehensive type annotation fix for Pydantic/LangChain compatibility
try:
    from typing import Annotated, Optional, Callable, Awaitable
except ImportError:
    from typing_extensions import Annotated, Optional, Callable, Awaitable

# Import all necessary Pydantic components
try:
    from pydantic import BaseModel, Field, SkipValidation
    from pydantic.fields import FieldInfo
    from pydantic.dataclasses import dataclass as pydantic_dataclass
    from pydantic._internal._typing_extra import eval_type_lenient
    from pydantic.json_schema import GenerateJsonSchema
    from pydantic_core import core_schema, SchemaValidator
    
    # Create ArgsSchema type alias if missing
    ArgsSchema = type("ArgsSchema", (BaseModel,), {})
    
except ImportError as e:
    print(f"Warning: Could not import Pydantic components: {e}")
    # Create basic fallbacks
    ArgsSchema = type("ArgsSchema", (), {})
    SkipValidation = type("SkipValidation", (), {})

# Make all types available globally
import builtins
import sys
builtins.Annotated = Annotated
builtins.ArgsSchema = ArgsSchema
builtins.SkipValidation = globals().get('SkipValidation', type("SkipValidation", (), {}))
builtins.Optional = Optional
builtins.Callable = Callable
builtins.Any = Any
builtins.Awaitable = Awaitable
builtins.tool_input = Any
globals().update({
    'Annotated': Annotated,
    'ArgsSchema': ArgsSchema,
    'SkipValidation': globals().get('SkipValidation', type("SkipValidation", (), {})),
    'Optional': Optional,
    'Callable': Callable,
    'Any': Any,
    'Awaitable': Awaitable,
    'tool_input': Any,
    'BaseModel': globals().get('BaseModel'),
    'Field': globals().get('Field'),
    'FieldInfo': globals().get('FieldInfo')
})

# Patch typing module
import typing
typing.Annotated = Annotated
typing.ArgsSchema = ArgsSchema
typing.SkipValidation = globals().get('SkipValidation', type("SkipValidation", (), {}))
typing.Optional = Optional
typing.Callable = Callable
typing.Any = Any
typing.Awaitable = Awaitable
typing.tool_input = Any

# Patch all relevant modules
module_patches = {
    'deepagents.tools': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
    'deepagents.sub_agent': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'], 
    'deepagents.state': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
    'langchain_core.tools.base': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
    'langchain_core.tools.convert': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
    'langchain_core.tools.structured': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input'],
    'pydantic.deprecated.decorator': ['Annotated', 'ArgsSchema', 'SkipValidation', 'Optional', 'Callable', 'Any', 'Awaitable', 'tool_input']
}

# Apply patches
for module_name, attrs in module_patches.items():
    try:
        import importlib
        if module_name in sys.modules:
            module = sys.modules[module_name]
            for attr in attrs:
                if not hasattr(module, attr):
                    setattr(module, attr, globals()[attr])
    except Exception as e:
        # Ignore patching errors but log them
        logging.debug(f"Note: Could not patch {module_name}: {e}")

# Setup logger for initialization
init_logger = logging.getLogger('deep_planning_init')
init_logger.info("🔧 Type annotation patching completed")

# Configure debug logging for development
def setup_debug_logging():
    """Setup comprehensive debug logging for all components."""
    log_level = os.getenv('PYTHON_LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'debug.log')
    
    # FORCE INFO level for better console visibility with LangGraph
    force_info = log_level in ['INFO', 'DEBUG']
    actual_level = logging.INFO if force_info else getattr(logging, log_level)
    
    # Configure root logger with file and console handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(actual_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter with more prominent format for console
    console_formatter = logging.Formatter('🔥 %(levelname)s - %(name)s - %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler (to view logs on screen) - FORCE INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Always show INFO in console
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Explicitly configure LangGraph loggers to propagate to console
    langgraph_loggers = ['langgraph', 'langchain', 'langgraph_api', 'langgraph_runtime_inmem']
    for logger_name in langgraph_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # Reduce LangGraph noise but keep errors
        logger.propagate = True
    
    # File handler (to save logs to file)
    file_handler = logging.FileHandler(log_file, mode='w')  # 'w' to overwrite each time
    file_handler.setLevel(logging.DEBUG)  # Always DEBUG on file
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Enable debug for specific modules
    loggers_to_debug = [
        'mcp_cleaners',
        'context_manager', 
        'mcp_wrapper',
        'mcp_context_tracker',  # New logger for context tracking
        'deepagents',
        'langgraph',
        'langchain'
    ]
    
    for logger_name in loggers_to_debug:
        logger = logging.getLogger(logger_name)
        # Configure specific loggers for context management to INFO
        if logger_name in ['mcp_context_tracker', 'context_manager', 'mcp_wrapper']:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)
    
    setup_logger = logging.getLogger('setup')
    setup_logger.info(f"🔍 Debug logging enabled at level: {log_level} (forced to INFO for console)")
    setup_logger.info(f"📁 Log file: {log_file}")
    setup_logger.debug(f"📊 Debug loggers: {', '.join(loggers_to_debug)}")
    setup_logger.debug(f"🎯 Context management loggers set to INFO level")
    setup_logger.debug(f"🔥 Console logging FORCED to INFO level for visibility")
    
    # Test log to verify it works - THESE SHOULD NOW APPEAR IN CONSOLE
    logging.debug("🚀 Debug logging setup completed - test message")
    logging.info("ℹ️ Info logging setup completed - test message - THIS SHOULD BE VISIBLE!")
    logging.warning("⚠️ Warning test - this should definitely be visible")
    
    # Specifically configure loggers for context management with welcome logs
    mcp_context_logger = logging.getLogger('mcp_context_tracker')
    context_manager_logger = logging.getLogger('context_manager')
    
    mcp_context_logger.info("🎯 MCP Context Tracker logging activated - tool calls will be tracked")
    context_manager_logger.info("📊 Context Manager logging activated - cleaning operations will be logged")
    
    # Console test to verify immediate visibility
    setup_logger.debug("🔥 Console logging configured successfully")
    
    # Create a simple test logger to verify console output
    test_logger = logging.getLogger('langgraph_console_test')
    test_logger.setLevel(logging.INFO)
    test_logger.info("🚀 CONSOLE TEST: This should appear immediately in your terminal!")

# Setup logging immediately
setup_debug_logging()

# Import dynamic prompt system - NO MORE STATIC TEMPLATES!
from prompt_templates import (
    inject_dynamic_context,
    generate_phase_todos,
    generate_phase_context,
    get_tool_context,
    generate_orchestrator_context,
    generate_all_phase_contexts
)
from prompt_config import (
    PhaseType,
    get_phase_config,
    get_tools_for_phase,
    validate_phase_completion,
    get_current_phase_config,
    get_next_phase,
    get_transition_requirements,
    get_phase_summary
)
# Keep optimization stats for reporting only
from optimized_prompts import OPTIMIZATION_STATS

# Import compatibility system
from tool_compatibility import apply_tool_compatibility_fixes, setup_compatibility_logging
from model_compatibility import (
    detect_model_from_environment, 
    should_apply_compatibility_fixes,
    print_model_compatibility_report,
    default_registry
)

# Import MCP wrapper for automatic cleaning
from mcp_wrapper import wrap_existing_mcp_tools

# Import compact integration for automatic context management
from compact_integration import CompactIntegration

# Import simplified agent factory for specialized sub-agents
from simplified_agent_factory import (
    SimplifiedAgentFactory,
    create_simplified_factory
)

# Import LLM compression system for automatic hook integration
try:
    from llm_compression import LLMCompressor, CompressionConfig, CompressionStrategy
    from context_hooks import ContextHookManager, CompressionHook, HookType
    from enhanced_compact_integration import EnhancedCompactIntegration
    from config_loader import get_trigger_config, get_context_management_config, print_config_summary
    LLM_COMPRESSION_AVAILABLE = True
    init_logger.info("✅ LLM Compression system available")
except ImportError as e:
    init_logger.warning(f"⚠️ LLM Compression system not available: {e}")
    LLM_COMPRESSION_AVAILABLE = False

# Model configuration from environment
DEFAULT_MODEL = os.getenv("DEEPAGENTS_MODEL", None)  # None = usa Claude default

# Setup compatibility system
setup_compatibility_logging(level="INFO")

# Detect and configure model compatibility
detected_model = detect_model_from_environment() or DEFAULT_MODEL or "claude-3.5-sonnet"
ENABLE_COMPATIBILITY_FIXES = should_apply_compatibility_fixes(detected_model, default_registry)

init_logger.info("🔧 Model Compatibility Configuration:")
init_logger.info(f"🤖 Detected/Configured model: {detected_model}")
init_logger.info(f"🛡️  Compatibility fixes enabled: {ENABLE_COMPATIBILITY_FIXES}")

# Print detailed compatibility report if fixes are enabled
if ENABLE_COMPATIBILITY_FIXES:
    print_model_compatibility_report(detected_model, default_registry)

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    init_logger.warning("langchain-mcp-adapters not available. Install with: pip install langchain-mcp-adapters")


# ============================================================================
# MCP CLIENT CONFIGURATION AND TOOL LOADING
# ============================================================================

async def load_fairmind_mcp_tools() -> Tuple[List[Any], Optional[Any], Optional[CompactIntegration]]:
    """
    Load MCP tools from the fairmind MCP server using LangChain MCP adapters.
    
    Returns:
        Tuple of (tools, mcp_wrapper, compact_integration)
        Falls back to demo tools if MCP server is not available.
    """
    if not MCP_AVAILABLE:
        mcp_logger = logging.getLogger('mcp_tools')
        mcp_logger.warning("⚠️ MCP adapters not available, using fallback tools")
        return get_fallback_tools(), None, None
    
    try:
        # Configure fairmind MCP server connection using HTTP streamable transport
        fairmind_server_config = {
            "fairmind": {
                "url": os.getenv("FAIRMIND_MCP_URL", "https://project-context.mindstream.fairmind.ai/mcp/mcp/"),
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {os.getenv('FAIRMIND_MCP_TOKEN', '')}",
                    "Content-Type": "application/json"
                }
            }
        }
        
        print("🔌 Connecting to fairmind MCP server...")
        client = MultiServerMCPClient(fairmind_server_config)
        
        # Load all available tools from the MCP server
        tools = await client.get_tools()
        
        print(f"✅ Loaded {len(tools)} MCP tools from fairmind server")
        
        # Filter for relevant fairmind tools
        fairmind_tools = [
            tool for tool in tools 
            if hasattr(tool, 'name') and any(
                prefix in tool.name for prefix in [
                    'General_list_projects',
                    'General_list_user_attachments',
                    'General_get_document_content',
                    'General_rag_retrieve_documents',
                    'Studio_list_needs',
                    'Studio_get_need',
                    'Studio_list_user_stories',
                    'Studio_get_user_story',
                    'Code_list_repositories',
                    'Code_get_directory_structure',
                    'Code_find_relevant_code_snippets',
                    'Code_get_file',
                    'Code_find_usages'
                ]
            )
        ]
        
        print(f"🎯 Found {len(fairmind_tools)} relevant fairmind tools")
        
        # Wrap MCP tools with auto-cleaning functionality
        print("🧹 Applying MCP auto-cleaning wrapper...")
        wrapped_tools, wrapper = wrap_existing_mcp_tools(fairmind_tools)
        
        # Create compact integration for automatic context management
        print("📦 Initializing automatic context compaction...")
        compact_integration = CompactIntegration(wrapper.context_manager, wrapper)
        
        print(f"✅ MCP tools wrapped with auto-cleaning - {len(wrapped_tools)} tools ready")
        print("✅ Automatic context compaction initialized")
        return wrapped_tools, wrapper, compact_integration
        
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("🔄 Falling back to demo tools")
        
        # EVEN FOR DEMO TOOLS: Create MCP wrapper to test logging functionality
        print("🧹 Creating MCP wrapper for demo tools to test logging system...")
        demo_tools = get_fallback_tools()
        wrapped_demo_tools, wrapper = wrap_existing_mcp_tools(demo_tools)
        
        print(f"✅ Demo tools wrapped for testing - {len(wrapped_demo_tools)} tools ready")
        print("⚠️ Using demo tools (no real MCP connection) but MCP wrapper active for testing")
        
        return wrapped_demo_tools, wrapper, None


def get_fallback_tools() -> List[Any]:
    """
    Fallback tools when MCP server is not available.
    These provide demo functionality with mock data.
    """
    from langchain_core.tools import tool
    
    @tool
    def list_projects_demo() -> Dict[str, Any]:
        """Demo: List available projects (fallback when MCP unavailable)."""
        return {
            "status": "demo_mode",
            "message": "MCP server not available - using demo data",
            "projects": [
                {"project_id": "demo_ecommerce", "name": "E-commerce Platform"},
                {"project_id": "demo_banking", "name": "Mobile Banking App"},
                {"project_id": "demo_ai", "name": "AI Assistant Platform"}
            ]
        }
    
    @tool
    def search_code_demo(project_id: str, query: str) -> Dict[str, Any]:
        """Demo: Search code using natural language (fallback when MCP unavailable)."""
        return {
            "status": "demo_mode",
            "message": f"MCP server not available - demo search for: {query}",
            "project_id": project_id,
            "results": [
                {
                    "file_path": f"src/components/{query.lower().replace(' ', '_')}.py",
                    "content_preview": f"# Demo code for {query}",
                    "line_start": 1,
                    "line_end": 10
                }
            ]
        }
    
    @tool  
    def get_project_overview_demo(project_id: str) -> Dict[str, Any]:
        """Demo: Get project overview (fallback when MCP unavailable)."""
        return {
            "status": "demo_mode",
            "message": "MCP server not available - using demo project data",
            "project_id": project_id,
            "needs": [{"need_id": "N1", "title": "User Authentication"}],
            "requirements": [{"req_id": "R1", "title": "JWT Security"}],
            "user_stories": [{"story_id": "US1", "title": "User Login"}],
            "tasks": [{"task_id": "T1", "title": "Implement Auth API"}]
        }
    
    return [list_projects_demo, search_code_demo, get_project_overview_demo]


# ============================================================================
# DEEP PLANNING MCP TOOL INITIALIZATION
# ============================================================================

def initialize_deep_planning_mcp_tools():
    """
    Initialize Deep Planning Agent with MCP tools. This function handles both async MCP loading
    and fallback to demo tools when MCP is not available.
    
    Returns:
        Tuple of (tools, mcp_wrapper, compact_integration)
    """
    try:
        # Try to load MCP tools asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mcp_tools, mcp_wrapper, compact_integration = loop.run_until_complete(load_fairmind_mcp_tools())
        loop.close()
        return mcp_tools, mcp_wrapper, compact_integration
    except Exception as e:
        print(f"⚠️ Failed to initialize MCP tools: {e}")
        print("🔄 Using fallback demo tools")
        return get_fallback_tools(), None, None


# Initialize MCP tools and context management systems
print("🏗️ Initializing Deep Planning Agent with MCP integration...")
deep_planning_tools, mcp_wrapper, compact_integration = initialize_deep_planning_mcp_tools()

# Apply compatibility fixes to tools if needed
if ENABLE_COMPATIBILITY_FIXES:
    print("🔧 Applying compatibility fixes to tools...")
    # Note: MCP tools don't need fixing, but deepagents built-in tools will be fixed in create_deep_agent
    print("✅ MCP tools prepared (fixes will be applied to deepagents built-in tools)")


# ============================================================================
# DYNAMIC PROMPT HELPER FUNCTIONS - PHASE MANAGEMENT SYSTEM
# ============================================================================

def format_todos_for_prompt(todos: List[Dict[str, Any]]) -> str:
    """Format dynamic TODOs for inclusion in prompts."""
    if not todos:
        return "No specific tasks generated"
    
    formatted = []
    for todo in todos:
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(todo.get("status", "pending"), "📋")
        formatted.append(f"{status_emoji} {todo['content']}")
    
    return "\n".join(formatted)

def format_outputs_list(outputs: List[str]) -> str:
    """Format required outputs list for prompts."""
    if not outputs:
        return "No specific output required"
    return "\n".join([f"📄 {output}" for output in outputs])

def format_validation_rules(rules) -> str:
    """Format validation rules for prompts."""
    if not rules:
        return "No specific validation criteria"
    
    formatted = []
    for rule in rules:
        if hasattr(rule, 'description'):
            status = "✅" if rule.required else "⚠️"
            formatted.append(f"{status} {rule.description}")
        else:
            formatted.append(f"📋 {str(rule)}")
    
    return "\n".join(formatted)

def format_interaction_points(interaction_points: List[str]) -> str:
    """Format human interaction points for prompts."""
    if not interaction_points:
        return "No human interaction required"
    return "\n".join([f"👤 {point}" for point in interaction_points])

def format_validation_result(validation_result: Dict[str, Any]) -> str:
    """Format validation result for orchestrator prompt."""
    if not validation_result:
        return "Validation not available"
    
    if validation_result.get('valid', False):
        return f"✅ Phase validated ({len(validation_result.get('completed_validations', []))} checks completed)"
    else:
        errors = validation_result.get('errors', [])
        return f"❌ Validation failed: {', '.join(errors) if errors else 'Unknown errors'}"

def validate_and_transition_phase(current_phase: str, state: Dict[str, Any], tools: List[Any]) -> Tuple[bool, str, List[str]]:
    """
    Phase Management: Validate current phase completion and determine transition.
    Uses dynamic validation from prompt_config.py!
    
    Args:
        current_phase: Current phase name
        state: Project state
        tools: Available tools
        
    Returns:
        Tuple of (can_transition, next_phase, missing_requirements)
    """
    try:
        phase_type = PhaseType(current_phase)
    except ValueError:
        return False, "", [f"Invalid phase: {current_phase}"]
    
    # Create factory for validation
    agent_factory = create_simplified_factory(tools)
    
    # Use factory's validation method
    can_transition, next_phase, missing_reqs = agent_factory.validate_phase_transition(
        current_phase, state
    )
    
    if can_transition:
        print(f"✅ Phase {current_phase} validation passed! Ready for transition to {next_phase}")
    else:
        print(f"❌ Phase {current_phase} validation failed. Missing: {missing_reqs}")
    
    return can_transition, next_phase, missing_reqs

def get_phase_progress_report(state: Dict[str, Any], tools: List[Any]) -> Dict[str, Any]:
    """
    Progress Dashboard: Generate comprehensive phase progress report.
    
    Args:
        state: Current project state
        tools: Available tools
        
    Returns:
        Complete progress report with dynamic analysis
    """
    agent_factory = create_simplified_factory(tools)
    report = agent_factory.get_phase_summary_report(state)
    
    # Add dynamic context analysis
    current_phase = state.get("current_phase", "unknown")
    if current_phase != "unknown":
        try:
            phase_type = PhaseType(current_phase)
            current_agent_config = agent_factory.create_agent_from_phase(phase_type, state)
            
            report["current_phase_details"] = {
                "agent_name": current_agent_config["agent_name"],
                "emoji": current_agent_config["emoji"],
                "dynamic_todos_count": len(current_agent_config["dynamic_todos"]),
                "relevant_tools_count": len(current_agent_config["relevant_tools"]),
                "requires_user_input": current_agent_config["requires_user_input"],
                "requires_approval": current_agent_config["requires_approval"]
            }
        except Exception as e:
            report["current_phase_details"] = {"error": f"Failed to analyze current phase: {e}"}
    
    return report

def auto_advance_phase_if_ready(state: Dict[str, Any], tools: List[Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Auto Progression: Automatically advance to next phase if current is completed.
    
    Args:
        state: Current project state
        tools: Available tools
        
    Returns:
        Tuple of (phase_advanced, updated_state)
    """
    current_phase = state.get("current_phase", "unknown")
    
    if current_phase == "unknown" or current_phase == "complete":
        return False, state
    
    # Check if current phase can transition
    can_transition, next_phase, missing_reqs = validate_and_transition_phase(
        current_phase, state, tools
    )
    
    if not can_transition:
        print(f"🔄 Auto-advance blocked. Missing requirements: {missing_reqs}")
        return False, state
    
    # Update state for next phase
    updated_state = state.copy()
    updated_state["current_phase"] = next_phase
    
    # Add to completed phases
    completed_phases = updated_state.get("completed_phases", [])
    if current_phase not in completed_phases:
        completed_phases.append(current_phase)
        updated_state["completed_phases"] = completed_phases
    
    # Update context summary
    updated_state["context_summary"] = f"Advanced from {current_phase} to {next_phase}"
    
    print(f"🔄 Auto Progression: Advanced from {current_phase} → {next_phase}")
    return True, updated_state

# ============================================================================
# AUTOMATIC CONTEXT COMPACTION FUNCTIONS
# ============================================================================

def check_and_compact_if_needed(messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Check if automatic compaction is needed and perform it if necessary.
    
    Args:
        messages: Current conversation messages
        context: Additional context for compaction
    
    Returns:
        Tuple of (compacted_messages, compaction_summary)
    """
    if compact_integration is None:
        # No compaction available, return original messages
        return messages, None
    
    try:
        # Check if compaction should be triggered
        should_compact, trigger_type, metrics = compact_integration.should_trigger_compaction(messages)
        
        if should_compact:
            print(f"📦 Context compaction triggered: {trigger_type.value}")
            print(f"📊 Context metrics: {metrics.utilization_percentage:.1f}% utilization, {metrics.mcp_noise_percentage:.1f}% MCP noise")
            
            # Perform automatic compaction
            compacted_messages, summary = compact_integration.perform_automatic_compaction(messages, context)
            
            print(f"✅ Context compacted: {summary.total_reduction_percentage:.1f}% reduction")
            print(f"📝 Summary: {len(summary.summary_content)} chars generated")
            
            return compacted_messages, summary.summary_content
        else:
            # No compaction needed
            return messages, None
            
    except Exception as e:
        print(f"⚠️ Compaction check failed: {e}")
        # Return original messages if compaction fails
        return messages, None

def get_compaction_metrics() -> Optional[Dict[str, Any]]:
    """Get current compaction system metrics."""
    if compact_integration is None:
        return None
    
    try:
        return {
            "compaction_history_count": len(compact_integration.compact_history),
            "last_compaction": compact_integration.compact_history[-1].timestamp if compact_integration.compact_history else None,
            "total_reductions": [s.total_reduction_percentage for s in compact_integration.compact_history],
            "mcp_wrapper_stats": mcp_wrapper.get_statistics() if mcp_wrapper else None
        }
    except Exception as e:
        print(f"⚠️ Failed to get compaction metrics: {e}")
        return None


# ============================================================================
# SUB-AGENT CONFIGURATIONS FOR 4-PHASE DEEP PLANNING
# ============================================================================

# ============================================================================
# OPTIMIZED SUB-AGENT CREATION WITH DYNAMIC PROMPTS
# ============================================================================

def create_optimized_subagent(agent_name: str, phase: str, tools: List[Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a sub-agent configuration with FULLY DYNAMIC prompts from prompt_config.
    NO MORE STATIC TEMPLATES - Everything generated from phase configuration!
    
    Args:
        agent_name: Name of the agent to create (matches phase config agent names)
        phase: Current phase name
        tools: Available tools list
        state: Current agent state for context injection
    
    Returns:
        Dictionary containing completely dynamic agent configuration
    """
    # Get dynamic configuration from prompt_config (not static AGENT_CONFIGS!)
    phase_type = PhaseType(phase) if phase in [e.value for e in PhaseType] else None
    if not phase_type:
        raise ValueError(f"Invalid phase: {phase}")
    
    phase_config = get_phase_config(phase_type)
    if not phase_config:
        raise ValueError(f"Phase configuration not found for: {phase}")
    
    # Generate dynamic context for this specific phase and state
    phase_context = generate_phase_context(phase, state)
    
    # Generate dynamic TODOs based on current context
    dynamic_todos = generate_phase_todos(phase, phase_context)
    
    # Generate dynamic tool context with filtering
    tool_context = get_tool_context(phase, tools)
    relevant_tools = get_tools_for_phase(phase_type, tools)
    
    # Create COMPLETELY DYNAMIC prompt template
    dynamic_prompt_template = f"""
You are the {phase_config.agent_name} - {phase_config.emoji} {phase_config.name}

## Your Mission
{phase_config.goal}

## Project Context
- Project: {{project_name}} ({{project_type}})
- Domain: {{domain}}
- Focus: {{focus_area}}
- Current phase: {phase} ({phase_config.completion_weight}% completion)

## Your Dynamic Tasks
{format_todos_for_prompt(dynamic_todos)}

## Available Tools ({tool_context['tool_count']} filtered for this phase)
{tool_context['tool_categories']}
Focus: {tool_context['phase_objectives']}

## Required Outputs
{format_outputs_list(phase_config.required_outputs)}

## Success Criteria
{format_validation_rules(phase_config.validation_rules)}

## Human Interactions
{format_interaction_points(phase_config.interaction_points) if phase_config.requires_user_input else "No interaction required"}

Estimated duration: {phase_config.duration_estimate}
"""
    
    # Inject dynamic context into the template
    final_prompt = inject_dynamic_context(
        dynamic_prompt_template,
        phase,
        state,
        relevant_tools
    )
    
    return {
        "name": phase_config.name,
        "description": phase_config.goal,
        "prompt": final_prompt,
        "tools": [getattr(tool, 'name', str(tool)) for tool in relevant_tools],
        "phase": phase,
        "requires_user_input": phase_config.requires_user_input,
        "requires_approval": phase_config.requires_approval,
        "validation_criteria": [rule.description for rule in phase_config.validation_rules],
        "outputs": phase_config.required_outputs,
        "dynamic_todos": dynamic_todos,
        "tool_context": tool_context,
        "phase_config": phase_config
    }


def create_dynamic_subagents(tools: List[Any], current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Create ALL sub-agents using the dynamic agent factory system.
    NO MORE MANUAL CREATION - Everything automated from phase configurations!
    
    Args:
        tools: Available tools list
        current_state: Current agent state for context injection
    
    Returns:
        List of completely dynamically configured sub-agents
    """
    # Create the dynamic agent factory system
    agent_factory = create_simplified_factory(tools)
    
    # Validate factory setup
    validation_report = validate_factory_setup(agent_factory)
    if not validation_report['factory_valid']:
        print(f"⚠️ Factory validation failed: {validation_report['errors']}")
        print("🔄 Falling back to direct phase creation...")
        
        # Fallback to direct creation if factory fails
        return create_fallback_subagents(tools, current_state)
    
    # Use factory to create all agents dynamically
    dynamic_agents = agent_factory.create_all_phase_agents(current_state)
    
    print(f"🏭 Agent Factory created {len(dynamic_agents)} dynamic sub-agents!")
    print(f"📊 Phase coverage: {[agent['phase'] for agent in dynamic_agents]}")
    print(f"⚙️ All agents generated from prompt_config.py with real-time context")
    
    return dynamic_agents

def create_fallback_subagents(tools: List[Any], current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fallback method for creating subagents if factory fails.
    """
    subagents = []
    
    for phase_type in PhaseType:
        if phase_type == PhaseType.COMPLETE:
            continue
            
        try:
            phase_config = get_phase_config(phase_type)
            if not phase_config:
                continue
                
            # Generate agent using direct method
            dynamic_agent = create_optimized_subagent(
                phase_config.agent_name,
                phase_type.value,
                tools, 
                current_state
            )
            
            subagents.append(dynamic_agent)
            
        except Exception as e:
            print(f"⚠️ Failed to create agent for {phase_type.value}: {e}")
            continue
    
    print(f"🔄 Fallback created {len(subagents)} agents")
    return subagents


def generate_optimized_main_prompt(current_phase: str, state: Dict[str, Any], tools: List[Any]) -> str:
    """
    Generate FULLY DYNAMIC main orchestrator prompt - NO MORE STATIC TEMPLATES!
    Everything generated from current phase configuration and state.
    
    Args:
        current_phase: Current phase name
        state: Current agent state
        tools: Available tools list
    
    Returns:
        Completely dynamically generated main prompt
    """
    # Get current phase configuration
    phase_type = PhaseType(current_phase) if current_phase in [e.value for e in PhaseType] else None
    current_config = get_phase_config(phase_type) if phase_type else None
    
    # Generate orchestrator-specific context
    orchestrator_context = generate_orchestrator_context(current_phase, state, tools)
    
    # Create DYNAMIC orchestrator template (NO MORE STATIC!)
    dynamic_orchestrator_template = f"""
You are the Deep Planning Orchestrator - 4-phase development planning coordinator.

## Process Status
- Current phase: {{current_phase}} ({{completion_percentage}}% completed)
- Context: {{context_summary}}
- Project: {{project_id}}
- Completed phases: {{completed_phases}}

## Current Phase: {current_config.emoji if current_config else '🔧'} {current_config.name if current_config else current_phase.title()}
{f'Goal: {current_config.goal}' if current_config else ''}
{f'Required agent: {current_config.agent_name}' if current_config else ''}
{f'Human interaction: {'Yes' if current_config and current_config.requires_user_input else 'No'}' if current_config else ''}
{f'Approval required: {'Yes' if current_config and current_config.requires_approval else 'No'}' if current_config else ''}

## Your Role
Coordinate sub-agents through structured phases, ensuring smooth transitions and completeness validation.

## Available Tools
{{tool_count}} total tools, {{phase_objectives}} for the current phase

## Recommended Action
{{recommended_next_action}}

## Transition Criteria
{get_transition_requirements(phase_type) if phase_type else ['Unknown phase']}

## Current Validation
{{validation_criteria}}

Deploy the appropriate sub-agent or manage the transition to the next phase.
"""
    
    # Add validation status to context
    if phase_type:
        validation_result = validate_phase_completion(phase_type, state)
        orchestrator_context['validation_status'] = format_validation_result(validation_result)
        orchestrator_context['validation_criteria'] = '\n'.join(
            [f"- {rule.description}" for rule in current_config.validation_rules] if current_config else ["No criteria"]
        )
    
    # Inject complete dynamic context
    final_prompt = inject_dynamic_context(
        dynamic_orchestrator_template,
        current_phase,
        state,
        tools
    )
    
    return final_prompt


def print_optimization_report():
    """
    Print a report showing the optimization improvements achieved.
    """
    stats = OPTIMIZATION_STATS
    
    print("\n" + "="*60)
    print("🚀 DEEP PLANNING AGENT OPTIMIZATION REPORT")
    print("="*60)
    
    print(f"📊 Prompt Length Reduction:")
    print(f"   Original main prompt: {stats['original_main_prompt_lines']} lines")
    print(f"   Optimized main prompt: {stats['optimized_main_prompt_lines']} lines")
    print(f"   Reduction: {stats['reduction_percentage']}%")
    
    print(f"\n📈 Overall Optimization:")
    print(f"   Total original lines: {stats['total_original_lines']} lines")
    print(f"   Total optimized lines: {stats['total_optimized_lines']} lines")
    print(f"   Overall reduction: {stats['overall_reduction_percentage']}%")
    
    print(f"\n🏗️  Architecture Improvements:")
    print(f"   Modular prompts: {stats['modular_prompts_count']}")
    print(f"   Template variables: {stats['template_variables_count']}")
    print(f"   Single responsibility: {stats['single_responsibility_achieved']}")
    print(f"   Dynamic context: {stats['dynamic_context_injection']}")
    
    print(f"\n✨ Key Benefits:")
    print(f"   • Better LLM focus through shorter, targeted prompts")
    print(f"   • Dynamic context adaptation to project state")
    print(f"   • Elimination of repetitive instructions")
    print(f"   • Modular architecture for easier maintenance")
    print(f"   • Template-based system for consistency")
    
    print("="*60 + "\n")


# ============================================================================
# MAIN DEEP PLANNING AGENT CONFIGURATION
# ============================================================================

# ============================================================================
# OPTIMIZED AGENT CREATION AND INITIALIZATION
# ============================================================================

def create_optimized_deep_planning_agent(initial_state: Dict[str, Any] = None, enable_llm_compression: bool = True) -> Any:
    """
    Create the deep planning agent with optimized, dynamic prompts and optional LLM compression.
    
    Args:
        initial_state: Initial state for context generation
        enable_llm_compression: Enable automatic LLM compression hooks
    
    Returns:
        Configured deep planning agent with optional compression hooks
    """
    # STRATEGIC LOGGING: This function is called by LangGraph
    main_logger = logging.getLogger('deep_planning_main')
    main_logger.info("🏗️ STARTING: create_optimized_deep_planning_agent() - LangGraph will see this!")
    main_logger.info(f"🔧 Parameters: enable_llm_compression={enable_llm_compression}")
    
    # Initialize default state
    if initial_state is None:
        initial_state = {
            "current_phase": "investigation",
            "project_id": "unknown",
            "completed_phases": [],
            "context_summary": "Initial deep planning session",
            "files": {},
            "project_domain": "software development",
            "project_type": "application"
        }
    
    # Generate dynamic main prompt
    current_phase = initial_state.get("current_phase", "investigation")
    main_logger.info(f"📝 GENERATING: Dynamic main prompt for phase: {current_phase}")
    
    optimized_main_prompt = generate_optimized_main_prompt(
        current_phase, 
        initial_state, 
        deep_planning_tools
    )
    main_logger.info(f"✅ GENERATED: Main prompt ({len(optimized_main_prompt)} chars)")
    
    # Create dynamic sub-agents
    main_logger.info("🤖 CREATING: Dynamic sub-agents")
    optimized_subagents = create_dynamic_subagents(deep_planning_tools, initial_state)
    main_logger.info(f"✅ CREATED: {len(optimized_subagents)} sub-agents")
    
    # Setup LLM compression if available and enabled
    enhanced_compact_integration = None
    if enable_llm_compression and LLM_COMPRESSION_AVAILABLE and compact_integration:
        print("🧠 Setting up LLM compression with POST_TOOL hooks...")
        
        # Load configuration from YAML
        trigger_config = get_trigger_config()
        print(f"📋 Using triggers from context_config.yaml:")
        print(f"   📏 Context window: {trigger_config.max_context_window:,} tokens")
        print(f"   🎯 Standard trigger: {trigger_config.trigger_threshold:.0%}")
        print(f"   🔧 POST_TOOL trigger: {trigger_config.post_tool_threshold:.0%}")
        print(f"   🔇 MCP noise trigger: {trigger_config.mcp_noise_threshold:.0%}")
        
        # Get the same model that will be used by the agent
        from deepagents.model import get_model
        agent_model = get_model(DEFAULT_MODEL)
        
        # Create LLM compressor using unified config
        from unified_config import get_model_config, get_performance_config
        model_cfg = get_model_config()
        perf_cfg = get_performance_config()
        
        compression_config = CompressionConfig(
            strategy=CompressionStrategy.ADAPTIVE,
            target_reduction_percentage=65.0,
            max_output_tokens=model_cfg.max_output_tokens,  # From unified config
            preserve_last_n_messages=trigger_config.preserve_last_n_messages,
            enable_fallback=trigger_config.enable_fallback,
            compression_timeout=perf_cfg.compression_timeout  # From unified config
        )
        
        llm_compressor = LLMCompressor(
            model=agent_model,
            config=compression_config,
            context_manager=compact_integration.context_manager
        )
        
        # Create enhanced compact integration with YAML config
        enhanced_config = {
            "prefer_llm_compression": True,
            "llm_threshold": trigger_config.llm_compression_threshold,
            "template_threshold": trigger_config.trigger_threshold,
            "force_llm_threshold": trigger_config.force_llm_threshold,
            "min_reduction_threshold": trigger_config.min_reduction_threshold,
            "enable_hybrid_mode": True
        }
        
        enhanced_compact_integration = EnhancedCompactIntegration(
            context_manager=compact_integration.context_manager,
            mcp_wrapper=mcp_wrapper,
            llm_compressor=llm_compressor,
            config=enhanced_config
        )
        
        print(f"✅ LLM compression configured with {agent_model.__class__.__name__}")
        print(f"   🎯 Strategy: {compression_config.strategy.value}")
        print(f"   📉 Target reduction: {compression_config.target_reduction_percentage}%")
        print(f"   ⚙️ Config source: context_config.yaml")
    
    # Final Assembly: Create the agent with completely dynamic prompts
    main_logger.info("🏎️ ASSEMBLING: Final agent with dynamic prompts")
    main_logger.info(f"🔧 Using model: {DEFAULT_MODEL}")
    main_logger.info(f"🛠️ Tools count: {len(deep_planning_tools)}")
    main_logger.info("🎯 CALLBACK: Adding DeepPlanningCallbackHandler for execution visibility")
    
    agent = create_compatible_deep_agent(
        tools=deep_planning_tools,
        instructions=optimized_main_prompt,
        model=DEFAULT_MODEL,
        subagents=optimized_subagents,
        enable_planning_approval=True,
        checkpointer="memory",
        # Pass compression integration for hook setup
        _enhanced_compact_integration=enhanced_compact_integration,
        # Add callback handler for execution logging
        _callback_handler=deep_planning_callback,
        # Pass MCP wrapper for StructuredTool re-wrapping
        _mcp_wrapper=mcp_wrapper
    )
    main_logger.info("✅ ASSEMBLED: Base agent created successfully")
    
    # Add validation capabilities to the agent
    main_logger.info("⚡ ENHANCING: Adding validation capabilities")
    agent._dynamic_factory = create_dynamic_agent_factory(deep_planning_tools)
    agent._validate_phase_transition = lambda phase, state: validate_and_transition_phase(phase, state, deep_planning_tools)
    agent._get_progress_report = lambda state: get_phase_progress_report(state, deep_planning_tools)
    agent._auto_advance_phase = lambda state: auto_advance_phase_if_ready(state, deep_planning_tools)
    
    main_logger.info("🏁 COMPLETED: Deep planning agent creation finished!")
    print("🤖 Agent equipped with dynamic validation and auto-progression!")
    
    return agent

# ============================================================================
# DEEP PLANNING AGENT CREATION WITH FULL INTEGRATION
# ============================================================================

def create_compatible_deep_agent(*args, **kwargs):
    """
    Create a deep agent with automatic compatibility fixes and optional LLM compression hooks.
    
    This function wraps the original create_deep_agent and applies compatibility
    fixes to the built-in tools before agent creation. It also sets up automatic
    compression hooks if enhanced_compact_integration is provided.
    """
    # STRATEGIC LOGGING: This function is called during agent creation
    compat_logger = logging.getLogger('deep_planning_compat')
    compat_logger.info("🔧 STARTING: create_compatible_deep_agent() - Setting up compatibility")
    
    # Import here to avoid circular imports and access to built-in tools
    from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
    
    # Extract compression integration, callback handler, and MCP wrapper from kwargs
    enhanced_compact_integration = kwargs.pop('_enhanced_compact_integration', None)
    callback_handler = kwargs.pop('_callback_handler', None)
    mcp_wrapper = kwargs.pop('_mcp_wrapper', None)
    
    compat_logger.info(f"🧠 LLM Compression available: {enhanced_compact_integration is not None}")
    compat_logger.info(f"🎯 Callback Handler provided: {callback_handler is not None}")
    
    if ENABLE_COMPATIBILITY_FIXES:
        compat_logger.info("🛡️ APPLYING: Compatibility fixes to built-in tools")
        print("🛡️  Applying compatibility fixes to built-in tools...")
        
        # Create list of built-in tools
        built_in_tools = [write_todos, write_file, read_file, ls, edit_file]
        
        # Add review_plan if planning approval is enabled
        if kwargs.get('enable_planning_approval', False):
            built_in_tools.append(review_plan)
            compat_logger.info("📋 ADDED: review_plan tool for planning approval")
        
        compat_logger.info(f"🔧 FIXING: {len(built_in_tools)} built-in tools for model: {detected_model}")
        
        # Apply compatibility fixes
        fixed_built_in_tools = apply_tool_compatibility_fixes(built_in_tools, detected_model)
        
        # Monkey patch the tools module to use our fixed tools
        import deepagents.tools as tools_module
        for i, original_tool in enumerate(built_in_tools):
            tool_name = getattr(original_tool, 'name', getattr(original_tool, '__name__', None))
            if tool_name and hasattr(tools_module, tool_name):
                setattr(tools_module, tool_name, fixed_built_in_tools[i])
        
        compat_logger.info("✅ PATCHED: Built-in tools with compatibility fixes")
        print("✅ Built-in tools patched with compatibility fixes")
    else:
        compat_logger.info("⏭️ SKIPPED: Compatibility fixes (not needed for this model)")
    
    # Prepare for callback handler configuration (deepagents doesn't support callbacks param)
    if callback_handler:
        compat_logger.info("🎯 PREPARING: Callback handler for post-creation configuration")
        # Remove callbacks from kwargs since deepagents doesn't support it
        if 'callbacks' in kwargs:
            kwargs.pop('callbacks')
            compat_logger.info("🔧 REMOVED: callbacks parameter (deepagents doesn't support it)")
        
        # Set environment for callback propagation
        import os
        os.environ['LANGCHAIN_CALLBACKS_ENABLED'] = 'true'
        compat_logger.info("🌐 SET: Environment configured for callback propagation")
    
    # Create the agent normally
    compat_logger.info("🏗️ CREATING: Base deep agent with deepagents library")
    compat_logger.info(f"🔧 Agent kwargs: {list(kwargs.keys())}")
    agent = create_deep_agent(*args, **kwargs)
    compat_logger.info("✅ CREATED: Base deep agent successfully")
    
    # CRITICAL FIX: Re-wrap the agent's tools after creation
    # deepagents might have extracted original tools, so re-apply wrappers
    try:
        compat_logger.info(f"🔍 AGENT INSPECTION: Agent type: {type(agent)}")
        compat_logger.info(f"🔍 AGENT ATTRIBUTES: {[attr for attr in dir(agent) if not attr.startswith('_')]}")
        
        # Check various possible tool locations
        tool_locations = ['tools', 'graph', 'nodes', '_tools', 'executor', 'runner']
        for location in tool_locations:
            if hasattr(agent, location):
                attr_value = getattr(agent, location)
                compat_logger.info(f"🔍 FOUND: agent.{location} = {type(attr_value)} with {len(str(attr_value))} chars")
        
        # CRITICAL NEW APPROACH: Re-wrap StructuredTools after creation
        if 'tools' in kwargs:
            original_wrapped_tools = kwargs['tools']
            
            # Check if we have an MCP wrapper available to re-wrap StructuredTools
            if mcp_wrapper is not None:
                compat_logger.info("🔧 APPLYING: StructuredTool re-wrapping with MCP wrapper")
                
                # Re-wrap any StructuredTools that were created
                for i, tool in enumerate(original_wrapped_tools):
                    if hasattr(tool, '_schema') or 'StructuredTool' in str(type(tool)):
                        tool_name = getattr(tool, 'name', f"tool_{i}")
                        is_mcp = mcp_wrapper._is_mcp_tool(tool_name)
                        compat_logger.info(f"🔧 CHECKING: Tool {i} name='{tool_name}' is_mcp={is_mcp}")
                        
                        # Force wrap ALL StructuredTools for now to test - USE LOGGING FOR RELIABILITY
                        compat_logger.info(f"🔧 FORCE WRAPPING StructuredTool: {tool_name}")
                        
                        try:
                            # This will trigger the new StructuredTool wrapping logic
                            compat_logger.info(f"🔧 CALLING: mcp_wrapper.wrap_tool() for {tool_name}")
                            re_wrapped = mcp_wrapper.wrap_tool(tool, tool_name)
                            compat_logger.info(f"🔧 RETURNED: wrap_tool() succeeded for {tool_name}")
                            
                            original_wrapped_tools[i] = re_wrapped
                            compat_logger.info(f"✅ FORCE WRAPPED: {tool_name} successfully replaced in list")
                            
                        except Exception as e:
                            compat_logger.error(f"❌ EXCEPTION in wrap_tool() for {tool_name}: {type(e).__name__}: {e}")
                            compat_logger.error(f"❌ TOOL TYPE: {type(tool)}")
                            compat_logger.error(f"❌ TOOL ATTRS: {[attr for attr in dir(tool) if not attr.startswith('_')]}")
                            # Continue with next tool instead of crashing
                        
                compat_logger.info("✅ STRUCTURED TOOLS: Re-wrapped with MCP integration")
                print("🎯 CRITICAL FIX APPLIED: StructuredTool functions now wrapped!")
            else:
                compat_logger.warning("⚠️ MCP wrapper not available for StructuredTool re-wrapping")
                    
        # If still no luck, print debug info
        if 'tools' in kwargs:
            original_wrapped_tools = kwargs['tools']
            compat_logger.info(f"📋 ORIGINAL WRAPPED TOOLS: {len(original_wrapped_tools)} tools")
            for i, tool in enumerate(original_wrapped_tools[:3]):  # Show first 3
                compat_logger.info(f"   Tool {i}: {type(tool)} - wrapped: {hasattr(tool, '__wrapped__')}")
                
    except Exception as e:
        compat_logger.warning(f"⚠️ Tool re-wrapping failed: {e}")
        import traceback
        compat_logger.warning(f"⚠️ Full error: {traceback.format_exc()}")
    
    # Setup LLM compression hooks if enhanced integration is provided
    if enhanced_compact_integration and LLM_COMPRESSION_AVAILABLE:
        print("🔗 Setting up POST_TOOL compression hooks...")
        
        try:
            # Get trigger config for printing
            hook_trigger_config = get_trigger_config()
            
            # Setup hook manager with POST_TOOL hook - configurazione automatica da YAML
            hook_manager = ContextHookManager(
                enhanced_compact_integration.llm_compressor,
                config_path="context_config.yaml"
            )
            
            # No need to manually create CompressionHook as it's created
            # automatically by ContextHookManager with YAML configuration
            
            # Wrap the agent with automatic hook execution
            agent = _wrap_agent_with_compression_hooks(agent, hook_manager, enhanced_compact_integration)
            
            print("✅ POST_TOOL compression hooks integrated")
            print(f"   🎯 Trigger threshold: {hook_trigger_config.post_tool_threshold:.0%} context utilization")
            print(f"   🔧 Using same LLM as agent for compression")
            print(f"   📋 All triggers from context_config.yaml")
            
        except Exception as e:
            compat_logger.error(f"❌ FAILED: Compression hook setup - {e}")
            print(f"⚠️ Failed to setup compression hooks: {e}")
            print("🔄 Agent running without automatic compression")
    else:
        compat_logger.info("⏭️ SKIPPED: LLM compression hooks (not available or disabled)")
    
    # Configure the callback handler on the agent itself
    if callback_handler:
        compat_logger.info("🎯 FINALIZING: Adding callback handler to agent object")
        try:
            # Try to add callback to the agent's LLM if it exists
            if hasattr(agent, 'llm') and agent.llm:
                if hasattr(agent.llm, 'callbacks'):
                    if agent.llm.callbacks is None:
                        agent.llm.callbacks = [callback_handler]
                    else:
                        agent.llm.callbacks.append(callback_handler)
                    compat_logger.info("✅ CONFIGURED: Callback added to agent.llm.callbacks")
                else:
                    compat_logger.info("⚠️ Agent LLM doesn't support callbacks directly")
            
            # Try to add to the agent itself if it supports callbacks
            if hasattr(agent, 'callbacks'):
                if agent.callbacks is None:
                    agent.callbacks = [callback_handler]
                else:
                    agent.callbacks.append(callback_handler)
                compat_logger.info("✅ CONFIGURED: Callback added to agent.callbacks")
            
            # Store callback for manual triggering if needed
            agent._deep_planning_callback = callback_handler
            compat_logger.info("✅ STORED: Callback handler stored on agent for manual access")
            
        except Exception as e:
            compat_logger.warning(f"⚠️ Could not configure callback on agent: {e}")
            compat_logger.info("🔄 Callback handler will rely on environment configuration")
    
    compat_logger.info("🏁 COMPLETED: create_compatible_deep_agent() finished successfully!")
    return agent


def wrap_agent_with_mcp_state_cleaning(agent, mcp_wrapper):
    """
    Wrap the agent to clean MCP ToolMessages in LangGraph state.
    
    This wrapper resolves the identified integration gap where the context manager
    cleans MCP responses but LangGraph saves raw ToolMessages in its state.
    
    The wrapper intercepts invoke() and cleans all MCP ToolMessages AFTER execution,
    ensuring the final state contains clean data instead of raw MCP data.
    
    Args:
        agent: The LangGraph agent to wrap
        mcp_wrapper: The MCP wrapper with cleaning functionality
    
    Returns:
        Wrapped agent that automatically cleans MCP state
    """
    if not mcp_wrapper:
        print("⚠️ No MCP wrapper provided, skipping state cleaning integration")
        return agent
    
    # Store original invoke methods
    original_invoke = agent.invoke
    original_ainvoke = agent.ainvoke if hasattr(agent, 'ainvoke') else None
    
    def cleaned_invoke(input_data, config=None, **kwargs):
        """Synchronous wrapper with MCP state cleaning."""
        # Execute the agent normally
        result = original_invoke(input_data, config, **kwargs)
        
        # Clean MCP ToolMessages in the resulting state
        if isinstance(result, dict) and "messages" in result:
            try:
                original_count = len(result["messages"])
                original_size = len(str(result["messages"])) // 4  # Rough token estimate
                
                # 🟠 MONITORING: MCP Cleaning Operation
                mcp_logger = logging.getLogger('context_manager')
                mcp_logger.info(f"🟠 MCP CLEANING ACTIVE 🧹")
                mcp_logger.info(f"📥 Pre-cleaning Messages: {original_count}")
                mcp_logger.info(f"📊 Pre-cleaning Size (est.): {original_size:,} tokens")
                
                cleaned_messages = mcp_wrapper.clean_message_list(result["messages"])
                result["messages"] = cleaned_messages
                
                cleaned_size = len(str(cleaned_messages)) // 4  # Rough token estimate
                reduction = ((original_size - cleaned_size) / original_size * 100) if original_size > 0 else 0
                
                mcp_logger.info(f"📤 Post-cleaning Messages: {len(cleaned_messages)}")
                mcp_logger.info(f"📉 Size Reduction: {reduction:.1f}% ({original_size:,} → {cleaned_size:,} tokens)")
                mcp_logger.info(f"🧹 LangGraph state cleaned: {original_count} messages processed")
                mcp_logger.info(f"✅ MCP ToolMessages now contain clean data instead of raw responses")
                
            except Exception as e:
                print(f"⚠️ Failed to clean LangGraph state: {e}")
                # Continue without cleaning if it fails
        
        return result
    
    def cleaned_ainvoke(input_data, config=None, **kwargs):
        """Asynchronous wrapper with MCP state cleaning."""
        import asyncio
        
        async def async_cleaned_invoke():
            # Execute the agent normally (asynchronously if supported)
            if original_ainvoke:
                result = await original_ainvoke(input_data, config, **kwargs)
            else:
                # Synchronous fallback if ainvoke not available
                result = original_invoke(input_data, config, **kwargs)
            
            # Clean MCP ToolMessages in the resulting state
            if isinstance(result, dict) and "messages" in result:
                try:
                    original_count = len(result["messages"])
                    cleaned_messages = mcp_wrapper.clean_message_list(result["messages"])
                    result["messages"] = cleaned_messages
                    
                    print(f"🧹 LangGraph state cleaned (async): {original_count} messages processed")
                    print(f"✅ MCP ToolMessages now contain clean data instead of raw responses")
                    
                except Exception as e:
                    print(f"⚠️ Failed to clean LangGraph state (async): {e}")
                    # Continue without cleaning if it fails
            
            return result
        
        return asyncio.create_task(async_cleaned_invoke())
    
    # Replace methods with wrapped versions
    agent.invoke = cleaned_invoke
    if original_ainvoke:
        agent.ainvoke = cleaned_ainvoke
    
    print("🔗 Agent wrapped with MCP state cleaning")
    print("📋 LangGraph ToolMessages will now contain cleaned MCP data")
    print("✅ Gap between context manager and LangGraph state resolved")
    
    return agent


def _wrap_agent_with_compression_hooks(agent, hook_manager, enhanced_compact_integration):
    """
    Wrap the agent with automatic POST_TOOL compression hooks.
    
    Intercepts agent execution to trigger compression after tool calls.
    """
    # Get trigger config for this scope
    trigger_config = get_trigger_config()
    
    # Store original invoke methods
    original_invoke = agent.invoke
    original_ainvoke = agent.ainvoke
    
    def wrapped_invoke(input_data, config=None, **kwargs):
        """Synchronous wrapper with POST_TOOL hook."""
        # 🔵 MONITORING: Pre-LLM call token tracking
        input_messages = input_data.get('messages', []) if isinstance(input_data, dict) else []
        pre_token_count = len(str(input_messages)) // 4  # Rough estimate
        
        # Use logger instead of print for LangGraph visibility
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 LLM CALL STARTING 🚀")
        monitor_logger.info(f"📊 Context Window Tokens (est.): {pre_token_count:,}")
        monitor_logger.info(f"💬 Input Messages Count: {len(input_messages)}")
        
        result = original_invoke(input_data, config, **kwargs)
        
        # 🟢 MONITORING: Post-LLM call analysis
        result_messages = result.get('messages', []) if isinstance(result, dict) else []
        post_token_count = len(str(result_messages)) // 4  # Rough estimate
        monitor_logger.info(f"🟢 LLM CALL COMPLETED ✅")
        monitor_logger.info(f"📈 Output Messages Count: {len(result_messages)}")
        monitor_logger.info(f"📊 Total Tokens After (est.): {post_token_count:,}")
        
        # Trigger POST_TOOL hook after execution
        if hasattr(result, 'get') and 'messages' in result:
            try:
                # Check if compression needed
                should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
                # 🔴 MONITORING: Context Management Status
                monitor_logger.info(f"🔴 CONTEXT MANAGEMENT CHECK 🧠")
                monitor_logger.info(f"📏 Context Utilization: {metrics.utilization_percentage:.1f}%")
                monitor_logger.info(f"🎯 Trigger Type: {trigger_type.value if should_compress else 'None'}")
                monitor_logger.info(f"🧹 MCP Cleaning Status: {'Active' if mcp_wrapper and hasattr(mcp_wrapper, 'context_manager') else 'None'}")
                monitor_logger.info(f"📦 Compression Needed: {'Yes' if should_compress else 'No'}")
                
                if should_compress:
                    print(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression synchronously
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        compacted_messages, summary = loop.run_until_complete(
                            enhanced_compact_integration.perform_automatic_compaction(
                                result.get('messages', []), 
                                {"hook_trigger": "POST_TOOL"}
                            )
                        )
                        
                        # Update result with compressed context
                        result['messages'] = compacted_messages
                        result['compression_applied'] = True
                        result['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                        
                        # 🟡 MONITORING: Compression Results
                        monitor_logger.info(f"🟡 COMPRESSION COMPLETED 🗜️")
                        monitor_logger.info(f"📉 Reduction: {getattr(summary, 'total_reduction_percentage', 0):.1f}%")
                        monitor_logger.info(f"📝 Summary Generated: {len(getattr(summary, 'summary_content', '')) if hasattr(summary, 'summary_content') else 0} chars")
                        monitor_logger.info(f"💾 Messages Reduced: {len(result_messages)} → {len(compacted_messages)}")
                        print(f"✅ Context compressed: {getattr(summary, 'total_reduction_percentage', 0):.1f}% reduction")
                        
                    finally:
                        loop.close()
                        
            except Exception as e:
                print(f"⚠️ POST_TOOL compression failed: {e}")
                # Continue without compression
        
        return result
    
    async def wrapped_ainvoke(input_data, config=None, **kwargs):
        """Asynchronous wrapper with POST_TOOL hook."""
        # 🔵 MONITORING: Pre-LLM call token tracking (async)
        input_messages = input_data.get('messages', []) if isinstance(input_data, dict) else []
        pre_token_count = len(str(input_messages)) // 4  # Rough estimate
        
        # Use logger for async monitoring
        monitor_logger = logging.getLogger('mcp_context_tracker')
        monitor_logger.info(f"🔵 ASYNC LLM CALL STARTING 🚀")
        monitor_logger.info(f"📊 Context Window Tokens (est.): {pre_token_count:,}")
        monitor_logger.info(f"💬 Input Messages Count: {len(input_messages)}")
        
        result = await original_ainvoke(input_data, config, **kwargs)
        
        # 🟢 MONITORING: Post-LLM call analysis (async)
        result_messages = result.get('messages', []) if isinstance(result, dict) else []
        post_token_count = len(str(result_messages)) // 4  # Rough estimate
        monitor_logger.info(f"🟢 ASYNC LLM CALL COMPLETED ✅")
        monitor_logger.info(f"📈 Output Messages Count: {len(result_messages)}")
        monitor_logger.info(f"📊 Total Tokens After (est.): {post_token_count:,}")
        
        # Trigger POST_TOOL hook after execution
        if hasattr(result, 'get') and 'messages' in result:
            try:
                # Check if compression needed
                should_compress, trigger_type, metrics = await enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
                if should_compress:
                    print(f"🔄 POST_TOOL compression triggered ({metrics.utilization_percentage:.1f}% utilization)")
                    
                    # Perform compression
                    compacted_messages, summary = await enhanced_compact_integration.perform_automatic_compaction(
                        result.get('messages', []), 
                        {"hook_trigger": "POST_TOOL"}
                    )
                    
                    # Update result with compressed context
                    result['messages'] = compacted_messages
                    result['compression_applied'] = True
                    result['compression_reduction'] = getattr(summary, 'total_reduction_percentage', 0)
                    
                    print(f"✅ Context compressed: {getattr(summary, 'total_reduction_percentage', 0):.1f}% reduction")
                    
            except Exception as e:
                print(f"⚠️ POST_TOOL compression failed: {e}")
                # Continue without compression
        
        return result
    
    # Replace methods with wrapped versions
    agent.invoke = wrapped_invoke
    agent.ainvoke = wrapped_ainvoke
    
    return agent


# ============================================================================
# OPTIMIZED AGENT INITIALIZATION
# ============================================================================

# Print optimization report
print_optimization_report()

# Print trigger configuration from YAML
if LLM_COMPRESSION_AVAILABLE:
    print_config_summary()

# Create the optimized Deep Planning Agent
print("🔧 Creating Optimized Deep Planning Agent with modular prompts...")

# Initialize with default state
initial_state = {
    "current_phase": "investigation",
    "project_id": "unknown", 
    "completed_phases": [],
    "context_summary": "Initial deep planning session with LLM compression",
    "files": {},
    "project_domain": "software development",
    "project_type": "application",
    "investigation_focus": "comprehensive project analysis"
}

# ============================================================================
# LANGGRAPH NATIVE CALLBACK SYSTEM FOR EXECUTION LOGGING
# ============================================================================

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from typing import Any, Dict, List, Optional

class DeepPlanningCallbackHandler(BaseCallbackHandler):
    """
    Custom callback handler that captures LangGraph execution events.
    This is the CORRECT way to get execution visibility in LangGraph.
    """
    
    def __init__(self):
        super().__init__()
        self.execution_logger = logging.getLogger('langgraph_execution_callback')
        self.execution_logger.setLevel(logging.INFO)
        
        # SUPER AGGRESSIVE CALLBACK INITIALIZATION
        print("🎯 CALLBACK: DeepPlanningCallbackHandler initialized")
        print("🔥 QUESTO MESSAGGIO DEVE ESSERE VISIBILE NEL TERMINALE!")
        print("🔥 SE VEDI QUESTO, IL CALLBACK HANDLER È ATTIVO!")
        print("🔥 ORA DOVRAI VEDERE I LOG DURANTE L'ESECUZIONE!")
        
        self.execution_logger.info("🎯 CALLBACK: Handler ready for LangGraph execution events")
        
        # FORCE FLUSH
        import sys
        sys.stdout.flush()
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM starts generating."""
        model_name = serialized.get('id', ['unknown'])[-1] if serialized.get('id') else 'unknown'
        prompt_preview = prompts[0][:100] + "..." if prompts and len(prompts[0]) > 100 else prompts[0] if prompts else ""
        
        message = f"🚀 LLM_START: model={model_name}, prompt_len={len(prompts[0]) if prompts else 0}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
        
        if prompt_preview:
            self.execution_logger.info(f"📝 PROMPT_PREVIEW: {prompt_preview}")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes generating."""
        if response.generations:
            response_preview = response.generations[0][0].text[:100] + "..." if len(response.generations[0][0].text) > 100 else response.generations[0][0].text
            response_len = len(response.generations[0][0].text)
        else:
            response_preview = "No response"
            response_len = 0
            
        message = f"✅ LLM_END: response_len={response_len}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
        
        if response_preview:
            self.execution_logger.info(f"💬 RESPONSE_PREVIEW: {response_preview}")
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error."""
        message = f"❌ LLM_ERROR: {str(error)[:200]}"
        self.execution_logger.error(message)
        print(f"🔥 ERROR: {message}")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts executing."""
        tool_name = serialized.get('name', 'unknown_tool')
        
        # SUPER AGGRESSIVE LOGGING
        message = f"🔧 TOOL_START: {tool_name}, input_len={len(input_str)}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC TOOL START: {message}")
        print(f"🔥 FORZATA VISIBILITA': TOOL {tool_name} HA INIZIATO!")
        print(f"🔥 INPUT: {input_str[:200]}..." if len(input_str) > 200 else f"🔥 INPUT: {input_str}")
        
        # FORCE FLUSH per assicurarsi che appaia subito
        import sys
        sys.stdout.flush()
        input_preview = input_str[:100] + "..." if len(input_str) > 100 else input_str
        
        message = f"🛠️ TOOL_START: {tool_name}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
        
        if input_preview:
            self.execution_logger.info(f"📋 TOOL_INPUT: {input_preview}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes executing."""
        output_preview = output[:200] + "..." if len(output) > 200 else output
        output_len = len(output)
        
        # SUPER AGGRESSIVE LOGGING
        message = f"✅ TOOL_END: output_len={output_len}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC TOOL END: {message}")
        print("🔥 FORZATA VISIBILITA': TOOL HA FINITO!")
        print(f"🔥 OUTPUT: {output_preview}")
        
        # FORCE FLUSH
        import sys
        sys.stdout.flush()
        
        if output_preview:
            self.execution_logger.info(f"📤 TOOL_OUTPUT: {output_preview}")
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a tool encounters an error."""
        message = f"❌ TOOL_ERROR: {str(error)[:200]}"
        self.execution_logger.error(message)
        print(f"🔥 ERROR: {message}")
    
    def on_agent_action(self, action, **kwargs: Any) -> None:
        """Called when an agent takes an action."""
        tool_name = getattr(action, 'tool', 'unknown')
        tool_input = str(getattr(action, 'tool_input', ''))[:100]
        
        message = f"🎯 AGENT_ACTION: tool={tool_name}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
        
        if tool_input:
            self.execution_logger.info(f"⚙️ ACTION_INPUT: {tool_input}")
    
    def on_agent_finish(self, finish, **kwargs: Any) -> None:
        """Called when an agent finishes."""
        output = str(getattr(finish, 'return_values', ''))[:100]
        
        message = f"🏁 AGENT_FINISH"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
        
        if output:
            self.execution_logger.info(f"🎉 FINAL_OUTPUT: {output}")
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain starts."""
        chain_name = serialized.get('id', ['unknown'])[-1] if serialized.get('id') else 'unknown'
        
        message = f"🔗 CHAIN_START: {chain_name}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain ends."""
        message = f"✅ CHAIN_END: keys={list(outputs.keys()) if outputs else []}"
        self.execution_logger.info(message)
        print(f"🔥 EXEC: {message}")
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a chain encounters an error."""
        message = f"❌ CHAIN_ERROR: {str(error)[:200]}"
        self.execution_logger.error(message)
        print(f"🔥 ERROR: {message}")

# Create the global callback handler instance
deep_planning_callback = DeepPlanningCallbackHandler()

# Configure global LangChain callbacks for LangGraph compatibility
try:
    from langchain_core.callbacks import get_callback_manager
    from langchain_core.globals import set_llm_cache
    import os
    
    # Set environment variable for callback propagation
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'  # Disable LangSmith to avoid conflicts
    os.environ['LANGCHAIN_CALLBACKS_ENABLED'] = 'true'
    
    # Try to configure global callback manager
    try:
        callback_manager = get_callback_manager()
        if callback_manager:
            callback_manager.add_handler(deep_planning_callback)
            print("✅ GLOBAL: Callback handler added to global callback manager")
        else:
            print("⚠️ GLOBAL: No global callback manager found")
    except Exception as e:
        print(f"⚠️ GLOBAL: Could not add to global callback manager: {e}")
    
    global_logger = logging.getLogger('langgraph_global_callbacks')
    global_logger.info("🌐 GLOBAL: Callback configuration attempted for LangGraph compatibility")
    
except ImportError as e:
    print(f"⚠️ GLOBAL: Could not import callback manager: {e}")
except Exception as e:
    print(f"⚠️ GLOBAL: Callback setup failed: {e}")

# Legacy functions for backward compatibility
def log_from_execution_context(message: str, level: str = "info", context: str = "execution"):
    """Legacy function - callback system is now preferred."""
    exec_logger = logging.getLogger(f'langgraph_exec_{context}')
    exec_logger.setLevel(logging.INFO)
    log_method = getattr(exec_logger, level.lower(), exec_logger.info)
    log_method(f"🎯 EXECUTION: {message}")
    print(f"🔥 LANGGRAPH_EXEC: {message}")

def create_execution_logger():
    """Legacy function - callback system is now preferred."""
    exec_logger = logging.getLogger('langgraph_execution')
    exec_logger.setLevel(logging.INFO)
    exec_logger.propagate = True
    return exec_logger

def log_agent_state_change(state: Dict[str, Any], operation: str):
    """Legacy function - callback system is now preferred."""
    state_logger = logging.getLogger('langgraph_state')
    state_logger.setLevel(logging.INFO)
    message = f"🔄 STATE_{operation.upper()}: "
    if 'current_phase' in state:
        message += f"phase={state['current_phase']} "
    if 'project_id' in state:
        message += f"project={state['project_id']} "
    if 'messages' in state:
        message += f"messages={len(state['messages'])} "
    state_logger.info(message)
    print(f"🔥 STATE: {message}")

def log_tool_execution(tool_name: str, args: Dict[str, Any] = None):
    """Legacy function - callback system is now preferred."""
    tool_logger = logging.getLogger('langgraph_tools')
    tool_logger.setLevel(logging.INFO)
    message = f"🛠️ TOOL_EXEC: {tool_name}"
    if args:
        safe_args = {k: v for k, v in args.items() if not any(secret in k.lower() for secret in ['token', 'key', 'password'])}
        if safe_args:
            message += f" args={safe_args}"
    tool_logger.info(message)
    print(f"🔥 TOOL: {message}")

# ============================================================================
# ENHANCED AGENT CREATION WITH EXECUTION LOGGING
# ============================================================================

# Create optimized agent with LLM compression enabled by default
module_logger = logging.getLogger('deep_planning_module')
module_logger.info("🚀 MODULE: Starting deep planning agent creation at module level")
module_logger.info("📋 This is the agent that LangGraph will import!")

# Log that we're creating the execution logger
execution_logger = create_execution_logger()
execution_logger.info("🎯 EXECUTION LOGGER: Created for LangGraph runtime visibility")

agent = create_optimized_deep_planning_agent(initial_state, enable_llm_compression=True)

module_logger.info("✅ MODULE: Agent created and available for LangGraph import")
module_logger.info("🎯 Agent object ready for langgraph.json reference")

# Add execution logging capabilities to the agent
agent._log_execution = log_from_execution_context
agent._log_state = log_agent_state_change
agent._log_tool = log_tool_execution

execution_logger.info("⚡ ENHANCED: Agent equipped with LangGraph execution logging")
print("🔥 EXECUTION: Agent enhanced with runtime logging capabilities")

# ============================================================================
# MCP STATE CLEANING INTEGRATION - RISOLVE IL GAP IDENTIFICATO
# ============================================================================

# Apply the wrapper to clean LangGraph state from raw MCP data
print("🔧 Applying MCP state cleaning wrapper to resolve LangGraph integration gap...")
agent = wrap_agent_with_mcp_state_cleaning(agent, mcp_wrapper)

print("✅ Deep Planning Agent with Dynamic System created successfully!")
print(f"⏰ TIMESTAMP: {__import__('datetime').datetime.now()}")
print("🔥 Se vedi questo messaggio ogni volta che fai una domanda, i wrapper funzionano!")
print("\n🔧 MONITORING STATUS:")
print(f"  🔗 Compression hooks enabled: {LLM_COMPRESSION_AVAILABLE}")
print(f"  🧹 MCP cleaning wrapper: {'Active' if mcp_wrapper else 'None'}")
