"""
Deep Planning Agent Core - Main Agent Creation and Orchestration

This is the core module for the Deep Planning Agent, providing the main agent
creation functions and orchestration logic. It imports functionality from
specialized modules for a clean, maintainable architecture.

Key Features:
- Main agent creation with dynamic prompts
- Sub-agent orchestration
- Compatibility wrapping
- Integration with all supporting modules
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from deepagents import create_deep_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import compatibility layer
from ..compatibility.compatibility_layer import ensure_compatibility, print_compatibility_report

# Apply compatibility patches on import
ensure_compatibility()

# Import all supporting modules
from ..integrations.mcp.mcp_integration import (
    initialize_deep_planning_mcp_tools,
    print_mcp_status
)

from .phase_orchestration import (
    format_todos_for_prompt,
    format_outputs_list,
    format_validation_rules,
    format_interaction_points,
    format_validation_result,
    validate_and_transition_phase,
    get_phase_progress_report,
    auto_advance_phase_if_ready,
    print_phase_status
)

from ..context.context_compression import (
    check_and_compact_if_needed,
    get_compaction_metrics,
    wrap_agent_with_compression_hooks,
    print_compression_status
)

# Import dynamic prompt system
from ..config.prompt_templates import (
    inject_dynamic_context,
    generate_phase_todos,
    generate_phase_context,
    get_tool_context,
    generate_orchestrator_context,
    generate_all_phase_contexts
)

from ..config.prompt_config import (
    PhaseType,
    get_phase_config,
    get_tools_for_phase,
    validate_phase_completion,
    get_current_phase_config,
    get_next_phase,
    get_transition_requirements,
    get_phase_summary
)

# Import optimization stats for reporting
from ..config.optimized_prompts import OPTIMIZATION_STATS

# Import compatibility system
from ..compatibility.tool_compatibility import apply_tool_compatibility_fixes, setup_compatibility_logging
from ..compatibility.model_compatibility import (
    detect_model_from_environment, 
    should_apply_compatibility_fixes,
    print_model_compatibility_report,
    default_registry
)

# Import simplified agent factory
from .agent_factory import (
    SimplifiedAgentFactory,
    create_simplified_factory
)

# Check for LLM compression availability
try:
    from ..context.llm_compression import LLMCompressor, CompressionConfig, CompressionStrategy
    from ..context.context_hooks import ContextHookManager, CompressionHook, HookType
    from ..context.compact_integration import EnhancedCompactIntegration
    from ..config.config_loader import get_trigger_config, get_context_management_config, print_config_summary
    from ..config.unified_config import get_model_config, get_performance_config
    LLM_COMPRESSION_AVAILABLE = True
    logger.info("✅ LLM Compression system available")
except ImportError as e:
    logger.warning(f"⚠️ LLM Compression system not available: {e}")
    LLM_COMPRESSION_AVAILABLE = False

# Model configuration
DEFAULT_MODEL = os.getenv("DEEPAGENTS_MODEL", "claude-sonnet-4-20250514")
setup_compatibility_logging(level="INFO")

# Detect and configure model compatibility
detected_model = detect_model_from_environment()
ENABLE_COMPATIBILITY_FIXES = should_apply_compatibility_fixes(detected_model, default_registry)

if ENABLE_COMPATIBILITY_FIXES:
    logger.info(f"🔧 Compatibility fixes ENABLED for model: {detected_model}")
else:
    logger.info(f"✅ Model {detected_model} does not require compatibility fixes")

# Print detailed compatibility report if fixes are enabled
if ENABLE_COMPATIBILITY_FIXES:
    print_model_compatibility_report(detected_model, default_registry)

# Initialize MCP tools and context management systems
print("🏗️ Initializing Deep Planning Agent with MCP integration...")
deep_planning_tools, mcp_wrapper, compact_integration = initialize_deep_planning_mcp_tools()

# Apply compatibility fixes to tools if needed
if ENABLE_COMPATIBILITY_FIXES:
    print("🔧 Applying compatibility fixes to tools...")
    print("✅ MCP tools prepared (fixes will be applied to deepagents built-in tools)")


# ============================================================================
# SUB-AGENT CREATION
# ============================================================================

def create_optimized_subagent(agent_name: str, phase: str, tools: List[Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a sub-agent configuration with FULLY DYNAMIC prompts from prompt_config.
    
    Args:
        agent_name: Name of the agent to create (matches phase config agent names)
        phase: Current phase name
        tools: Available tools list
        state: Current agent state for context injection
    
    Returns:
        Dictionary containing completely dynamic agent configuration
    """
    # Get dynamic configuration from prompt_config
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
    Create ALL sub-agents dynamically based on phase configurations.
    Uses DynamicAgentFactory for complete agent generation!
    
    Args:
        tools: Available tools list
        current_state: Current agent state
    
    Returns:
        List of dynamically generated sub-agent configurations
    """
    # Use the simplified agent factory
    agent_factory = create_simplified_factory(tools)
    
    # Generate agents for all phases
    subagents = []
    for phase in PhaseType:
        try:
            agent_config = agent_factory.create_phase_agent(phase, current_state)
            subagents.append(agent_config)
            print(f"✅ Created {agent_config['emoji']} {agent_config['agent_name']} for {phase.value} phase")
        except Exception as e:
            print(f"⚠️ Failed to create agent for {phase.value}: {e}")
            # Create fallback agent
            fallback = create_fallback_subagent(phase.value, tools, current_state)
            if fallback:
                subagents.append(fallback)
    
    return subagents


def create_fallback_subagent(phase: str, tools: List[Any], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a fallback sub-agent if dynamic creation fails."""
    try:
        return create_optimized_subagent(f"{phase}_agent", phase, tools, state)
    except Exception as e:
        logger.error(f"Failed to create fallback agent for {phase}: {e}")
        return None


