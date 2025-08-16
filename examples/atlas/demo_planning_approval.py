#!/usr/bin/env python3
"""
Demo of human-in-the-loop planning approval with DeepAgents.

This script shows how the new planning approval functionality works
in practice, with a simplified example.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from deepagents import create_deep_agent, SubAgent
from langgraph.types import Command


def create_demo_agent():
    """Create a simple demo agent with planning approval."""
    
    # Define a documentation subagent that requires approval
    doc_writer = SubAgent(
        name="doc-writer",
        description="Writes documentation with mandatory planning approval",
        prompt="""You are a Documentation Writer with human-in-the-loop planning approval.

CRITICAL WORKFLOW:
1. Before writing any documentation, you MUST use the review_plan tool
2. Create a detailed plan with sections and descriptions  
3. Present it for human approval
4. Only proceed after getting approval

When using review_plan:
- plan_type: "documentation"
- plan_content: Include title, description, and sections array
- Each section needs: title, description, estimated_length, content_type

Example plan_content structure:
{
    "title": "Project Documentation", 
    "description": "Comprehensive project documentation",
    "sections": [
        {
            "title": "Overview",
            "description": "Project introduction and goals",
            "estimated_length": "1-2 pages",
            "content_type": "overview"
        }
    ]
}

NEVER write documentation without first getting plan approval!""",
        requires_approval=True
    )
    
    # Create agent with planning approval enabled
    agent = create_deep_agent(
        tools=[],  # No additional tools needed for demo
        instructions="""You are a demo agent that showcases human-in-the-loop planning approval.

When asked to create documentation:
1. Delegate to the doc-writer subagent
2. The doc-writer will automatically request plan approval
3. The user will see a detailed plan and can approve/edit/reject it
4. Only after approval will documentation be written

This demonstrates the new planning approval workflow in DeepAgents.""",
        subagents=[doc_writer],
        enable_planning_approval=True,
        checkpointer="memory"  # Required for human-in-the-loop
    )
    
    return agent


def demo_with_mock_interaction():
    """Demonstrate the workflow with mock interactions."""
    print("🎭 DEMO: Human-in-the-Loop Planning Approval")
    print("=" * 50)
    
    agent = create_demo_agent()
    
    print("✅ Agent created with planning approval enabled")
    print("💾 Checkpointer configured for state persistence")
    print("🔧 doc-writer subagent requires approval")
    
    print("\n📝 Simulated Interaction:")
    print("-" * 30)
    
    print("👤 User: 'Create documentation for our new API project'")
    print()
    print("🤖 Agent: 'I'll use the doc-writer to create that documentation for you.'")
    print()
    print("📋 doc-writer: *Generates plan and calls review_plan tool*")
    print()
    print("⏸️  INTERRUPT - Plan Review Required:")
    print("""
╭─────────────────────────────────────────╮
│           DOCUMENTATION PLAN            │
├─────────────────────────────────────────┤
│                                         │
│ Title: API Project Documentation        │
│ Type: documentation                     │
│                                         │
│ Sections:                               │
│ 1. API Overview (1-2 pages)            │
│ 2. Authentication (2-3 pages)          │ 
│ 3. Endpoints Reference (3-5 pages)     │
│ 4. Code Examples (2-4 pages)           │
│ 5. Error Handling (1-2 pages)          │
│                                         │
│ Total: ~10 pages estimated             │
│                                         │
├─────────────────────────────────────────┤
│ Options:                                │
│ • approve - Proceed with plan           │
│ • edit: <changes> - Modify plan         │ 
│ • reject - Start over                   │
╰─────────────────────────────────────────╯
""")
    
    print("👤 Human Response Options:")
    print("   ✅ 'approve'")
    print("   ✏️  'edit: add troubleshooting section'")
    print("   ❌ 'reject: too technical, make it more user-friendly'")
    print()
    
    print("▶️  After Approval:")
    print("🤖 Agent continues with documentation writing based on approved plan")
    print("📄 Final documentation follows the exact structure that was approved")
    
    return agent


def show_configuration_example():
    """Show how to configure the planning approval feature."""
    print("\n⚙️  CONFIGURATION EXAMPLE")
    print("=" * 50)
    
    print("""
# How to enable planning approval in your agents:

from deepagents import create_deep_agent, SubAgent

# Define subagent with approval requirement
my_subagent = SubAgent(
    name="content-creator",
    description="Creates content with human approval",
    prompt="Your detailed prompt here...",
    requires_approval=True,  # 🔑 Key: Enable approval
    approval_points=["before_write"]  # Optional: specific points
)

# Create agent with planning features
agent = create_deep_agent(
    tools=your_tools,
    instructions="Your instructions...",
    subagents=[my_subagent], 
    enable_planning_approval=True,  # 🔑 Key: Enable planning
    checkpointer="memory"  # 🔑 Key: Required for interrupts
)

# Usage - the workflow is automatic!
# 1. User requests work from the subagent
# 2. Subagent automatically requests plan approval  
# 3. Human reviews and approves/edits/rejects
# 4. Work proceeds based on approved plan
""")


if __name__ == "__main__":
    print("🚀 DEEPAGENTS PLANNING APPROVAL DEMO")
    print("Showcasing human-in-the-loop planning workflow")
    print("=" * 50)
    
    agent = demo_with_mock_interaction()
    
    show_configuration_example()
    
    print("\n🎯 KEY BENEFITS:")
    print("• Human oversight before content creation")  
    print("• Ability to modify plans before execution")
    print("• Prevents unwanted or incorrect documentation")
    print("• Enables collaborative AI-human workflows")
    
    print("\n🔧 TECHNICAL FEATURES:")
    print("• Built on LangGraph interrupt() mechanism")
    print("• State persistence with checkpointing")
    print("• Automatic plan generation and formatting") 
    print("• Support for plan modifications")
    print("• Integration with existing DeepAgents architecture")
    
    print("\n📚 Try it yourself:")
    print("1. Import the atlas_agent.py")
    print("2. Ask it to generate documentation")
    print("3. Review the plan when prompted")
    print("4. Experience the human-in-the-loop workflow!")