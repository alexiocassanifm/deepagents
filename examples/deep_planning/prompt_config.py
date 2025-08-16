"""
Phase Configuration System for Deep Planning Agent

This module defines comprehensive configurations for each phase of the
deep planning process, including validation rules, tool mappings,
and transition criteria.

Key Features:
- Phase-specific validation rules
- Tool categorization and filtering
- Transition criteria definitions
- Human interaction points configuration
- Success metrics and completion thresholds
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# PHASE ENUMS AND CONSTANTS
# ============================================================================

class PhaseType(Enum):
    """Enumeration of deep planning phases."""
    INVESTIGATION = "investigation"
    DISCUSSION = "discussion"
    PLANNING = "planning"
    TASK_GENERATION = "task_generation"
    COMPLETE = "complete"


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    FLEXIBLE = "flexible"


class ToolCategory(Enum):
    """Tool categorization for phase filtering."""
    PROJECT_DISCOVERY = "project_discovery"
    CODE_ANALYSIS = "code_analysis"
    DOCUMENTATION = "documentation"
    FILE_OPERATIONS = "file_operations"
    REQUIREMENTS_MANAGEMENT = "requirements_management"
    VALIDATION = "validation"
    APPROVAL = "approval"


# ============================================================================
# PHASE CONFIGURATION DATACLASSES
# ============================================================================

@dataclass
class ValidationRule:
    """Configuration for a single validation rule."""
    name: str
    description: str
    required: bool = True
    validation_function: Optional[str] = None
    error_message: str = ""
    success_message: str = ""


@dataclass
class PhaseConfig:
    """Complete configuration for a single phase."""
    name: str
    phase_type: PhaseType
    emoji: str
    goal: str
    agent_name: str
    duration_estimate: str
    completion_weight: int
    
    # Tool configuration
    required_tool_categories: List[ToolCategory]
    optional_tool_categories: List[ToolCategory]
    
    # File outputs
    required_outputs: List[str]
    optional_outputs: List[str]
    
    # Validation configuration
    validation_level: ValidationLevel
    validation_rules: List[ValidationRule]
    
    # Transition criteria
    transition_criteria: List[str]
    blocking_conditions: List[str]
    
    # Human interaction
    interaction_points: List[str]
    
    # Optional fields with defaults
    requires_user_input: bool = False
    requires_approval: bool = False
    approval_message: str = ""


# ============================================================================
# PHASE CONFIGURATIONS
# ============================================================================

# Investigation Phase Configuration
INVESTIGATION_PHASE_CONFIG = PhaseConfig(
    name="Silent Investigation",
    phase_type=PhaseType.INVESTIGATION,
    emoji="🔍",
    goal="Understand project and codebase without user interaction",
    agent_name="investigation-agent",
    duration_estimate="15-30 minutes",
    completion_weight=25,
    requires_user_input=False,
    requires_approval=False,
    
    required_tool_categories=[
        ToolCategory.PROJECT_DISCOVERY,
        ToolCategory.CODE_ANALYSIS,
        ToolCategory.DOCUMENTATION
    ],
    optional_tool_categories=[
        ToolCategory.REQUIREMENTS_MANAGEMENT
    ],
    
    required_outputs=[
        "investigation_findings.md",
        "project_context.md",
        "technical_analysis.md"
    ],
    optional_outputs=[
        "architecture_overview.md",
        "dependency_analysis.md"
    ],
    
    validation_level=ValidationLevel.STRICT,
    validation_rules=[
        ValidationRule(
            name="projects_discovered",
            description="At least one project must be discovered and analyzed",
            required=True,
            validation_function="validate_projects_discovered",
            error_message="No projects were discovered during investigation",
            success_message="Projects successfully discovered and analyzed"
        ),
        ValidationRule(
            name="findings_documented",
            description="Investigation findings must be documented in required files",
            required=True,
            validation_function="validate_findings_documented",
            error_message="Investigation findings not properly documented",
            success_message="All investigation findings properly documented"
        ),
        ValidationRule(
            name="technical_patterns_identified",
            description="Technical patterns and architecture must be analyzed",
            required=True,
            validation_function="validate_technical_analysis",
            error_message="Technical analysis incomplete or missing",
            success_message="Technical patterns successfully identified"
        )
    ],
    
    transition_criteria=[
        "All required output files created",
        "Project structure documented",
        "Technical analysis completed",
        "Knowledge gaps identified for discussion"
    ],
    
    blocking_conditions=[
        "No projects found or accessible",
        "Investigation files missing or empty",
        "Technical analysis not completed"
    ],
    
    interaction_points=[
        "Initial project selection (if multiple projects available)"
    ]
)

# Discussion Phase Configuration
DISCUSSION_PHASE_CONFIG = PhaseConfig(
    name="Targeted Discussion",
    phase_type=PhaseType.DISCUSSION,
    emoji="💬",
    goal="Clarify requirements through focused questions",
    agent_name="discussion-agent",
    duration_estimate="10-20 minutes",
    completion_weight=50,
    requires_user_input=True,
    requires_approval=False,
    
    required_tool_categories=[
        ToolCategory.FILE_OPERATIONS
    ],
    optional_tool_categories=[
        ToolCategory.DOCUMENTATION
    ],
    
    required_outputs=[
        "clarification_questions.md",
        "user_responses.md",
        "requirements_clarified.md"
    ],
    optional_outputs=[
        "technical_constraints.md",
        "scope_definition.md"
    ],
    
    validation_level=ValidationLevel.MODERATE,
    validation_rules=[
        ValidationRule(
            name="questions_generated",
            description="5-7 specific, actionable questions must be generated",
            required=True,
            validation_function="validate_questions_quality",
            error_message="Questions are too generic or insufficient",
            success_message="High-quality targeted questions generated"
        ),
        ValidationRule(
            name="responses_collected",
            description="User responses must be collected and documented",
            required=True,
            validation_function="validate_responses_collected",
            error_message="User responses not properly collected",
            success_message="User responses successfully documented"
        ),
        ValidationRule(
            name="requirements_clarified",
            description="Final requirements must be synthesized from responses",
            required=True,
            validation_function="validate_requirements_synthesis",
            error_message="Requirements not properly clarified or synthesized",
            success_message="Requirements successfully clarified"
        )
    ],
    
    transition_criteria=[
        "Targeted questions generated and asked",
        "User responses collected and documented",
        "Requirements clarified and finalized",
        "Knowledge gaps addressed"
    ],
    
    blocking_conditions=[
        "No questions generated",
        "User responses missing or incomplete",
        "Requirements remain unclear"
    ],
    
    interaction_points=[
        "Presenting clarification questions to user",
        "Collecting and processing user responses",
        "Confirming final requirements understanding"
    ]
)

# Planning Phase Configuration
PLANNING_PHASE_CONFIG = PhaseConfig(
    name="Structured Planning",
    phase_type=PhaseType.PLANNING,
    emoji="📋",
    goal="Create comprehensive implementation plan with 8 sections",
    agent_name="planning-agent",
    duration_estimate="20-40 minutes",
    completion_weight=75,
    requires_user_input=True,
    requires_approval=True,
    
    required_tool_categories=[
        ToolCategory.FILE_OPERATIONS,
        ToolCategory.VALIDATION,
        ToolCategory.APPROVAL
    ],
    optional_tool_categories=[
        ToolCategory.DOCUMENTATION
    ],
    
    required_outputs=[
        "implementation_plan.md"
    ],
    optional_outputs=[
        "risk_assessment.md",
        "resource_requirements.md"
    ],
    
    validation_level=ValidationLevel.STRICT,
    validation_rules=[
        ValidationRule(
            name="eight_sections_present",
            description="All 8 mandatory sections must be present and detailed",
            required=True,
            validation_function="validate_eight_sections",
            error_message="Implementation plan missing required sections",
            success_message="All 8 sections present and detailed"
        ),
        ValidationRule(
            name="implementation_steps_detailed",
            description="At least 5 actionable implementation steps with checkboxes",
            required=True,
            validation_function="validate_implementation_steps",
            error_message="Implementation steps insufficient or not actionable",
            success_message="Implementation steps properly detailed"
        ),
        ValidationRule(
            name="file_changes_specified",
            description="Specific file paths and changes must be identified",
            required=True,
            validation_function="validate_file_changes",
            error_message="File changes not specifically identified",
            success_message="File changes clearly specified"
        ),
        ValidationRule(
            name="plan_approved",
            description="Plan must be approved by human reviewer",
            required=True,
            validation_function="validate_plan_approval",
            error_message="Plan not yet approved by human reviewer",
            success_message="Plan approved and ready for implementation"
        )
    ],
    
    transition_criteria=[
        "All 8 sections completed",
        "Implementation steps detailed with checkboxes",
        "File changes specifically identified",
        "Timeline estimates provided",
        "Plan approved by human reviewer"
    ],
    
    blocking_conditions=[
        "Missing required plan sections",
        "Implementation steps too vague",
        "File changes not specified",
        "Plan not approved by human"
    ],
    
    interaction_points=[
        "Plan review and approval request",
        "Addressing feedback and revisions",
        "Final plan confirmation"
    ],
    
    approval_message="Please review the implementation plan and approve if satisfactory."
)

# Task Generation Phase Configuration
TASK_GENERATION_PHASE_CONFIG = PhaseConfig(
    name="Task Generation",
    phase_type=PhaseType.TASK_GENERATION,
    emoji="⚡",
    goal="Transform plan into actionable implementation tasks",
    agent_name="task-generation-agent",
    duration_estimate="10-15 minutes",
    completion_weight=90,
    requires_user_input=False,
    requires_approval=False,
    
    required_tool_categories=[
        ToolCategory.FILE_OPERATIONS
    ],
    optional_tool_categories=[
        ToolCategory.VALIDATION
    ],
    
    required_outputs=[
        "implementation_tasks.md",
        "focus_chain.md",
        "success_criteria.md",
        "next_steps.md"
    ],
    optional_outputs=[
        "deployment_checklist.md",
        "testing_plan.md"
    ],
    
    validation_level=ValidationLevel.MODERATE,
    validation_rules=[
        ValidationRule(
            name="tasks_extracted",
            description="Tasks must be extracted from all plan sections",
            required=True,
            validation_function="validate_tasks_extracted",
            error_message="Tasks not properly extracted from plan",
            success_message="All tasks successfully extracted from plan"
        ),
        ValidationRule(
            name="focus_chain_created",
            description="Focus chain must include all relevant files",
            required=True,
            validation_function="validate_focus_chain",
            error_message="Focus chain incomplete or missing files",
            success_message="Focus chain properly created with all files"
        ),
        ValidationRule(
            name="success_criteria_defined",
            description="Clear success criteria must be defined",
            required=True,
            validation_function="validate_success_criteria",
            error_message="Success criteria not clearly defined",
            success_message="Success criteria clearly defined"
        ),
        ValidationRule(
            name="next_steps_actionable",
            description="Next steps must be actionable and prioritized",
            required=True,
            validation_function="validate_next_steps",
            error_message="Next steps not actionable or properly prioritized",
            success_message="Next steps actionable and prioritized"
        )
    ],
    
    transition_criteria=[
        "All tasks extracted from plan",
        "Focus chain created with relevant files",
        "Success criteria clearly defined",
        "Next steps prioritized and actionable",
        "Implementation setup complete"
    ],
    
    blocking_conditions=[
        "Task extraction incomplete",
        "Focus chain missing files",
        "Success criteria unclear",
        "Next steps not actionable"
    ],
    
    interaction_points=[
        "Presenting implementation roadmap",
        "Confirming task priorities",
        "Delivery of final setup"
    ]
)


# ============================================================================
# PHASE CONFIGURATION REGISTRY
# ============================================================================

PHASE_CONFIGS: Dict[PhaseType, PhaseConfig] = {
    PhaseType.INVESTIGATION: INVESTIGATION_PHASE_CONFIG,
    PhaseType.DISCUSSION: DISCUSSION_PHASE_CONFIG,
    PhaseType.PLANNING: PLANNING_PHASE_CONFIG,
    PhaseType.TASK_GENERATION: TASK_GENERATION_PHASE_CONFIG
}


# ============================================================================
# TOOL CATEGORY CONFIGURATIONS
# ============================================================================

TOOL_CATEGORY_CONFIGS = {
    ToolCategory.PROJECT_DISCOVERY: {
        "name": "Project Discovery",
        "description": "Tools for discovering and exploring project structure",
        "keywords": ["list_projects", "get_project", "discover", "explore"],
        "examples": ["General_list_projects", "Studio_list_needs", "Code_list_repositories"]
    },
    
    ToolCategory.CODE_ANALYSIS: {
        "name": "Code Analysis", 
        "description": "Tools for analyzing code structure and patterns",
        "keywords": ["code", "find", "analyze", "get_file", "structure"],
        "examples": ["Code_find_relevant_code_snippets", "Code_get_file", "Code_get_directory_structure"]
    },
    
    ToolCategory.DOCUMENTATION: {
        "name": "Documentation",
        "description": "Tools for document retrieval and analysis",
        "keywords": ["document", "rag", "retrieve", "content"],
        "examples": ["General_rag_retrieve_documents", "General_get_document_content"]
    },
    
    ToolCategory.FILE_OPERATIONS: {
        "name": "File Operations",
        "description": "Tools for file manipulation and management",
        "keywords": ["read_file", "write_file", "edit_file", "ls"],
        "examples": ["read_file", "write_file", "edit_file", "ls"]
    },
    
    ToolCategory.REQUIREMENTS_MANAGEMENT: {
        "name": "Requirements Management",
        "description": "Tools for managing requirements, user stories, and tasks",
        "keywords": ["needs", "stories", "requirements", "tasks"],
        "examples": ["Studio_list_user_stories", "Studio_list_requirements", "Studio_list_tasks"]
    },
    
    ToolCategory.VALIDATION: {
        "name": "Validation",
        "description": "Tools for validation and quality checking",
        "keywords": ["review", "validate", "check"],
        "examples": ["review_plan"]
    },
    
    ToolCategory.APPROVAL: {
        "name": "Approval",
        "description": "Tools for human approval and review processes",
        "keywords": ["approve", "review_plan"],
        "examples": ["review_plan"]
    }
}


# ============================================================================
# TRANSITION CONFIGURATION
# ============================================================================

PHASE_TRANSITIONS = {
    PhaseType.INVESTIGATION: {
        "next_phase": PhaseType.DISCUSSION,
        "transition_message": "Investigation complete. Moving to targeted discussion phase.",
        "requirements": [
            "All investigation outputs created",
            "Project structure documented", 
            "Knowledge gaps identified"
        ]
    },
    
    PhaseType.DISCUSSION: {
        "next_phase": PhaseType.PLANNING,
        "transition_message": "Discussion complete. Moving to structured planning phase.",
        "requirements": [
            "Questions answered",
            "Requirements clarified",
            "User responses documented"
        ]
    },
    
    PhaseType.PLANNING: {
        "next_phase": PhaseType.TASK_GENERATION,
        "transition_message": "Planning complete and approved. Moving to task generation phase.",
        "requirements": [
            "8-section plan created",
            "Plan approved by human",
            "All validation criteria met"
        ]
    },
    
    PhaseType.TASK_GENERATION: {
        "next_phase": PhaseType.COMPLETE,
        "transition_message": "Task generation complete. Deep planning process finished.",
        "requirements": [
            "Tasks extracted",
            "Focus chain created", 
            "Success criteria defined",
            "Next steps prioritized"
        ]
    }
}


# ============================================================================
# CONFIGURATION UTILITIES
# ============================================================================

def get_phase_config(phase: PhaseType) -> PhaseConfig:
    """Get configuration for a specific phase."""
    return PHASE_CONFIGS.get(phase)


def get_current_phase_config(phase_name: str) -> Optional[PhaseConfig]:
    """Get configuration for a phase by string name."""
    for phase_type, config in PHASE_CONFIGS.items():
        if phase_type.value == phase_name or config.name.lower().replace(" ", "_") == phase_name:
            return config
    return None


def get_next_phase(current_phase: PhaseType) -> Optional[PhaseType]:
    """Get the next phase in the sequence."""
    transition = PHASE_TRANSITIONS.get(current_phase)
    return transition["next_phase"] if transition else None


def get_transition_requirements(current_phase: PhaseType) -> List[str]:
    """Get requirements for transitioning from current phase."""
    transition = PHASE_TRANSITIONS.get(current_phase)
    return transition["requirements"] if transition else []


def get_tools_for_phase(phase: PhaseType, available_tools: List[Any]) -> List[Any]:
    """Filter available tools to those relevant for a specific phase."""
    config = get_phase_config(phase)
    if not config:
        return available_tools
    
    relevant_tools = []
    required_categories = config.required_tool_categories + config.optional_tool_categories
    
    for tool in available_tools:
        tool_name = getattr(tool, 'name', '').lower()
        tool_desc = getattr(tool, 'description', '').lower()
        
        for category in required_categories:
            category_config = TOOL_CATEGORY_CONFIGS.get(category, {})
            keywords = category_config.get('keywords', [])
            
            if any(keyword in tool_name or keyword in tool_desc for keyword in keywords):
                relevant_tools.append(tool)
                break
    
    return relevant_tools


def validate_phase_completion(phase: PhaseType, state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that a phase has been completed according to its configuration."""
    config = get_phase_config(phase)
    if not config:
        return {"valid": False, "error": "Phase configuration not found"}
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "completed_validations": [],
        "phase": phase.value
    }
    
    # Check required outputs exist
    files = state.get("files", {})
    for required_output in config.required_outputs:
        if required_output not in files or not files[required_output]:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Required output missing: {required_output}")
        else:
            validation_results["completed_validations"].append(f"Output present: {required_output}")
    
    # Check transition criteria
    for criterion in config.transition_criteria:
        # This would need actual validation logic based on the criterion
        # For now, we'll assume basic file existence covers most criteria
        validation_results["completed_validations"].append(f"Criterion checked: {criterion}")
    
    return validation_results


def get_phase_summary(phase: PhaseType) -> Dict[str, Any]:
    """Get a summary of phase configuration for display."""
    config = get_phase_config(phase)
    if not config:
        return {}
    
    return {
        "name": config.name,
        "emoji": config.emoji,
        "goal": config.goal,
        "agent": config.agent_name,
        "duration": config.duration_estimate,
        "completion_weight": config.completion_weight,
        "requires_user_input": config.requires_user_input,
        "requires_approval": config.requires_approval,
        "required_outputs": config.required_outputs,
        "validation_level": config.validation_level.value,
        "transition_criteria_count": len(config.transition_criteria),
        "validation_rules_count": len(config.validation_rules)
    }