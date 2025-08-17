"""
Dynamic Prompt Template System for Deep Planning Agent

This module provides dynamic context generation and template injection
for the optimized deep planning agent prompts.

Key Features:
- Context-aware todo generation based on phase and project state
- Dynamic tool categorization and filtering by phase relevance
- Template variable injection for all prompt types
- Safe formatting with fallback handling
- Phase-specific context generation
"""

from typing import Dict, Any, List, Optional
import re


# ============================================================================
# DYNAMIC TODO GENERATION SYSTEM
# ============================================================================

def generate_phase_todos(phase: str, context: dict) -> List[Dict[str, Any]]:
    """
    Generate context-aware todos for each phase dynamically.
    
    Args:
        phase: Current phase name (investigation, discussion, planning, task_generation)
        context: Dictionary with phase-specific context variables
    
    Returns:
        List of todo dictionaries with id, content, and status
    """
    
    # Define phase-specific todo templates
    todo_templates = {
        "investigation": [
            "Discover available projects in {domain}",
            "Analyze {project_type} architecture and structure", 
            "Gather requirements and user stories for {focus_area}",
            "Explore codebase patterns and dependencies",
            "Document investigation findings in structured format"
        ],
        "discussion": [
            "Review investigation results for {project_name}",
            "Identify knowledge gaps in {unclear_areas}",
            "Generate targeted questions about {requirement_type}",
            "Process and document user responses",
            "Finalize requirements based on clarifications"
        ],
        "planning": [
            "Synthesize findings from {context_sources}",
            "Create Overview section with goals and success criteria",
            "Define Technical Approach for {architecture_type}",
            "Detail Implementation Steps with checkboxes",
            "Complete all 8 required plan sections",
            "Request human approval for implementation plan"
        ],
        "task_generation": [
            "Parse approved plan from {plan_location}",
            "Extract file list from File Changes section",
            "Create focus chain with {file_count} tracked files",
            "Generate task breakdown by priority",
            "Document success criteria and next steps"
        ]
    }
    
    # Get templates for current phase
    templates = todo_templates.get(phase, [])
    
    # Generate todos with context injection
    todos = []
    for i, template in enumerate(templates, 1):
        # Safe format with fallback for missing keys
        try:
            content = template.format(**context)
        except KeyError as e:
            # Fallback to template without substitution if key missing
            content = template.replace("{" + str(e.args[0]) + "}", f"[{e.args[0]}]")
        
        todo = {
            "id": f"{phase[:3]}{i}",
            "content": content,
            "status": "pending"
        }
        todos.append(todo)
    
    return todos


def generate_phase_context(phase: str, state: dict) -> dict:
    """
    Generate phase-specific context for todo generation.
    
    Args:
        phase: Current phase name
        state: Current agent state
    
    Returns:
        Context dictionary for todo template formatting
    """
    
    base_context = {
        "domain": state.get("project_domain", "software development"),
        "project_type": state.get("project_type", "application"),
        "project_name": state.get("project_name", "current project"),
        "focus_area": state.get("focus_area", "core functionality")
    }
    
    phase_contexts = {
        "investigation": {
            **base_context,
        },
        "discussion": {
            **base_context,
            "unclear_areas": ", ".join(state.get("knowledge_gaps", ["requirements"])),
            "requirement_type": state.get("requirement_type", "functional")
        },
        "planning": {
            **base_context,
            "context_sources": "investigation and discussion phases",
            "architecture_type": state.get("architecture_type", "modular")
        },
        "task_generation": {
            **base_context,
            "plan_location": "implementation_plan.md",
            "file_count": len(state.get("files_to_track", []))
        }
    }
    
    return phase_contexts.get(phase, base_context)


# ============================================================================
# DYNAMIC TOOL CONTEXT GENERATION
# ============================================================================

