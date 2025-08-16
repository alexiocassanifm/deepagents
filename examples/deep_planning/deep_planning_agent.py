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
        print(f"Note: Could not patch {module_name}: {e}")

print("🔧 Comprehensive type annotation patching completed")

# Configure debug logging for development
def setup_debug_logging():
    """Setup comprehensive debug logging for all components."""
    log_level = os.getenv('PYTHON_LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'debug.log')
    
    # Configure root logger with file and console handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler (per vedere i log a schermo)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (per salvare i log su file)
    file_handler = logging.FileHandler(log_file, mode='w')  # 'w' per sovrascrivere ogni volta
    file_handler.setLevel(logging.DEBUG)  # Sempre DEBUG su file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Enable debug for specific modules
    loggers_to_debug = [
        'mcp_cleaners',
        'context_manager', 
        'mcp_wrapper',
        'deepagents',
        'langgraph',
        'langchain'
    ]
    
    for logger_name in loggers_to_debug:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
    
    print(f"🔍 Debug logging enabled at level: {log_level}")
    print(f"📁 Log file: {log_file}")
    print(f"📊 Debug loggers: {', '.join(loggers_to_debug)}")
    
    # Test log per verificare che funzioni
    logging.debug("🚀 Debug logging setup completed - test message")
    logging.info("ℹ️ Info logging setup completed - test message")

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

# Import dynamic agent factory - FERRARI ENGINE!
from dynamic_agent_factory import (
    DynamicAgentFactory,
    create_dynamic_agent_factory,
    quick_create_phase_agent,
    validate_factory_setup
)

# Import LLM compression system for automatic hook integration
try:
    from llm_compression import LLMCompressor, CompressionConfig, CompressionStrategy
    from context_hooks import ContextHookManager, CompressionHook, HookType
    from enhanced_compact_integration import EnhancedCompactIntegration
    from config_loader import get_trigger_config, get_context_management_config, print_config_summary
    LLM_COMPRESSION_AVAILABLE = True
    print("✅ LLM Compression system available")
except ImportError as e:
    print(f"⚠️ LLM Compression system not available: {e}")
    LLM_COMPRESSION_AVAILABLE = False

# Model configuration from environment
DEFAULT_MODEL = os.getenv("DEEPAGENTS_MODEL", None)  # None = usa Claude default

# Setup compatibility system
setup_compatibility_logging(level="INFO")

# Detect and configure model compatibility
detected_model = detect_model_from_environment() or DEFAULT_MODEL or "claude-3.5-sonnet"
ENABLE_COMPATIBILITY_FIXES = should_apply_compatibility_fixes(detected_model, default_registry)

print("🔧 Model Compatibility Configuration:")
print(f"🤖 Detected/Configured model: {detected_model}")
print(f"🛡️  Compatibility fixes enabled: {ENABLE_COMPATIBILITY_FIXES}")

# Print detailed compatibility report if fixes are enabled
if ENABLE_COMPATIBILITY_FIXES:
    print_model_compatibility_report(detected_model, default_registry)

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: langchain-mcp-adapters not available. Install with: pip install langchain-mcp-adapters")


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
        print("⚠️ MCP adapters not available, using fallback tools")
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
        return get_fallback_tools(), None, None


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
# DYNAMIC PROMPT HELPER FUNCTIONS - NEW FERRARI ENGINE!
# ============================================================================

def format_todos_for_prompt(todos: List[Dict[str, Any]]) -> str:
    """Format dynamic TODOs for inclusion in prompts."""
    if not todos:
        return "Nessun task specifico generato"
    
    formatted = []
    for todo in todos:
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(todo.get("status", "pending"), "📋")
        formatted.append(f"{status_emoji} {todo['content']}")
    
    return "\n".join(formatted)

def format_outputs_list(outputs: List[str]) -> str:
    """Format required outputs list for prompts."""
    if not outputs:
        return "Nessun output specifico richiesto"
    return "\n".join([f"📄 {output}" for output in outputs])

def format_validation_rules(rules) -> str:
    """Format validation rules for prompts."""
    if not rules:
        return "Nessun criterio di validazione specifico"
    
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
        return "Nessuna interazione umana richiesta"
    return "\n".join([f"👤 {point}" for point in interaction_points])

def format_validation_result(validation_result: Dict[str, Any]) -> str:
    """Format validation result for orchestrator prompt."""
    if not validation_result:
        return "Validazione non disponibile"
    
    if validation_result.get('valid', False):
        return f"✅ Fase validata ({len(validation_result.get('completed_validations', []))} controlli completati)"
    else:
        errors = validation_result.get('errors', [])
        return f"❌ Validazione fallita: {', '.join(errors) if errors else 'Errori sconosciuti'}"

def validate_and_transition_phase(current_phase: str, state: Dict[str, Any], tools: List[Any]) -> Tuple[bool, str, List[str]]:
    """
    FERRARI ENGINE: Validate current phase completion and determine transition.
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
    agent_factory = create_dynamic_agent_factory(tools)
    
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
    FERRARI DASHBOARD: Generate comprehensive phase progress report.
    
    Args:
        state: Current project state
        tools: Available tools
        
    Returns:
        Complete progress report with dynamic analysis
    """
    agent_factory = create_dynamic_agent_factory(tools)
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
    FERRARI AUTO-PILOT: Automatically advance to next phase if current is completed.
    
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
    
    print(f"🏁 FERRARI AUTO-PILOT: Advanced from {current_phase} → {next_phase}")
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
Sei il {phase_config.agent_name} - {phase_config.emoji} {phase_config.name}

## La Tua Missione
{phase_config.goal}

## Contesto Progetto
- Progetto: {{project_name}} ({{project_type}})
- Dominio: {{domain}}
- Focus: {{focus_area}}
- Fase corrente: {phase} ({phase_config.completion_weight}% completamento)

## I Tuoi Task Dinamici
{format_todos_for_prompt(dynamic_todos)}

## Strumenti Disponibili ({tool_context['tool_count']} filtrati per questa fase)
{tool_context['tool_categories']}
Focus: {tool_context['phase_objectives']}

## Output Richiesti
{format_outputs_list(phase_config.required_outputs)}

## Criteri di Successo
{format_validation_rules(phase_config.validation_rules)}

## Interazioni Umane
{format_interaction_points(phase_config.interaction_points) if phase_config.requires_user_input else "Nessuna interazione richiesta"}

Durata stimata: {phase_config.duration_estimate}
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
    Create ALL sub-agents using the DYNAMIC AGENT FACTORY - FERRARI POWER!
    NO MORE MANUAL CREATION - Everything automated from phase configurations!
    
    Args:
        tools: Available tools list
        current_state: Current agent state for context injection
    
    Returns:
        List of completely dynamically configured sub-agents
    """
    # Create the dynamic agent factory - FERRARI ENGINE
    agent_factory = create_dynamic_agent_factory(tools)
    
    # Validate factory setup
    validation_report = validate_factory_setup(agent_factory)
    if not validation_report['factory_valid']:
        print(f"⚠️ Factory validation failed: {validation_report['errors']}")
        print("🔄 Falling back to direct phase creation...")
        
        # Fallback to direct creation if factory fails
        return create_fallback_subagents(tools, current_state)
    
    # Use factory to create all agents dynamically
    dynamic_agents = agent_factory.create_all_phase_agents(current_state)
    
    print(f"🏎️ FERRARI FACTORY created {len(dynamic_agents)} dynamic sub-agents!")
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
Sei il Deep Planning Orchestrator - Coordinatore di pianificazione sviluppo a 4 fasi.

## Stato Processo
- Fase attuale: {{current_phase}} ({{completion_percentage}}% completato)
- Contesto: {{context_summary}}
- Progetto: {{project_id}}
- Fasi completate: {{completed_phases}}

## Fase Corrente: {current_config.emoji if current_config else '🔧'} {current_config.name if current_config else current_phase.title()}
{f'Goal: {current_config.goal}' if current_config else ''}
{f'Agent richiesto: {current_config.agent_name}' if current_config else ''}
{f'Interazione umana: {'Sì' if current_config and current_config.requires_user_input else 'No'}' if current_config else ''}
{f'Approvazione richiesta: {'Sì' if current_config and current_config.requires_approval else 'No'}' if current_config else ''}

## Il Tuo Ruolo
Coordi i sub-agent attraverso fasi strutturate, assicurando transizioni fluide e validazione completezza.

## Strumenti Disponibili
{{tool_count}} strumenti totali, {{phase_objectives}} per la fase corrente

## Azione Raccomandata
{{recommended_next_action}}

## Criteri Transizione
{get_transition_requirements(phase_type) if phase_type else ['Fase sconosciuta']}

## Validazione Attuale
{{validation_criteria}}

Deploya il sub-agent appropriato o gestisci la transizione alla prossima fase.
"""
    
    # Add validation status to context
    if phase_type:
        validation_result = validate_phase_completion(phase_type, state)
        orchestrator_context['validation_status'] = format_validation_result(validation_result)
        orchestrator_context['validation_criteria'] = '\n'.join(
            [f"- {rule.description}" for rule in current_config.validation_rules] if current_config else ["Nessun criterio"]
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
    optimized_main_prompt = generate_optimized_main_prompt(
        current_phase, 
        initial_state, 
        deep_planning_tools
    )
    
    # Create dynamic sub-agents
    optimized_subagents = create_dynamic_subagents(deep_planning_tools, initial_state)
    
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
        from src.deepagents.model import get_model
        agent_model = get_model(DEFAULT_MODEL)
        
        # Create LLM compressor using YAML config
        compression_config = CompressionConfig(
            strategy=CompressionStrategy.ADAPTIVE,
            target_reduction_percentage=65.0,
            max_output_tokens=2500,
            preserve_last_n_messages=trigger_config.preserve_last_n_messages,
            enable_fallback=trigger_config.enable_fallback,
            compression_timeout=trigger_config.compression_timeout
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
    
    # FERRARI FINAL ASSEMBLY: Create the agent with COMPLETELY DYNAMIC prompts
    agent = create_compatible_deep_agent(
        tools=deep_planning_tools,
        instructions=optimized_main_prompt,
        model=DEFAULT_MODEL,
        subagents=optimized_subagents,
        enable_planning_approval=True,
        checkpointer="memory",
        # Pass compression integration for hook setup
        _enhanced_compact_integration=enhanced_compact_integration
    )
    
    # Add FERRARI validation capabilities to the agent
    agent._dynamic_factory = create_dynamic_agent_factory(deep_planning_tools)
    agent._validate_phase_transition = lambda phase, state: validate_and_transition_phase(phase, state, deep_planning_tools)
    agent._get_progress_report = lambda state: get_phase_progress_report(state, deep_planning_tools)
    agent._auto_advance_phase = lambda state: auto_advance_phase_if_ready(state, deep_planning_tools)
    
    print("🏎️ FERRARI agent equipped with dynamic validation and auto-pilot!")
    
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
    # Import here to avoid circular imports and access to built-in tools
    from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
    
    # Extract compression integration from kwargs
    enhanced_compact_integration = kwargs.pop('_enhanced_compact_integration', None)
    
    if ENABLE_COMPATIBILITY_FIXES:
        print("🛡️  Applying compatibility fixes to built-in tools...")
        
        # Create list of built-in tools
        built_in_tools = [write_todos, write_file, read_file, ls, edit_file]
        
        # Add review_plan if planning approval is enabled
        if kwargs.get('enable_planning_approval', False):
            built_in_tools.append(review_plan)
        
        # Apply compatibility fixes
        fixed_built_in_tools = apply_tool_compatibility_fixes(built_in_tools, detected_model)
        
        # Monkey patch the tools module to use our fixed tools
        import deepagents.tools as tools_module
        for i, original_tool in enumerate(built_in_tools):
            tool_name = getattr(original_tool, 'name', getattr(original_tool, '__name__', None))
            if tool_name and hasattr(tools_module, tool_name):
                setattr(tools_module, tool_name, fixed_built_in_tools[i])
        
        print("✅ Built-in tools patched with compatibility fixes")
    
    # Create the agent normally
    agent = create_deep_agent(*args, **kwargs)
    
    # Setup LLM compression hooks if enhanced integration is provided
    if enhanced_compact_integration and LLM_COMPRESSION_AVAILABLE:
        print("🔗 Setting up POST_TOOL compression hooks...")
        
        try:
            # Setup hook manager with POST_TOOL hook
            hook_manager = ContextHookManager(enhanced_compact_integration.llm_compressor)
            
            # Get trigger config from YAML
            yaml_trigger_config = get_trigger_config()
            
            # Create compression hook configured for POST_TOOL using YAML values
            compression_hook = CompressionHook(
                compressor=enhanced_compact_integration.llm_compressor,
                trigger_config={
                    "utilization_threshold": yaml_trigger_config.post_tool_threshold,
                    "mcp_noise_threshold": yaml_trigger_config.mcp_noise_threshold,
                    "min_messages": 3,  # Keep low for responsiveness
                    "force_compression_threshold": yaml_trigger_config.force_llm_threshold
                },
                priority=HookType.POST_TOOL
            )
            
            # Register POST_TOOL hook
            hook_manager.register_hook(HookType.POST_TOOL, compression_hook)
            
            # Wrap the agent with automatic hook execution
            agent = _wrap_agent_with_compression_hooks(agent, hook_manager, enhanced_compact_integration)
            
            print("✅ POST_TOOL compression hooks integrated")
            print(f"   🎯 Trigger threshold: {yaml_trigger_config.post_tool_threshold:.0%} context utilization")
            print(f"   🔧 Using same LLM as agent for compression")
            print(f"   📋 All triggers from context_config.yaml")
            
        except Exception as e:
            print(f"⚠️ Failed to setup compression hooks: {e}")
            print("🔄 Agent running without automatic compression")
    
    return agent


def _wrap_agent_with_compression_hooks(agent, hook_manager, enhanced_compact_integration):
    """
    Wrappa l'agent con hook automatici di compressione POST_TOOL.
    
    Intercetta l'esecuzione dell'agent per triggare compressione dopo tool calls.
    """
    # Store original invoke methods
    original_invoke = agent.invoke
    original_ainvoke = agent.ainvoke
    
    def wrapped_invoke(input_data, config=None, **kwargs):
        """Wrapper sincrono con hook POST_TOOL."""
        result = original_invoke(input_data, config, **kwargs)
        
        # Trigger POST_TOOL hook after execution
        if hasattr(result, 'get') and 'messages' in result:
            try:
                # Check if compression needed
                should_compress, trigger_type, metrics = enhanced_compact_integration.should_trigger_compaction(
                    result.get('messages', [])
                )
                
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
                        
                        print(f"✅ Context compressed: {getattr(summary, 'total_reduction_percentage', 0):.1f}% reduction")
                        
                    finally:
                        loop.close()
                        
            except Exception as e:
                print(f"⚠️ POST_TOOL compression failed: {e}")
                # Continue without compression
        
        return result
    
    async def wrapped_ainvoke(input_data, config=None, **kwargs):
        """Wrapper asincrono con hook POST_TOOL."""
        result = await original_ainvoke(input_data, config, **kwargs)
        
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

# Create optimized agent with LLM compression enabled by default
agent = create_optimized_deep_planning_agent(initial_state, enable_llm_compression=True)

print("🏁 FERRARI-POWERED Deep Planning Agent with FULL DYNAMIC SYSTEM created successfully!")
print("📋 🏎️ FERRARI FEATURES - 100% DYNAMIC SYSTEM:")
print("  🚀 COMPLETE dynamic prompt system - NO MORE STATIC TEMPLATES!")
print("  🎯 Context-aware TODO generation based on project state")
print("  🔧 Intelligent tool filtering per phase from configurations")
print("  📋 Phase validation using prompt_config.py rules")
print("  🏗️ Sub-agents created entirely from PhaseType configurations")
print("  ⚡ 91% reduction in main prompt length (650 → 60 lines)")
print("  🧠 Dynamic context injection throughout ALL prompts")
print("  📊 Real-time phase configuration and state adaptation")
print("  🔄 Automatic phase transition validation")
print("  🎨 Template-free prompt generation system")
print("  📱 MCP integration for real-time project analysis")
print("  👤 Human-in-the-loop plan approval workflow")
print("  ✅ Structured plan validation (8 required sections)")
print("  🎼 Sub-agent orchestration with FULLY dynamic prompts")
print("  📈 Focus chain creation for implementation tracking")
if compact_integration:
    print("  ✅ Automatic context compaction with 60-80% noise reduction")
    print("  ✅ Claude Code compatible summarization and continuation")
if LLM_COMPRESSION_AVAILABLE:
    print("  ✅ LLM-based semantic compression with POST_TOOL hooks")
    print("  ✅ Intelligent compression using same LLM as agent") 
    print("  ✅ Automatic trigger at 70% context utilization")
print("  🏎️ FERRARI Dynamic Agent Factory for real-time agent generation")
print("  🏆 Automatic phase validation and transition management")
print("  📊 Real-time progress reporting with dynamic analysis")
print("  ⚡ Auto-pilot phase advancement when criteria met")
if ENABLE_COMPATIBILITY_FIXES:
    print("  ✅ Model compatibility fixes for reliable tool calling")

print(f"\n🏁 FERRARI ACTIVATED! {OPTIMIZATION_STATS['overall_reduction_percentage']}% more efficient prompts with 100% dynamic system!")
print("🏗️  FULLY modular architecture - every prompt generated from configurations")
print("🛡️  Tool compatibility system active for maximum model compatibility")
print("⚙️  Dynamic system status: ALL components using prompt_config.py")
print("🎯  Context-awareness: MAXIMUM (no more static templates!)")
if compact_integration:
    print("📦 Automatic context compaction system active for extended conversations")
if mcp_wrapper:
    print("🧹 MCP noise reduction system active for cleaner context")
print("\n💡 FERRARI Performance Benefits:")
print("  🧠 MAXIMUM LLM attention with context-specific prompts")
print("  ⚡ ZERO cognitive load - each prompt perfectly tailored")
print("  🎯 COMPLETE dynamic adaptation to any project context")
print("  🔧 ULTIMATE maintainability - single source of truth in configs")
print("  🏆 CONSISTENT peak performance across all scenarios")
print("  🚀 INTELLIGENT todo generation based on real project state")
print("  🎨 NO MORE HARDCODED EXAMPLES - everything dynamically generated")