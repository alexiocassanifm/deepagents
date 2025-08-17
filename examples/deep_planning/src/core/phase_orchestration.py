"""
Phase Orchestration Module for Deep Planning Agent

This module manages the 4-phase development methodology, including phase validation,
transitions, progress tracking, and automatic advancement. It provides the core
workflow management for the structured planning process.

Key Features:
- Phase validation and transition management
- Progress reporting and tracking
- Automatic phase advancement
- Format helpers for phase-specific content
- Integration with dynamic agent factory
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

# Setup logger for phase operations
logger = logging.getLogger(__name__)

# Import phase configuration and dynamic agent factory
try:
    from ..config.prompt_config import PhaseType
    from .agent_factory import create_simplified_factory
    PHASE_CONFIG_AVAILABLE = True
except ImportError:
    PHASE_CONFIG_AVAILABLE = False
    logger.warning("⚠️ Phase configuration or dynamic agent factory not available")


def format_todos_for_prompt(todos: List[Dict[str, Any]]) -> str:
    """
    Format dynamic TODOs for inclusion in prompts.
    
    Args:
        todos: List of todo items with content and status
        
    Returns:
        Formatted string of todos with status indicators
    """
    if not todos:
        return "No specific tasks generated"
    
    formatted = []
    for todo in todos:
        status_emoji = {
            "pending": "⏳", 
            "in_progress": "🔄", 
            "completed": "✅"
        }.get(todo.get("status", "pending"), "📋")
        formatted.append(f"{status_emoji} {todo['content']}")
    
    return "\n".join(formatted)


def format_outputs_list(outputs: List[str]) -> str:
    """
    Format required outputs list for prompts.
    
    Args:
        outputs: List of required output descriptions
        
    Returns:
        Formatted string of outputs
    """
    if not outputs:
        return "No specific output required"
    return "\n".join([f"📄 {output}" for output in outputs])


def format_validation_rules(rules) -> str:
    """
    Format validation rules for prompts.
    
    Args:
        rules: List of validation rules (can be objects or strings)
        
    Returns:
        Formatted string of validation rules
    """
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
    """
    Format human interaction points for prompts.
    
    Args:
        interaction_points: List of interaction point descriptions
        
    Returns:
        Formatted string of interaction points
    """
    if not interaction_points:
        return "No human interaction required"
    return "\n".join([f"👤 {point}" for point in interaction_points])


def format_validation_result(validation_result: Dict[str, Any]) -> str:
    """
    Format validation result for orchestrator prompt.
    
    Args:
        validation_result: Dictionary containing validation status and details
        
    Returns:
        Formatted validation result string
    """
    if not validation_result:
        return "Validation not available"
    
    if validation_result.get('valid', False):
        completed_count = len(validation_result.get('completed_validations', []))
        return f"✅ Phase validated ({completed_count} checks completed)"
    else:
        errors = validation_result.get('errors', [])
        return f"❌ Validation failed: {', '.join(errors) if errors else 'Unknown errors'}"


def validate_and_transition_phase(
    current_phase: str, 
    state: Dict[str, Any], 
    tools: List[Any]
) -> Tuple[bool, str, List[str]]:
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
    if not PHASE_CONFIG_AVAILABLE:
        logger.error("Phase configuration not available")
        return False, "", ["Phase configuration module not available"]
    
    try:
        phase_type = PhaseType(current_phase)
    except ValueError:
        return False, "", [f"Invalid phase: {current_phase}"]
    
    # Create factory for validation
    agent_factory = create_simplified_factory(tools)
    
    # Use factory's validation method
    can_transition, next_phase, missing_reqs = agent_factory.validate_transition(
        current_phase, state
    )
    
    if can_transition:
        logger.info(f"✅ Phase {current_phase} validation passed! Ready for transition to {next_phase}")
    else:
        logger.warning(f"❌ Phase {current_phase} validation failed. Missing: {missing_reqs}")
    
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
    if not PHASE_CONFIG_AVAILABLE:
        logger.error("Phase configuration not available")
        return {"error": "Phase configuration module not available"}
    
    agent_factory = create_simplified_factory(tools)
    # Note: Simplified factory doesn't have get_phase_summary_report, using basic report
    report = {
        "current_phase": state.get("current_phase", "unknown"),
        "completed_phases": state.get("completed_phases", [])
    }
    
    # Add dynamic context analysis
    current_phase = state.get("current_phase", "unknown")
    if current_phase != "unknown":
        try:
            phase_type = PhaseType(current_phase)
            current_agent_config = agent_factory.create_phase_agent(phase_type, state)
            
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


def auto_advance_phase_if_ready(
    state: Dict[str, Any], 
    tools: List[Any]
) -> Tuple[bool, Dict[str, Any]]:
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
        logger.info(f"🔄 Auto-advance blocked. Missing requirements: {missing_reqs}")
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
    
    logger.info(f"🔄 Auto Progression: Advanced from {current_phase} → {next_phase}")
    return True, updated_state


def get_phase_status(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current phase status information.
    
    Args:
        state: Current project state
        
    Returns:
        Dictionary containing phase status
    """
    return {
        "current_phase": state.get("current_phase", "unknown"),
        "completed_phases": state.get("completed_phases", []),
        "phase_outputs": state.get("phase_outputs", {}),
        "validation_status": state.get("validation_status", {}),
        "todos": state.get("todos", []),
        "context_summary": state.get("context_summary", "")
    }


def print_phase_status(state: Dict[str, Any]):
    """
    Print phase status for debugging.
    
    Args:
        state: Current project state
    """
    status = get_phase_status(state)
    
    print("\n" + "="*60)
    print("PHASE ORCHESTRATION STATUS")
    print("="*60)
    print(f"Current Phase: {status['current_phase']}")
    print(f"Completed Phases: {', '.join(status['completed_phases']) if status['completed_phases'] else 'None'}")
    
    # Count todos by status
    todos = status['todos']
    if todos:
        pending = sum(1 for t in todos if t.get('status') == 'pending')
        in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
        completed = sum(1 for t in todos if t.get('status') == 'completed')
        print(f"Todos: {pending} pending, {in_progress} in progress, {completed} completed")
    else:
        print("Todos: None")
    
    # Show phase outputs
    if status['phase_outputs']:
        print("Phase Outputs:")
        for phase, outputs in status['phase_outputs'].items():
            print(f"  {phase}: {len(outputs) if isinstance(outputs, list) else 1} output(s)")
    
    print("="*60 + "\n")