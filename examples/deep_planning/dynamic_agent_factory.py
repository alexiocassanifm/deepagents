"""
🏎️ Dynamic Agent Factory - FERRARI ENGINE for Deep Planning Agents

This module provides a factory system for creating completely dynamic agents
based on phase configurations. NO MORE STATIC TEMPLATES!

Key Features:
- Factory methods for creating agents from PhaseType configurations
- Dynamic prompt generation based on real project state
- Context-aware tool filtering and TODO generation
- Phase transition validation and management
- Single source of truth from prompt_config.py

This replaces the old static AGENT_CONFIGS system with a fully dynamic approach.
"""

from typing import Dict, Any, List, Optional, Tuple
from prompt_config import (
    PhaseType, 
    get_phase_config, 
    get_tools_for_phase,
    validate_phase_completion,
    get_next_phase,
    get_transition_requirements,
    get_phase_summary
)
from prompt_templates import (
    generate_phase_todos,
    generate_phase_context,
    get_tool_context,
    inject_dynamic_context,
    generate_all_phase_contexts
)


# ============================================================================
# DYNAMIC AGENT FACTORY
# ============================================================================

class DynamicAgentFactory:
    """
    Factory for creating completely dynamic agents from phase configurations.
    
    This replaces the static AGENT_CONFIGS approach with a fully dynamic system
    that adapts to project state and context.
    """
    
    def __init__(self, available_tools: List[Any]):
        """
        Initialize the factory with available tools.
        
        Args:
            available_tools: List of all available tools for filtering
        """
        self.available_tools = available_tools
        self.cached_contexts = {}
    
    def create_agent_from_phase(
        self, 
        phase_type: PhaseType, 
        state: Dict[str, Any], 
        include_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Create a completely dynamic agent from phase configuration.
        
        Args:
            phase_type: Phase type to create agent for
            state: Current project state for context generation
            include_validation: Whether to include validation criteria
            
        Returns:
            Dictionary with complete dynamic agent configuration
        """
        phase_config = get_phase_config(phase_type)
        if not phase_config:
            raise ValueError(f"No configuration found for phase: {phase_type}")
        
        # Generate dynamic context for this phase
        phase_context = generate_phase_context(phase_type.value, state)
        dynamic_todos = generate_phase_todos(phase_type.value, phase_context)
        tool_context = get_tool_context(phase_type.value, self.available_tools)
        
        # Filter tools for this specific phase
        relevant_tools = get_tools_for_phase(phase_type, self.available_tools)
        
        # Create dynamic prompt template
        dynamic_prompt = self._build_phase_prompt(
            phase_config, 
            phase_context, 
            dynamic_todos, 
            tool_context, 
            state
        )
        
        # Inject final dynamic context
        final_prompt = inject_dynamic_context(
            dynamic_prompt,
            phase_type.value,
            state,
            relevant_tools
        )
        
        agent_config = {
            "name": phase_config.name,
            "agent_name": phase_config.agent_name,
            "emoji": phase_config.emoji,
            "description": phase_config.goal,
            "prompt": final_prompt,
            "tools": [getattr(tool, 'name', str(tool)) for tool in relevant_tools],
            "phase": phase_type.value,
            "requires_user_input": phase_config.requires_user_input,
            "requires_approval": phase_config.requires_approval,
            "required_outputs": phase_config.required_outputs,
            "optional_outputs": phase_config.optional_outputs,
            "duration_estimate": phase_config.duration_estimate,
            "completion_weight": phase_config.completion_weight,
            
            # Dynamic components
            "dynamic_todos": dynamic_todos,
            "tool_context": tool_context,
            "phase_context": phase_context,
            "relevant_tools": relevant_tools,
            
            # Validation components (if requested)
            "validation_rules": phase_config.validation_rules if include_validation else [],
            "transition_criteria": phase_config.transition_criteria if include_validation else [],
            "blocking_conditions": phase_config.blocking_conditions if include_validation else []
        }
        
        return agent_config
    
    def _build_phase_prompt(
        self,
        phase_config,
        phase_context: Dict[str, Any],
        dynamic_todos: List[Dict[str, Any]],
        tool_context: Dict[str, Any],
        state: Dict[str, Any]
    ) -> str:
        """
        Build a completely dynamic prompt for the phase.
        
        Returns:
            Dynamic prompt template ready for context injection
        """
        
        # Helper functions (moved from main file)
        def format_todos_for_prompt(todos):
            if not todos:
                return "Nessun task specifico generato"
            formatted = []
            for todo in todos:
                status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(todo.get("status", "pending"), "📋")
                formatted.append(f"{status_emoji} {todo['content']}")
            return "\\n".join(formatted)
        
        def format_outputs_list(outputs):
            if not outputs:
                return "Nessun output specifico richiesto"
            return "\\n".join([f"📄 {output}" for output in outputs])
        
        def format_validation_rules(rules):
            if not rules:
                return "Nessun criterio di validazione specifico"
            formatted = []
            for rule in rules:
                if hasattr(rule, 'description'):
                    status = "✅" if rule.required else "⚠️"
                    formatted.append(f"{status} {rule.description}")
                else:
                    formatted.append(f"📋 {str(rule)}")
            return "\\n".join(formatted)
        
        def format_interaction_points(interaction_points):
            if not interaction_points:
                return "Nessuna interazione umana richiesta"
            return "\\n".join([f"👤 {point}" for point in interaction_points])
        
        # Build the dynamic prompt
        prompt_template = f"""
Sei il {phase_config.agent_name} - {phase_config.emoji} {phase_config.name}

## 🎯 La Tua Missione
{phase_config.goal}

## 📊 Contesto Progetto Attuale
- Progetto: {{project_name}} ({{project_type}})
- Dominio: {{domain}}
- Focus: {{focus_area}}
- Fase: {phase_config.name} ({phase_config.completion_weight}% del processo totale)
- Durata stimata: {phase_config.duration_estimate}

## ⚡ I Tuoi Task Dinamici (Generati per questo Contesto)
{format_todos_for_prompt(dynamic_todos)}

## 🛠️ Strumenti Disponibili ({tool_context['tool_count']} filtrati per questa fase)
{tool_context['tool_categories']}

**Focus fase:** {tool_context['phase_objectives']}

## 📋 Output Richiesti
{format_outputs_list(phase_config.required_outputs)}

## ✅ Criteri di Successo per Questa Fase
{format_validation_rules(phase_config.validation_rules)}

## 👥 Interazioni Umane
{format_interaction_points(phase_config.interaction_points)}

## 🚦 Condizioni di Transizione
Prima di completare questa fase, assicurati che:
{chr(10).join([f"- {criterion}" for criterion in phase_config.transition_criteria])}

## ⚠️ Condizioni Bloccanti
Evita queste situazioni che impedirebbero il progresso:
{chr(10).join([f"- {condition}" for condition in phase_config.blocking_conditions])}

Inizia il tuo lavoro concentrandoti sui task dinamici generati per questo specifico contesto progettuale.
"""
        
        return prompt_template
    
    def create_all_phase_agents(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create dynamic agents for all phases.
        
        Args:
            state: Current project state
            
        Returns:
            List of all dynamic agent configurations
        """
        agents = []
        
        for phase_type in PhaseType:
            if phase_type == PhaseType.COMPLETE:
                continue  # Skip the COMPLETE phase
                
            try:
                agent_config = self.create_agent_from_phase(phase_type, state)
                agents.append(agent_config)
            except Exception as e:
                print(f"⚠️ Failed to create agent for {phase_type.value}: {e}")
                continue
        
        print(f"🏭 Dynamic factory created {len(agents)} agents from phase configurations")
        return agents
    
    def get_current_phase_agent(
        self, 
        current_phase: str, 
        state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get the agent configuration for the current phase.
        
        Args:
            current_phase: Current phase name
            state: Project state
            
        Returns:
            Agent configuration for current phase or None
        """
        try:
            phase_type = PhaseType(current_phase)
            return self.create_agent_from_phase(phase_type, state)
        except (ValueError, KeyError):
            print(f"⚠️ Invalid phase for agent creation: {current_phase}")
            return None
    
    def validate_phase_transition(
        self, 
        current_phase: str, 
        state: Dict[str, Any]
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate if the current phase can transition to the next one.
        
        Args:
            current_phase: Current phase name
            state: Project state
            
        Returns:
            Tuple of (can_transition, next_phase, missing_requirements)
        """
        try:
            phase_type = PhaseType(current_phase)
        except ValueError:
            return False, "", [f"Invalid phase: {current_phase}"]
        
        # Validate current phase completion
        validation_result = validate_phase_completion(phase_type, state)
        
        if not validation_result.get('valid', False):
            errors = validation_result.get('errors', ['Unknown validation errors'])
            return False, "", errors
        
        # Get next phase
        next_phase_type = get_next_phase(phase_type)
        if not next_phase_type:
            return True, "complete", []
        
        return True, next_phase_type.value, []
    
    def get_phase_summary_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of all phases and their status.
        
        Args:
            state: Current project state
            
        Returns:
            Dictionary with complete phase status report
        """
        report = {
            "total_phases": len(PhaseType) - 1,  # Exclude COMPLETE
            "current_phase": state.get("current_phase", "unknown"),
            "completed_phases": state.get("completed_phases", []),
            "phase_details": {},
            "overall_progress": 0
        }
        
        total_weight = 0
        completed_weight = 0
        
        for phase_type in PhaseType:
            if phase_type == PhaseType.COMPLETE:
                continue
                
            phase_config = get_phase_config(phase_type)
            if not phase_config:
                continue
                
            validation_result = validate_phase_completion(phase_type, state)
            is_completed = validation_result.get('valid', False)
            
            phase_summary = get_phase_summary(phase_type)
            phase_summary.update({
                "is_completed": is_completed,
                "validation_errors": validation_result.get('errors', []),
                "transition_ready": len(validation_result.get('errors', [])) == 0
            })
            
            report["phase_details"][phase_type.value] = phase_summary
            
            total_weight += phase_config.completion_weight
            if is_completed:
                completed_weight += phase_config.completion_weight
        
        report["overall_progress"] = (completed_weight / total_weight * 100) if total_weight > 0 else 0
        
        return report


# ============================================================================
# FACTORY UTILITIES
# ============================================================================

def create_dynamic_agent_factory(tools: List[Any]) -> DynamicAgentFactory:
    """
    Create a new dynamic agent factory instance.
    
    Args:
        tools: Available tools for agent creation
        
    Returns:
        Configured DynamicAgentFactory instance
    """
    return DynamicAgentFactory(tools)


def quick_create_phase_agent(
    phase: str, 
    state: Dict[str, Any], 
    tools: List[Any]
) -> Optional[Dict[str, Any]]:
    """
    Quick utility to create an agent for a specific phase.
    
    Args:
        phase: Phase name
        state: Project state
        tools: Available tools
        
    Returns:
        Agent configuration or None if failed
    """
    factory = create_dynamic_agent_factory(tools)
    return factory.get_current_phase_agent(phase, state)


# ============================================================================
# COMPATIBILITY LAYER
# ============================================================================

def migrate_from_static_config(static_agent_configs: Dict[str, Any]) -> Dict[str, str]:
    """
    Helper to migrate from old static AGENT_CONFIGS to dynamic system.
    
    Args:
        static_agent_configs: Old static configurations
        
    Returns:
        Migration mapping of old agent names to phase types
    """
    migration_map = {}
    
    # Map common static agent names to phase types
    name_to_phase = {
        "investigation-agent": PhaseType.INVESTIGATION,
        "discussion-agent": PhaseType.DISCUSSION,
        "planning-agent": PhaseType.PLANNING,
        "task-generation-agent": PhaseType.TASK_GENERATION
    }
    
    for old_name, config in static_agent_configs.items():
        phase = config.get("phase", "unknown")
        if phase in [p.value for p in PhaseType]:
            migration_map[old_name] = phase
            print(f"🔄 Migrated {old_name} -> {phase}")
    
    return migration_map


# ============================================================================
# VALIDATION AND TESTING
# ============================================================================

def validate_factory_setup(factory: DynamicAgentFactory) -> Dict[str, Any]:
    """
    Validate that the dynamic factory is set up correctly.
    
    Args:
        factory: Factory instance to validate
        
    Returns:
        Validation report
    """
    test_state = {
        "project_id": "test_project",
        "project_type": "web_application",
        "project_domain": "e-commerce",
        "current_phase": "investigation"
    }
    
    report = {
        "factory_valid": True,
        "errors": [],
        "created_agents": 0,
        "phase_coverage": []
    }
    
    try:
        agents = factory.create_all_phase_agents(test_state)
        report["created_agents"] = len(agents)
        report["phase_coverage"] = [agent["phase"] for agent in agents]
        
        # Validate each agent has required components
        for agent in agents:
            required_keys = ["name", "prompt", "tools", "phase", "dynamic_todos"]
            missing_keys = [key for key in required_keys if key not in agent]
            if missing_keys:
                report["errors"].append(f"Agent {agent.get('name', 'unknown')} missing: {missing_keys}")
                report["factory_valid"] = False
                
    except Exception as e:
        report["factory_valid"] = False
        report["errors"].append(f"Factory creation failed: {str(e)}")
    
    return report


if __name__ == "__main__":
    """Test the dynamic factory system."""
    print("🧪 Testing Dynamic Agent Factory...")
    
    # Create mock tools for testing
    mock_tools = [
        type('MockTool', (), {'name': 'list_projects', 'description': 'List projects'})(),
        type('MockTool', (), {'name': 'write_file', 'description': 'Write file'})(),
        type('MockTool', (), {'name': 'read_file', 'description': 'Read file'})()
    ]
    
    # Test factory creation
    factory = create_dynamic_agent_factory(mock_tools)
    validation_report = validate_factory_setup(factory)
    
    print(f"🔍 Validation Results:")
    print(f"  ✅ Factory valid: {validation_report['factory_valid']}")
    print(f"  🤖 Agents created: {validation_report['created_agents']}")
    print(f"  📋 Phase coverage: {validation_report['phase_coverage']}")
    
    if validation_report['errors']:
        print(f"  ⚠️ Errors: {validation_report['errors']}")
    
    print("🏎️ Dynamic Agent Factory test completed!")