def get_tool_context(phase: str, available_tools: List[Any]) -> dict:
    """
    Generate dynamic tool context for current phase.
    
    Args:
        phase: Current phase name
        available_tools: List of available tool objects
    
    Returns:
        Dictionary with tool context for prompt injection
    """
    
    # Define phase-relevant tool patterns
    phase_tool_patterns = {
        "investigation": {
            "patterns": ["list", "get", "find", "retrieve", "explore"],
            "categories": ["Discovery", "Analysis", "Documentation"],
            "objectives": "comprehensive project understanding"
        },
        "discussion": {
            "patterns": ["read", "write", "edit"],
            "categories": ["File Operations", "Documentation"],
            "objectives": "requirements clarification"
        },
        "planning": {
            "patterns": ["write", "edit", "review"],
            "categories": ["Documentation", "Validation", "Approval"],
            "objectives": "comprehensive plan creation"
        },
        "task_generation": {
            "patterns": ["read", "write", "extract"],
            "categories": ["File Operations", "Task Management"],
            "objectives": "implementation setup"
        }
    }
    
    phase_config = phase_tool_patterns.get(phase, {
        "patterns": [],
        "categories": ["General"],
        "objectives": "phase completion"
    })
    
    # Filter tools relevant to current phase
    relevant_tools = []
    for tool in available_tools:
        tool_name = getattr(tool, 'name', '').lower()
        if any(pattern in tool_name for pattern in phase_config["patterns"]):
            relevant_tools.append(tool)
    
    # Categorize tools
    tool_categories = {}
    for category in phase_config["categories"]:
        tool_categories[category] = [
            tool for tool in relevant_tools
            if category.lower() in getattr(tool, 'description', '').lower()
        ]
    
    # Format categories for prompt
    formatted_categories = []
    for category, tools in tool_categories.items():
        if tools:
            tool_names = [getattr(t, 'name', 'unknown') for t in tools[:3]]
            formatted_categories.append(
                f"- {category}: {', '.join(tool_names)} ({len(tools)} tools)"
            )
    
    return {
        "tool_count": len(relevant_tools),
        "current_phase": phase,
        "tool_categories": "\n".join(formatted_categories) or "- General tools available",
        "phase_objectives": phase_config["objectives"],
        "available_tools": [getattr(t, 'name', 'unknown') for t in relevant_tools]
    }


def categorize_tools_by_function(tools: List[Any]) -> dict:
    """
    Categorize tools by their primary function.
    
    Args:
        tools: List of tool objects
    
    Returns:
        Dictionary mapping categories to tool lists
    """
    
    categories = {
        "Project Discovery": [],
        "Code Analysis": [],
        "Documentation": [],
        "File Operations": [],
        "Requirements Management": [],
        "Validation": []
    }
    
    # Keywords for categorization
    category_keywords = {
        "Project Discovery": ["list_projects", "get_project", "discover"],
        "Code Analysis": ["code", "find", "analyze", "get_file"],
        "Documentation": ["document", "rag", "retrieve"],
        "File Operations": ["read_file", "write_file", "edit_file"],
        "Requirements Management": ["needs", "stories", "requirements", "tasks"],
        "Validation": ["review", "validate", "check"]
    }
    
    for tool in tools:
        tool_name = getattr(tool, 'name', '').lower()
        tool_desc = getattr(tool, 'description', '').lower()
        
        categorized = False
        for category, keywords in category_keywords.items():
            if any(kw in tool_name or kw in tool_desc for kw in keywords):
                categories[category].append(tool)
                categorized = True
                break
        
        if not categorized:
            # Default category for uncategorized tools
            if "File Operations" in categories:
                categories["File Operations"].append(tool)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


# ============================================================================
# DYNAMIC PROMPT INJECTION SYSTEM
# ============================================================================