def generate_optimized_main_prompt(current_phase: str, state: Dict[str, Any], tools: List[Any]) -> str:
    """
    Generate FULLY DYNAMIC main orchestrator prompt.
    
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
    
    # Create DYNAMIC orchestrator template
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
    """Print optimization statistics report."""
    print("\n" + "="*60)
    print("PROMPT OPTIMIZATION REPORT")
    print("="*60)
    
    for key, value in OPTIMIZATION_STATS.items():
        print(f"{key}: {value}")
    
    print("="*60 + "\n")


# ============================================================================
# MAIN AGENT CREATION
# ============================================================================

def create_optimized_deep_planning_agent(
    initial_state: Dict[str, Any] = None, 
    enable_llm_compression: bool = True
) -> Any:
    """
    Create the deep planning agent with optimized, dynamic prompts and optional LLM compression.
    
    Args:
        initial_state: Initial state for context generation
        enable_llm_compression: Enable automatic LLM compression hooks
    
    Returns:
        Configured deep planning agent with optional compression hooks
    """
    logger.info("🏗️ Starting deep planning agent creation")
    logger.info(f"🔧 Parameters: enable_llm_compression={enable_llm_compression}")
    
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
    logger.info(f"📝 Generating dynamic main prompt for phase: {current_phase}")
    
    optimized_main_prompt = generate_optimized_main_prompt(
        current_phase, 
        initial_state, 
        deep_planning_tools
    )
    logger.info(f"✅ Generated main prompt ({len(optimized_main_prompt)} chars)")
    
    # Create dynamic sub-agents
    logger.info("🤖 Creating dynamic sub-agents")
    optimized_subagents = create_dynamic_subagents(deep_planning_tools, initial_state)
    logger.info(f"✅ Created {len(optimized_subagents)} sub-agents")
    
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
        model_cfg = get_model_config()
        perf_cfg = get_performance_config()
        
        compression_config = CompressionConfig(
            strategy=CompressionStrategy.ADAPTIVE,
            target_reduction_percentage=65.0,
            max_output_tokens=model_cfg.max_output_tokens,
            preserve_last_n_messages=trigger_config.preserve_last_n_messages,
            enable_fallback=trigger_config.enable_fallback,
            compression_timeout=perf_cfg.compression_timeout
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
    
    # Create the agent
    logger.info("🏎️ Assembling final agent with dynamic prompts")
    logger.info(f"🔧 Using model: {DEFAULT_MODEL}")
    logger.info(f"🛠️ Tools count: {len(deep_planning_tools)}")
    
    agent = create_compatible_deep_agent(
        tools=deep_planning_tools,
        instructions=optimized_main_prompt,
        model=DEFAULT_MODEL,
        subagents=optimized_subagents,
        enable_planning_approval=True,
        checkpointer="memory",
        _enhanced_compact_integration=enhanced_compact_integration,
        _mcp_wrapper=mcp_wrapper
    )
    logger.info("✅ Base agent created successfully")
    
    # Add validation capabilities to the agent
    logger.info("⚡ Adding validation capabilities")
    agent._dynamic_factory = create_simplified_factory(deep_planning_tools)
    agent._validate_phase_transition = lambda phase, state: validate_and_transition_phase(phase, state, deep_planning_tools)
    agent._get_progress_report = lambda state: get_phase_progress_report(state, deep_planning_tools)
    agent._auto_advance_phase = lambda state: auto_advance_phase_if_ready(state, deep_planning_tools)
    
    logger.info("🏁 Deep planning agent creation completed!")
    print("🤖 Agent equipped with dynamic validation and auto-progression!")
    
    return agent


def create_compatible_deep_agent(*args, **kwargs):
    """
    Create a deep agent with automatic compatibility fixes and optional LLM compression hooks.
    """
    logger.info("🔧 Creating compatible deep agent")
    
    # Import here to avoid circular imports
    from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
    
    # Extract compression integration and MCP wrapper from kwargs
    enhanced_compact_integration = kwargs.pop('_enhanced_compact_integration', None)
    mcp_wrapper = kwargs.pop('_mcp_wrapper', None)
    
    logger.info(f"🧠 LLM Compression available: {enhanced_compact_integration is not None}")
    
    if ENABLE_COMPATIBILITY_FIXES:
        logger.info("🛡️ Applying compatibility fixes to built-in tools")
        print("🛡️  Applying compatibility fixes to built-in tools...")
        
        # Create list of built-in tools
        built_in_tools = [write_todos, write_file, read_file, ls, edit_file]
        
        # Add review_plan if planning approval is enabled
        if kwargs.get('enable_planning_approval', False):
            built_in_tools.append(review_plan)
            logger.info("📋 Added review_plan tool for planning approval")
        
        logger.info(f"🔧 Fixing {len(built_in_tools)} built-in tools for model: {detected_model}")
        
        # Apply compatibility fixes
        fixed_built_in_tools = apply_tool_compatibility_fixes(built_in_tools, detected_model)
        
        # Monkey patch the tools module to use our fixed tools
        import deepagents.tools as tools_module
        for i, original_tool in enumerate(built_in_tools):
            tool_name = getattr(original_tool, 'name', getattr(original_tool, '__name__', None))
            if tool_name and hasattr(tools_module, tool_name):
                setattr(tools_module, tool_name, fixed_built_in_tools[i])
        
        logger.info("✅ Built-in tools patched with compatibility fixes")
        print("✅ Built-in tools patched with compatibility fixes")
    else:
        logger.info("⏭️ Skipping compatibility fixes (not needed for this model)")
    
    # Create the agent normally
    logger.info("🏗️ Creating base deep agent")
    agent = create_deep_agent(*args, **kwargs)
    logger.info("✅ Base deep agent created successfully")
    
    # Setup LLM compression hooks if enhanced integration is provided
    if enhanced_compact_integration and LLM_COMPRESSION_AVAILABLE:
        print("🔗 Setting up POST_TOOL compression hooks...")
        
        try:
            agent = wrap_agent_with_compression_hooks(
                agent, 
                None, 
                enhanced_compact_integration,
                mcp_wrapper
            )
            
            print("✅ POST_TOOL compression hooks integrated")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup compression hooks: {e}")
            print(f"⚠️ Failed to setup compression hooks: {e}")
            print("🔄 Agent running without automatic compression")
    else:
        logger.info("⏭️ Skipping LLM compression hooks (not available or disabled)")
    
    logger.info("🏁 Compatible deep agent creation completed!")
    return agent


# ============================================================================
# MAIN EXECUTION
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

# Create the agent (this will be used by LangGraph)
agent = create_optimized_deep_planning_agent(initial_state, enable_llm_compression=True)

print("\n✅ Deep Planning Agent ready for deployment!")
print("🚀 Use 'langgraph dev' to start the development server")
print("📚 Or import 'agent' from this module in your code")

# Export the agent for LangGraph
__all__ = ['agent', 'create_optimized_deep_planning_agent', 'create_compatible_deep_agent']