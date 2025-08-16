from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command, interrupt
from langchain_core.messages import ToolMessage
from typing import Annotated, Dict, Any, List
from langgraph.prebuilt import InjectedState

from deepagents.prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
)
from deepagents.state import Todo, DeepAgentState, PlanInfo


@tool(description=WRITE_TODOS_DESCRIPTION)
async def write_todos(
    todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todo list to {todos}", tool_call_id=tool_call_id)
            ],
        }
    )


async def ls(state: Annotated[DeepAgentState, InjectedState]) -> list[str]:
    """List all files"""
    return list(state.get("files", {}).keys())


@tool(description=TOOL_DESCRIPTION)
async def read_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file."""
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get file content
    content = mock_filesystem[file_path]

    # Handle empty file
    if not content or content.strip() == "":
        return "System reminder: File exists but has empty contents"

    # Split content into lines
    lines = content.splitlines()

    # Apply line offset and limit
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    # Handle case where offset is beyond file length
    if start_idx >= len(lines):
        return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

    # Format output with line numbers (cat -n format)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1, so add 1 to the index
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return "\n".join(result_lines)


async def write_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Write to a file."""
    files = state.get("files", {})
    files[file_path] = content
    return Command(
        update={
            "files": files,
            "messages": [
                ToolMessage(f"Updated file {file_path}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool(description=EDIT_DESCRIPTION)
async def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    replace_all: bool = False,
) -> str:
    """Write to a file."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get current file content
    content = mock_filesystem[file_path]

    # Check if old_string exists in the file
    if old_string not in content:
        return f"Error: String not found in file: '{old_string}'"

    # If not replace_all, check for uniqueness
    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."
        elif occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

    # Perform the replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacement_count = content.count(old_string)
        result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{file_path}'"
    else:
        new_content = content.replace(
            old_string, new_string, 1
        )  # Replace only first occurrence
        result_msg = f"Successfully replaced string in '{file_path}'"

    # Update the mock filesystem
    mock_filesystem[file_path] = new_content
    return Command(
        update={
            "files": mock_filesystem,
            "messages": [
                ToolMessage(f"Updated file {file_path}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool
async def review_plan(
    plan_type: str,
    plan_content: Dict[str, Any],
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Present a plan for human review and approval before execution.
    
    This tool stores the plan for review and returns immediately. The actual human
    review happens through LangGraph's interrupt mechanism at the graph level.
    
    Args:
        plan_type: Type of plan (e.g., "documentation", "implementation", "analysis")
        plan_content: The plan structure with sections and details
        state: Current agent state
        tool_call_id: ID of the tool call for response tracking
        
    Returns:
        Command: LangGraph command with updated state and immediate ToolMessage response
    """
    # Format plan for human review
    formatted_plan = _format_plan_for_review(plan_type, plan_content)
    
    # Create a pending plan object
    pending_plan = PlanInfo(
        id=f"plan_{hash(str(plan_content))}",
        type=plan_type,
        title=plan_content.get("title", f"{plan_type.title()} Plan"),
        description=plan_content.get("description", ""),
        sections=plan_content.get("sections", []),
        status="pending"
    )
    
    # Store the plan for review and trigger interrupt at graph level
    return Command(
        update={
            "pending_plan": pending_plan,
            "plan_review_data": {
                "type": "plan_review_request",
                "plan_type": plan_type,
                "formatted_plan": formatted_plan,
                "raw_plan": plan_content,
                "options": {
                    "approve": "Approve plan as-is and proceed with execution",
                    "edit": "Request specific modifications to the plan",
                    "reject": "Reject plan completely and request replanning"
                },
                "instructions": """Please review the plan above and respond with one of the following:

1. Type 'approve' to proceed with the plan as-is
2. Type 'edit' followed by your requested changes
3. Type 'reject' to completely restart the planning process

Example responses:
- approve
- edit: Add a security analysis section and expand the technical architecture section
- reject: The plan doesn't address the main requirements"""
            },
            "messages": [
                ToolMessage(
                    f"Plan submitted for review. Plan type: {plan_type}. Waiting for human approval...",
                    tool_call_id=tool_call_id
                )
            ]
        },
        # Use interrupt after returning the tool message
        goto="human_review_node"  # This will trigger the interrupt at graph level
    )


def _format_plan_for_review(plan_type: str, plan_content: Dict[str, Any]) -> str:
    """Format a plan for human review."""
    title = plan_content.get("title", f"{plan_type.title()} Plan")
    description = plan_content.get("description", "No description provided")
    sections = plan_content.get("sections", [])
    
    formatted = f"""# {title}

## Plan Type
{plan_type.title()}

## Description
{description}

## Planned Sections
"""
    
    if sections:
        for i, section in enumerate(sections, 1):
            section_title = section.get("title", f"Section {i}")
            section_desc = section.get("description", "No description")
            section_length = section.get("estimated_length", "Unknown length")
            content_type = section.get("content_type", "general")
            
            formatted += f"""
### {i}. {section_title}
- **Description:** {section_desc}
- **Estimated Length:** {section_length}
- **Content Type:** {content_type}
"""
    else:
        formatted += "\n*No sections defined*\n"
    
    formatted += f"""
## Summary
- **Total Sections:** {len(sections)}
- **Plan Type:** {plan_type}
"""
    
    if sections:
        total_estimated = sum(
            _extract_page_estimate(section.get("estimated_length", "1 page"))
            for section in sections
        )
        formatted += f"- **Estimated Total Length:** {total_estimated} pages\n"
    
    return formatted


def _extract_page_estimate(length_str: str) -> float:
    """Extract page estimate from length string."""
    import re
    numbers = re.findall(r'\d+', str(length_str))
    if len(numbers) >= 2:
        return (int(numbers[0]) + int(numbers[1])) / 2
    elif len(numbers) == 1:
        return int(numbers[0])
    else:
        return 1.0  # Default


def _parse_human_response(response: str) -> Dict[str, Any]:
    """Parse human response into structured action."""
    response = response.strip().lower()
    
    if response == "approve":
        return {"type": "approve"}
    
    elif response.startswith("edit"):
        # Extract modifications after "edit:"
        if ":" in response:
            modifications = response.split(":", 1)[1].strip()
        else:
            modifications = response.replace("edit", "").strip()
        
        return {
            "type": "edit",
            "modifications": modifications
        }
    
    elif response.startswith("reject"):
        # Extract reason after "reject:"
        if ":" in response:
            reason = response.split(":", 1)[1].strip()
        else:
            reason = "Plan rejected by user"
        
        return {
            "type": "reject",
            "reason": reason
        }
    
    else:
        # Default to approve if unclear
        return {"type": "approve"}


def _apply_plan_modifications(plan_content: Dict[str, Any], modifications: str) -> Dict[str, Any]:
    """Apply text-based modifications to a plan."""
    # This is a simple implementation - in practice you might want more sophisticated parsing
    modified_plan = plan_content.copy()
    
    # Add modification notes to description
    current_desc = modified_plan.get("description", "")
    modified_plan["description"] = f"{current_desc}\n\n**Modifications requested:** {modifications}"
    
    # Simple keyword-based modifications
    if "security" in modifications.lower():
        sections = modified_plan.get("sections", [])
        sections.append({
            "title": "Security Analysis",
            "description": "Security considerations and recommendations",
            "estimated_length": "2-3 pages",
            "content_type": "security"
        })
        modified_plan["sections"] = sections
    
    if "expand" in modifications.lower() and "architecture" in modifications.lower():
        sections = modified_plan.get("sections", [])
        for section in sections:
            if "architecture" in section.get("title", "").lower():
                section["description"] += " (expanded per user request)"
                # Increase estimated length
                current_length = section.get("estimated_length", "2-3 pages")
                if "2-3" in current_length:
                    section["estimated_length"] = "4-6 pages"
    
    return modified_plan