def inject_dynamic_context(prompt_template: str, phase: str, state: dict, tools: List[Any]) -> str:
    """
    Inject dynamic context into prompt templates.
    
    Args:
        prompt_template: Template string with placeholders
        phase: Current phase name
        state: Current agent state
        tools: Available tools list
    
    Returns:
        Prompt with injected context
    """
    
    # Generate all context components
    tool_context = get_tool_context(phase, tools)
    phase_context = generate_phase_context(phase, state)
    
    # Combine contexts
    full_context = {
        **tool_context,
        **phase_context,
        "current_phase": phase,
        "completed_phases": ", ".join(state.get("completed_phases", [])),
        "context_summary": state.get("context_summary", "Initial phase"),
        "completion_percentage": calculate_completion_percentage(phase),
        "recommended_agent": get_recommended_agent(phase),
        "agent_context": get_agent_context_summary(state, phase),
        "expected_outputs": get_expected_outputs(phase),
        "phase_success_criteria": get_phase_criteria(phase),
        "validation_criteria": get_validation_checklist(phase),
        "recommended_next_action": get_next_action(phase, state),
        "project_id": state.get("project_id", "unknown"),
        "investigation_focus": state.get("investigation_focus", "general project analysis"),
        "investigation_files": ", ".join(state.get("investigation_files", [])),
        "knowledge_gaps": ", ".join(state.get("knowledge_gaps", ["general requirements"])),
        "investigation_summary": state.get("investigation_summary", "Investigation phase results"),
        "clarifications_summary": state.get("clarifications_summary", "User clarifications"),
        "requirements_summary": state.get("requirements_summary", "Final requirements"),
        "feature_name": state.get("feature_name", "New Feature"),
        "plan_file": state.get("plan_file", "implementation_plan.md"),
        "plan_sections": ", ".join(state.get("plan_sections", ["8 sections"])),
        "scope_summary": state.get("scope_summary", "Implementation scope")
    }
    
    # Safe format with defaults
    formatted_prompt = prompt_template
    for key, value in full_context.items():
        placeholder = "{" + key + "}"
        if placeholder in formatted_prompt:
            formatted_prompt = formatted_prompt.replace(placeholder, str(value))
    
    return formatted_prompt


# ============================================================================
# HELPER FUNCTIONS FOR CONTEXT GENERATION
# ============================================================================

def calculate_completion_percentage(phase: str) -> int:
    """Calculate overall process completion percentage."""
    phase_weights = {
        "investigation": 25,
        "discussion": 50,
        "planning": 75,
        "task_generation": 90,
        "complete": 100
    }
    return phase_weights.get(phase, 0)


def get_recommended_agent(phase: str) -> str:
    """Get the recommended agent for current phase."""
    agents = {
        "investigation": "investigation-agent",
        "discussion": "discussion-agent", 
        "planning": "planning-agent",
        "task_generation": "task-generation-agent"
    }
    return agents.get(phase, "none")


def get_expected_outputs(phase: str) -> str:
    """Get expected outputs for current phase."""
    outputs = {
        "investigation": "investigation_findings.md, project_context.md, technical_analysis.md",
        "discussion": "clarification_questions.md, user_responses.md, requirements_clarified.md",
        "planning": "implementation_plan.md with 8 sections, approval confirmation",
        "task_generation": "implementation_tasks.md, focus_chain.md, success_criteria.md"
    }
    return outputs.get(phase, "phase outputs")


def get_phase_criteria(phase: str) -> str:
    """Get success criteria for current phase."""
    criteria = {
        "investigation": "All project areas explored and documented",
        "discussion": "Requirements clarified and documented",
        "planning": "8-section plan created and approved",
        "task_generation": "Tasks generated and tracking setup complete"
    }
    return criteria.get(phase, "phase completion")


def get_validation_checklist(phase: str) -> str:
    """Get validation checklist for phase completion."""
    checklists = {
        "investigation": "- [ ] Projects discovered\n- [ ] Structure analyzed\n- [ ] Findings documented",
        "discussion": "- [ ] Questions generated\n- [ ] Responses collected\n- [ ] Requirements finalized",
        "planning": "- [ ] All 8 sections present\n- [ ] Plan detailed\n- [ ] Approval received",
        "task_generation": "- [ ] Tasks created\n- [ ] Focus chain defined\n- [ ] Success criteria documented"
    }
    return checklists.get(phase, "- [ ] Phase tasks complete")


def get_next_action(phase: str, state: dict) -> str:
    """Determine the next recommended action."""
    if not state.get(f"{phase}_complete", False):
        return f"Deploy {get_recommended_agent(phase)} to complete current phase"
    
    next_phase = {
        "investigation": "discussion",
        "discussion": "planning",
        "planning": "task_generation", 
        "task_generation": "complete"
    }.get(phase, "review")
    
    if next_phase == "complete":
        return "All phases complete - deliver results to user"
    return f"Transition to {next_phase} phase"


