"""
Planning module for deepagents with human-in-the-loop approval.

This module provides planning capabilities that allow for human review and approval
of execution plans before implementation.
"""

from typing import Dict, Any, List, Optional, Literal
from langgraph.types import interrupt, Command
from dataclasses import dataclass
from enum import Enum


class PlanStatus(Enum):
    """Status of a plan."""
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class Plan:
    """Represents an execution plan."""
    id: str
    type: str  # "documentation", "implementation", etc.
    title: str
    description: str
    sections: List[Dict[str, Any]]
    status: PlanStatus = PlanStatus.PENDING
    feedback: Optional[str] = None
    

class DocumentationPlanner:
    """Planner specialized for documentation generation with human approval."""
    
    def __init__(self, enable_sequential_thinking: bool = False):
        """
        Initialize the documentation planner.
        
        Args:
            enable_sequential_thinking: Whether to use MCP sequential-thinking for planning
        """
        self.enable_sequential_thinking = enable_sequential_thinking
    
    def create_documentation_plan(
        self,
        context: Dict[str, Any],
        requirements: List[str],
        target_audience: str = "technical"
    ) -> Plan:
        """
        Create a documentation plan based on context and requirements.
        
        Args:
            context: Project context including analysis results
            requirements: List of documentation requirements
            target_audience: Target audience for the documentation
            
        Returns:
            Plan: A structured documentation plan
        """
        # Generate plan based on context
        sections = self._generate_sections(context, requirements, target_audience)
        
        plan = Plan(
            id=f"doc_plan_{hash(str(context))}", 
            type="documentation",
            title=f"Documentation Plan for {context.get('project_name', 'Project')}",
            description=f"Comprehensive documentation plan targeting {target_audience} audience",
            sections=sections
        )
        
        return plan
    
    def _generate_sections(
        self, 
        context: Dict[str, Any], 
        requirements: List[str],
        target_audience: str
    ) -> List[Dict[str, Any]]:
        """Generate documentation sections based on context."""
        sections = []
        
        # Executive Summary (always first)
        sections.append({
            "title": "Executive Summary",
            "description": "High-level overview and key findings",
            "estimated_length": "1-2 pages",
            "content_type": "summary"
        })
        
        # Project Overview
        if context.get("project_info"):
            sections.append({
                "title": "Project Overview", 
                "description": "Project description, goals, and scope",
                "estimated_length": "2-3 pages",
                "content_type": "overview"
            })
        
        # Technical Architecture (if technical context available)
        if context.get("technical_analysis"):
            sections.append({
                "title": "Technical Architecture",
                "description": "System architecture, components, and design patterns", 
                "estimated_length": "3-5 pages",
                "content_type": "technical"
            })
        
        # Implementation Analysis
        if context.get("code_analysis"):
            sections.append({
                "title": "Implementation Analysis",
                "description": "Code structure, patterns, and technical decisions",
                "estimated_length": "4-6 pages", 
                "content_type": "technical"
            })
        
        # Requirements and User Stories
        if context.get("requirements") or context.get("user_stories"):
            sections.append({
                "title": "Requirements Analysis",
                "description": "Functional and non-functional requirements",
                "estimated_length": "2-4 pages",
                "content_type": "requirements"
            })
        
        # Recommendations
        sections.append({
            "title": "Recommendations",
            "description": "Actionable recommendations and next steps",
            "estimated_length": "1-2 pages", 
            "content_type": "recommendations"
        })
        
        # Add custom sections based on requirements
        for req in requirements:
            if any(keyword in req.lower() for keyword in ["security", "performance", "testing"]):
                sections.append({
                    "title": req.title(),
                    "description": f"Detailed analysis of {req.lower()}",
                    "estimated_length": "2-3 pages",
                    "content_type": "analysis"
                })
        
        return sections
    
    def request_plan_approval(self, plan: Plan) -> Dict[str, Any]:
        """
        Request human approval for a documentation plan using LangGraph interrupt.
        
        Args:
            plan: The plan to request approval for
            
        Returns:
            Dict containing the approval response
        """
        # Format plan for human review
        formatted_plan = self._format_plan_for_review(plan)
        
        # Use LangGraph interrupt to pause for human input
        response = interrupt({
            "type": "plan_approval_request",
            "plan_id": plan.id,
            "plan_type": plan.type,
            "formatted_plan": formatted_plan,
            "options": {
                "approve": "Approve plan as-is and proceed with documentation",
                "edit": "Request modifications to the plan",
                "reject": "Reject plan and request complete replanning"
            },
            "instructions": "Please review the documentation plan and choose an action"
        })
        
        return response
    
    def _format_plan_for_review(self, plan: Plan) -> str:
        """Format a plan for human review."""
        formatted = f"""# {plan.title}

## Description
{plan.description}

## Planned Sections

"""
        
        for i, section in enumerate(plan.sections, 1):
            formatted += f"""### {i}. {section['title']}
**Description:** {section['description']}
**Estimated Length:** {section['estimated_length']}
**Content Type:** {section['content_type']}

"""
        
        formatted += f"""
## Summary
- **Total Sections:** {len(plan.sections)}
- **Estimated Total Length:** {self._estimate_total_length(plan.sections)}
- **Plan ID:** {plan.id}
"""
        
        return formatted
    
    def _estimate_total_length(self, sections: List[Dict[str, Any]]) -> str:
        """Estimate total documentation length."""
        total_pages = 0
        for section in sections:
            length = section.get('estimated_length', '1 page')
            # Extract numbers from length strings like "2-3 pages"
            import re
            numbers = re.findall(r'\d+', length)
            if numbers:
                # Take the average of the range or the single number
                if len(numbers) >= 2:
                    total_pages += (int(numbers[0]) + int(numbers[1])) / 2
                else:
                    total_pages += int(numbers[0])
            else:
                total_pages += 1  # Default fallback
        
        return f"{int(total_pages)} pages (estimated)"
    
    def process_approval_response(
        self, 
        plan: Plan, 
        response: Dict[str, Any]
    ) -> tuple[Plan, Command]:
        """
        Process the human approval response and return updated plan and command.
        
        Args:
            plan: The original plan
            response: Human approval response
            
        Returns:
            Tuple of (updated_plan, command_for_graph)
        """
        action = response.get("action", "reject")
        
        if action == "approve":
            plan.status = PlanStatus.APPROVED
            return plan, Command(update={"approved_plan": plan})
            
        elif action == "edit":
            modifications = response.get("modifications", {})
            feedback = response.get("feedback", "")
            
            # Apply modifications to plan
            updated_plan = self._apply_modifications(plan, modifications, feedback)
            updated_plan.status = PlanStatus.MODIFIED
            
            return updated_plan, Command(update={"pending_plan": updated_plan})
            
        else:  # reject
            plan.status = PlanStatus.REJECTED
            plan.feedback = response.get("feedback", "Plan rejected by user")
            
            # Command to restart planning process
            return plan, Command(goto="planning_node")
    
    def _apply_modifications(
        self, 
        plan: Plan, 
        modifications: Dict[str, Any],
        feedback: str
    ) -> Plan:
        """Apply user modifications to a plan."""
        # Create a modified copy
        modified_plan = Plan(
            id=f"{plan.id}_modified",
            type=plan.type,
            title=modifications.get("title", plan.title),
            description=modifications.get("description", plan.description),
            sections=plan.sections.copy(),
            status=PlanStatus.MODIFIED,
            feedback=feedback
        )
        
        # Apply section modifications
        if "sections" in modifications:
            section_mods = modifications["sections"]
            
            # Add new sections
            if "add" in section_mods:
                for new_section in section_mods["add"]:
                    modified_plan.sections.append(new_section)
            
            # Remove sections
            if "remove" in section_mods:
                indices_to_remove = section_mods["remove"]
                modified_plan.sections = [
                    section for i, section in enumerate(modified_plan.sections)
                    if i not in indices_to_remove
                ]
            
            # Modify existing sections
            if "modify" in section_mods:
                for index, changes in section_mods["modify"].items():
                    if 0 <= index < len(modified_plan.sections):
                        modified_plan.sections[index].update(changes)
        
        return modified_plan


# Utility functions for integration with subagents

def create_planning_workflow_node(planner: DocumentationPlanner):
    """Create a LangGraph node that handles the planning workflow."""
    
    def planning_node(state):
        """Node that generates and requests approval for a plan."""
        context = state.get("analysis_results", {})
        requirements = state.get("documentation_requirements", [])
        target_audience = state.get("target_audience", "technical")
        
        # Generate plan
        plan = planner.create_documentation_plan(context, requirements, target_audience)
        
        # Request approval
        response = planner.request_plan_approval(plan)
        
        # Process response
        updated_plan, command = planner.process_approval_response(plan, response)
        
        # Update state and execute command
        state.update({"current_plan": updated_plan})
        return command
    
    return planning_node