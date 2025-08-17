"""
Simplified Agent Factory - Lightweight agent creation for 4-phase process

This module provides a streamlined factory for creating phase-specific agents
without the over-engineering of the original 497-line implementation.

Key simplifications:
- Removed unused migration and validation methods
- Simplified prompt generation
- Direct phase-to-agent mapping
- Reduced from 497 to ~150 lines
"""

from typing import Dict, Any, List, Optional
from ..config.prompt_config import (
    PhaseType, 
    get_phase_config, 
    get_tools_for_phase,
    validate_phase_completion,
    get_next_phase
)
from ..config.prompt_templates import (
    generate_phase_todos,
    generate_phase_context,
    inject_dynamic_context
)


class SimplifiedAgentFactory:
    """
    Lightweight factory for creating phase-specific agents.
    Focuses on essential functionality for the 4-phase process.
    """
    
    def __init__(self, available_tools: List[Any]):
        """Initialize factory with available tools."""
        self.available_tools = available_tools
    
    def create_phase_agent(
        self, 
        phase_type: PhaseType, 
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an agent for a specific phase.
        
        Args:
            phase_type: The phase to create an agent for
            state: Current project state for context
            
        Returns:
            Agent configuration dictionary
        """
        phase_config = get_phase_config(phase_type)
        if not phase_config:
            raise ValueError(f"No configuration for phase: {phase_type}")
        
        # Generate dynamic context
        phase_context = generate_phase_context(phase_type.value, state)
        dynamic_todos = generate_phase_todos(phase_type.value, phase_context)
        
        # Filter tools for this phase
        relevant_tools = get_tools_for_phase(phase_type, self.available_tools)
        
        # Build simple prompt
        prompt = self._build_prompt(
            phase_config,
            dynamic_todos,
            state
        )
        
        # Inject dynamic context
        final_prompt = inject_dynamic_context(
            prompt,
            phase_type.value,
            state,
            relevant_tools
        )
        
        return {
            "name": phase_config.name,
            "agent_name": phase_config.agent_name,
            "emoji": phase_config.emoji,
            "prompt": final_prompt,
            "tools": [getattr(tool, 'name', str(tool)) for tool in relevant_tools],
            "phase": phase_type.value,
            "requires_approval": phase_config.requires_approval,
            "required_outputs": phase_config.required_outputs,
        }
    
    def _build_prompt(
        self,
        phase_config,
        dynamic_todos: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> str:
        """Build a simple, focused prompt for the phase."""
        
        todos_text = "\n".join([
            f"- {todo['content']}" 
            for todo in dynamic_todos
        ])
        
        outputs_text = "\n".join([
            f"- {output}" 
            for output in phase_config.required_outputs
        ])
        
        return f"""
You are the {phase_config.agent_name} - {phase_config.emoji} {phase_config.name}

## Mission
{phase_config.goal}

## Your Tasks
{todos_text}

## Required Outputs
{outputs_text}

## Duration Estimate
{phase_config.duration_estimate}

Focus on completing your specific phase objectives efficiently.
"""
    
    def get_current_agent(
        self, 
        current_phase: str, 
        state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get agent for the current phase."""
        try:
            phase_type = PhaseType(current_phase)
            return self.create_phase_agent(phase_type, state)
        except (ValueError, KeyError):
            return None
    
    def validate_transition(
        self, 
        current_phase: str, 
        state: Dict[str, Any]
    ) -> tuple[bool, str, List[str]]:
        """Check if current phase can transition to next."""
        try:
            phase_type = PhaseType(current_phase)
        except ValueError:
            return False, "", [f"Invalid phase: {current_phase}"]
        
        validation = validate_phase_completion(phase_type, state)
        
        if not validation.get('valid', False):
            return False, "", validation.get('errors', [])
        
        next_phase = get_next_phase(phase_type)
        if not next_phase:
            return True, "complete", []
        
        return True, next_phase.value, []


def create_simplified_factory(tools: List[Any]) -> SimplifiedAgentFactory:
    """Create a new simplified agent factory."""
    return SimplifiedAgentFactory(tools)