def get_agent_context_summary(state: dict, phase: str) -> str:
    """Generate a summary of context to pass to sub-agent."""
    context_items = []
    
    if phase == "discussion" and "investigation_findings" in state.get("files", {}):
        context_items.append("Investigation findings available")
    
    if phase == "planning":
        if "requirements_clarified" in state.get("files", {}):
            context_items.append("Clarified requirements available")
        if "investigation_findings" in state.get("files", {}):
            context_items.append("Investigation results available")
    
    if phase == "task_generation" and "implementation_plan" in state.get("files", {}):
        context_items.append("Approved implementation plan available")
    
    return ", ".join(context_items) if context_items else "Initial context"


# ============================================================================
# PROMPT TEMPLATE UTILITIES
# ============================================================================

def validate_template_variables(template: str) -> List[str]:
    """
    Extract and validate all template variables in a prompt template.
    
    Args:
        template: Prompt template string
    
    Returns:
        List of template variable names found
    """
    # Find all {variable} patterns
    variables = re.findall(r'\{([^}]+)\}', template)
    return list(set(variables))  # Remove duplicates


def get_missing_variables(template: str, context: dict) -> List[str]:
    """
    Identify template variables that are missing from context.
    
    Args:
        template: Prompt template string
        context: Available context dictionary
    
    Returns:
        List of missing variable names
    """
    required_vars = validate_template_variables(template)
    missing_vars = [var for var in required_vars if var not in context]
    return missing_vars


def create_context_report(phase: str, state: dict, tools: List[Any]) -> dict:
    """
    Generate a comprehensive context report for debugging.
    
    Args:
        phase: Current phase name
        state: Current agent state
        tools: Available tools list
    
    Returns:
        Dictionary with context analysis
    """
    tool_context = get_tool_context(phase, tools)
    phase_context = generate_phase_context(phase, state)
    
    return {
        "phase": phase,
        "tool_context": tool_context,
        "phase_context": phase_context,
        "recommended_agent": get_recommended_agent(phase),
        "completion_percentage": calculate_completion_percentage(phase),
        "validation_criteria": get_validation_checklist(phase),
        "next_action": get_next_action(phase, state),
        "context_completeness": {
            "has_project_id": "project_id" in state,
            "has_investigation_results": "investigation_findings" in state.get("files", {}),
            "has_clarifications": "requirements_clarified" in state.get("files", {}),
            "has_approved_plan": "implementation_plan" in state.get("files", {})
        }
    }


# ============================================================================
# BATCH CONTEXT GENERATION
# ============================================================================

def generate_all_phase_contexts(state: dict, tools: List[Any]) -> dict:
    """
    Generate context for all phases at once for planning purposes.
    
    Args:
        state: Current agent state
        tools: Available tools list
    
    Returns:
        Dictionary mapping phase names to their contexts
    """
    phases = ["investigation", "discussion", "planning", "task_generation"]
    contexts = {}
    
    for phase in phases:
        contexts[phase] = {
            "tool_context": get_tool_context(phase, tools),
            "phase_context": generate_phase_context(phase, state),
            "todos": generate_phase_todos(phase, generate_phase_context(phase, state)),
            "completion_percentage": calculate_completion_percentage(phase),
            "recommended_agent": get_recommended_agent(phase),
            "expected_outputs": get_expected_outputs(phase)
        }
    
    return contexts


def generate_orchestrator_context(current_phase: str, state: dict, tools: List[Any]) -> dict:
    """
    Generate comprehensive context specifically for the main orchestrator.
    
    Args:
        current_phase: Current phase name
        state: Current agent state
        tools: Available tools list
    
    Returns:
        Dictionary with orchestrator-specific context
    """
    base_context = {
        "current_phase": current_phase,
        "project_id": state.get("project_id", "unknown"),
        "tool_count": len(tools),
        "completion_percentage": calculate_completion_percentage(current_phase),
        "recommended_agent": get_recommended_agent(current_phase),
        "context_summary": get_agent_context_summary(state, current_phase),
        "expected_outputs": get_expected_outputs(current_phase),
        "validation_criteria": get_phase_criteria(current_phase),
        "recommended_next_action": get_next_action(current_phase, state)
    }
    
    return base_context