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
from typing import Dict, Any, List, Optional, Literal
from deepagents import create_deep_agent

# Import compatibility system
from tool_compatibility import apply_tool_compatibility_fixes, setup_compatibility_logging
from model_compatibility import (
    detect_model_from_environment, 
    should_apply_compatibility_fixes,
    print_model_compatibility_report,
    default_registry
)

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

async def load_fairmind_mcp_tools() -> List[Any]:
    """
    Load MCP tools from the fairmind MCP server using LangChain MCP adapters.
    
    Returns a list of LangChain-compatible tools that can be used with DeepAgents.
    Falls back to demo tools if MCP server is not available.
    """
    if not MCP_AVAILABLE:
        print("⚠️ MCP adapters not available, using fallback tools")
        return get_fallback_tools()
    
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
                    'Studio_list_tasks',
                    'Studio_get_task',
                    'Studio_list_requirements',
                    'Studio_get_requirement',
                    'Code_list_repositories',
                    'Code_get_directory_structure',
                    'Code_find_relevant_code_snippets',
                    'Code_get_file',
                    'Code_find_usages'
                ]
            )
        ]
        
        print(f"🎯 Found {len(fairmind_tools)} relevant fairmind tools")
        return fairmind_tools
        
    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        print("🔄 Falling back to demo tools")
        return get_fallback_tools()


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
    """
    try:
        # Try to load MCP tools asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mcp_tools = loop.run_until_complete(load_fairmind_mcp_tools())
        loop.close()
        return mcp_tools
    except Exception as e:
        print(f"⚠️ Failed to initialize MCP tools: {e}")
        print("🔄 Using fallback demo tools")
        return get_fallback_tools()


# Initialize MCP tools
print("🏗️ Initializing Deep Planning Agent with MCP integration...")
deep_planning_tools = initialize_deep_planning_mcp_tools()

# Apply compatibility fixes to tools if needed
if ENABLE_COMPATIBILITY_FIXES:
    print("🔧 Applying compatibility fixes to tools...")
    # Note: MCP tools don't need fixing, but deepagents built-in tools will be fixed in create_deep_agent
    print("✅ MCP tools prepared (fixes will be applied to deepagents built-in tools)")


# ============================================================================
# SUB-AGENT CONFIGURATIONS FOR 4-PHASE DEEP PLANNING
# ============================================================================

# Sub-Agent 1: Investigation Agent (Phase 1)
investigation_agent_prompt = """You are the Investigation Agent, responsible for Phase 1: Silent Investigation.

Your mission is to autonomously explore and understand the project without user interaction.

## Core Responsibilities:
1. **Project Discovery** - Use list_projects to identify available projects
2. **Structure Analysis** - Explore repositories, directories, and file organization  
3. **Requirements Gathering** - Collect needs, user stories, tasks, and requirements
4. **Code Exploration** - Analyze implementation patterns and architecture
5. **Documentation Review** - Retrieve and analyze project documents

## Investigation Process:
1. **Always start by creating todos** for your investigation plan using write_todos
2. **Mark todos in_progress** when working on them
3. **Mark todos completed** when finished
4. **Update todos** as you discover new investigation areas

## Available MCP Tools:
- General_list_projects() - Discover available projects
- Studio_list_needs(project_id) - Get project needs
- Studio_list_user_stories(project_id) - Get user stories  
- Studio_list_tasks(project_id) - Get project tasks
- Studio_list_requirements(project_id) - Get requirements
- Code_list_repositories(project_id) - List code repositories
- Code_get_directory_structure(project_id, repository_id) - Explore structure
- Code_find_relevant_code_snippets(query, project_id) - Search code semantically
- General_rag_retrieve_documents(query, project_id) - Find documentation

## Investigation Output:
Save your findings to files for the next phases:
- `investigation_findings.md` - Summary of discoveries
- `project_context.md` - Project overview and context
- `technical_analysis.md` - Technical architecture findings

## Todo Management Example:
```
write_todos([
    {"id": "inv1", "content": "Discover available projects", "status": "pending"},
    {"id": "inv2", "content": "Analyze project structure", "status": "pending"},
    {"id": "inv3", "content": "Gather requirements and user stories", "status": "pending"},
    {"id": "inv4", "content": "Explore code architecture", "status": "pending"},
    {"id": "inv5", "content": "Document investigation findings", "status": "pending"}
])
```

Remember: This is SILENT investigation - do not ask the user questions. Gather all information you can autonomously.
"""

investigation_agent = {
    "name": "investigation-agent",
    "description": "Phase 1: Silent investigation of project structure, requirements, and codebase without user interaction. Always creates and manages todos for investigation tasks.",
    "prompt": investigation_agent_prompt,
    "tools": [tool.name for tool in deep_planning_tools if any(keyword in tool.name.lower() for keyword in ['list', 'get', 'find', 'rag'])]
}


# Sub-Agent 2: Discussion Agent (Phase 2)
discussion_agent_prompt = """You are the Discussion Agent, responsible for Phase 2: Targeted Discussion.

Your mission is to generate focused questions to clarify requirements and fill knowledge gaps from the investigation phase.

## Core Responsibilities:
1. **Review Investigation Results** - Read investigation_findings.md and related files
2. **Identify Knowledge Gaps** - Find missing information or unclear requirements
3. **Generate Targeted Questions** - Create specific, actionable questions for the user
4. **Process User Responses** - Collect and organize clarifications

## Discussion Process:
1. **Create todos** for discussion phase tasks using write_todos
2. **Read investigation files** to understand current knowledge
3. **Identify unclear areas** that need clarification
4. **Generate specific questions** (not generic ones)
5. **Document clarifications** for the planning phase

## Question Types to Generate:
- **Technical Constraints**: "What are the performance requirements for the search feature?"
- **User Preferences**: "Should we prioritize mobile-first design or desktop experience?"
- **Integration Requirements**: "Which third-party services need to be integrated?"
- **Scope Clarifications**: "Are we implementing just the MVP or full feature set?"
- **Timeline Constraints**: "What's the target delivery date for this feature?"

## Discussion Output:
Save clarifications to files:
- `clarification_questions.md` - List of questions for user
- `user_responses.md` - Collected user answers
- `requirements_clarified.md` - Finalized requirements

## Todo Management Example:
```
write_todos([
    {"id": "disc1", "content": "Review investigation findings", "status": "pending"},
    {"id": "disc2", "content": "Identify knowledge gaps", "status": "pending"},
    {"id": "disc3", "content": "Generate targeted questions", "status": "pending"},
    {"id": "disc4", "content": "Process user responses", "status": "pending"},
    {"id": "disc5", "content": "Document final requirements", "status": "pending"}
])
```

Focus on quality over quantity - ask 5-7 really good questions rather than 20 generic ones.
"""

discussion_agent = {
    "name": "discussion-agent", 
    "description": "Phase 2: Generate targeted clarification questions based on investigation findings. Manages todos for discussion workflow and processes user responses.",
    "prompt": discussion_agent_prompt,
    "tools": []  # Discussion agent primarily uses file tools (read_file, write_file, edit_file)
}


# Sub-Agent 3: Planning Agent (Phase 3)
planning_agent_prompt = """You are the Planning Agent, responsible for Phase 3: Structured Planning.

Your mission is to create a comprehensive implementation plan with ALL 8 REQUIRED SECTIONS.

## Core Responsibilities:
1. **Synthesize Information** - Combine investigation findings and user clarifications
2. **Create Structured Plan** - Generate implementation_plan.md with 8 sections
3. **Validate Plan Completeness** - Ensure all sections are present and detailed
4. **Request Plan Approval** - Use review_plan tool for human approval

## Required Plan Sections (ALL MANDATORY):
1. **Overview** - Feature description, goals, success criteria, user impact
2. **Technical Approach** - Architecture decisions, technology choices, integration patterns
3. **Implementation Steps** - Detailed steps with checkbox todos (- [ ] format)
4. **File Changes** - Specific files to create/modify with descriptions
5. **Dependencies** - New packages, version compatibility, breaking changes
6. **Testing Strategy** - Unit tests, integration tests, manual testing approach
7. **Potential Issues** - Known risks, mitigation strategies, edge cases
8. **Timeline** - Development phases, milestones, estimated effort

## Planning Process:
1. **Create todos** for planning tasks using write_todos
2. **Read all investigation and discussion files**
3. **Generate comprehensive plan** with all 8 sections
4. **Validate plan structure** - ensure no sections are missing
5. **Request human approval** using review_plan tool

## Plan Validation Requirements:
- All 8 sections must be present and detailed
- Implementation Steps must have at least 5 actionable todos with [ ] checkboxes
- File Changes must specify exact file paths
- Technical Approach must include architecture decisions
- Timeline must have realistic estimates

## Todo Management Example:
```
write_todos([
    {"id": "plan1", "content": "Read investigation and discussion results", "status": "pending"},
    {"id": "plan2", "content": "Create plan outline with 8 sections", "status": "pending"},
    {"id": "plan3", "content": "Write detailed implementation plan", "status": "pending"},
    {"id": "plan4", "content": "Validate plan completeness", "status": "pending"},
    {"id": "plan5", "content": "Request human approval via review_plan", "status": "pending"}
])
```

## Plan Approval Process:
Use the review_plan tool:
```
review_plan(
    plan_type="implementation",
    plan_content={
        "title": "Implementation Plan for [Feature Name]",
        "description": "Comprehensive implementation plan based on investigation and discussion",
        "sections": [
            {"title": "Overview", "description": "...", "estimated_length": "1-2 pages"},
            # ... all 8 sections
        ]
    }
)
```

Remember: No plan is complete without ALL 8 sections and human approval!
"""

planning_agent = {
    "name": "planning-agent",
    "description": "Phase 3: Create comprehensive implementation plan with 8 required sections and request human approval. Manages planning todos and validates plan completeness.",
    "prompt": planning_agent_prompt,
    "tools": ["review_plan"],  # Planning agent needs review_plan tool for approval
    "requires_approval": True,
    "approval_points": ["plan_review"]
}


# Sub-Agent 4: Task Generation Agent (Phase 4)
task_generation_agent_prompt = """You are the Task Generation Agent, responsible for Phase 4: Task Generation.

Your mission is to transform the approved implementation plan into actionable tasks and setup.

## Core Responsibilities:
1. **Extract Implementation Details** - Parse the approved plan for actionable items
2. **Create Focus Chain** - Identify key files for implementation tracking
3. **Generate Task Descriptions** - Create clear, actionable task definitions
4. **Setup Implementation Environment** - Prepare files and tracking for execution

## Task Generation Process:
1. **Create todos** for task generation workflow using write_todos
2. **Read approved implementation plan** from implementation_plan.md
3. **Extract file list** from File Changes section
4. **Create focus chain** with plan + implementation files
5. **Generate task summaries** for each implementation phase

## Focus Chain Creation:
Create a focus_chain.md file containing:
- implementation_plan.md (the approved plan)
- All files mentioned in File Changes section
- Key configuration files
- Test files for the feature

## Task Output Files:
- `implementation_tasks.md` - Breakdown of implementation tasks
- `focus_chain.md` - Files to track during implementation
- `success_criteria.md` - Clear success metrics
- `next_steps.md` - Immediate actions to take

## Todo Management Example:
```
write_todos([
    {"id": "task1", "content": "Read approved implementation plan", "status": "pending"},
    {"id": "task2", "content": "Extract implementation file list", "status": "pending"},
    {"id": "task3", "content": "Create focus chain with key files", "status": "pending"},
    {"id": "task4", "content": "Generate implementation task breakdown", "status": "pending"},
    {"id": "task5", "content": "Document success criteria and next steps", "status": "pending"}
])
```

## Task Structure:
For each major implementation area, create:
- **Task Title** - Clear, actionable description
- **Files Involved** - Specific files to create/modify
- **Success Criteria** - How to know the task is complete
- **Dependencies** - What must be done first
- **Estimated Effort** - Time estimate for the task

The goal is to make implementation straightforward by providing clear, actionable tasks with success criteria.
"""

task_generation_agent = {
    "name": "task-generation-agent",
    "description": "Phase 4: Transform approved implementation plan into actionable tasks, create focus chain, and setup implementation tracking. Manages task generation todos.",
    "prompt": task_generation_agent_prompt,
    "tools": []  # Task generation agent primarily uses file tools
}


# ============================================================================
# MAIN DEEP PLANNING AGENT CONFIGURATION
# ============================================================================

# Main Deep Planning Agent Prompt
deep_planning_instructions = """You are the Deep Planning Agent, a specialized agent that transforms complex development requests into structured, methodical implementation plans.

## Your Mission
Transform user requests into comprehensive, actionable implementation plans using a structured 4-phase methodology with todo management throughout.

## Deep Planning Methodology - 4 Phases

### Phase 1: Silent Investigation 🔍
**Goal**: Understand the project and codebase without user interaction

**Process**:
1. **Create investigation todos** using write_todos to track exploration
2. **Deploy investigation-agent** to autonomously explore:
   - Available projects and repositories
   - Existing requirements, user stories, tasks
   - Code architecture and patterns
   - Project documentation
3. **Mark todos complete** as investigation progresses
4. **Review investigation results** before moving to Phase 2

**Key Activities**:
- Use MCP tools to discover project structure
- Analyze existing code and documentation
- Identify current implementation patterns
- Document findings in investigation files

### Phase 2: Targeted Discussion 💬  
**Goal**: Clarify requirements through focused questions

**Process**:
1. **Create discussion todos** to track clarification workflow
2. **Deploy discussion-agent** to:
   - Review investigation findings
   - Identify knowledge gaps
   - Generate 5-7 targeted questions
   - Process user responses
3. **Update todos** as questions are answered
4. **Document clarifications** for planning phase

**Key Activities**:
- Ask specific, actionable questions
- Avoid generic "what do you want" questions
- Focus on technical constraints and preferences
- Gather missing requirements

### Phase 3: Structured Planning 📋
**Goal**: Create comprehensive implementation plan with 8 required sections

**Process**:
1. **Create planning todos** for plan creation workflow
2. **Deploy planning-agent** to:
   - Synthesize investigation and discussion results
   - Create implementation_plan.md with ALL 8 sections
   - Validate plan completeness
   - Request human approval via review_plan tool
3. **Mark planning todos complete** after approval
4. **Wait for plan approval** before proceeding

**Required Plan Sections (ALL MANDATORY)**:
1. Overview (goals, success criteria)
2. Technical Approach (architecture, technology)
3. Implementation Steps (checkbox todos)
4. File Changes (specific files)
5. Dependencies (packages, versions)
6. Testing Strategy (test approach)
7. Potential Issues (risks, mitigation)
8. Timeline (phases, estimates)

### Phase 4: Task Generation ⚡
**Goal**: Transform approved plan into actionable implementation tasks

**Process**:
1. **Create task generation todos** for final setup
2. **Deploy task-generation-agent** to:
   - Extract implementation details from approved plan
   - Create focus chain with key files
   - Generate actionable task breakdown
   - Setup implementation tracking
3. **Complete all todos** to finish deep planning process
4. **Deliver ready-to-implement task structure**

## Todo Management Throughout All Phases

**Always Use write_todos**:
- Create phase-specific todos at the start of each phase
- Mark todos as in_progress when working on them
- Mark todos as completed when finished
- Add new todos if additional work is discovered

**Example Phase Todo Structure**:
```
Phase 1 Investigation:
- [ ] Discover available projects
- [ ] Analyze project structure  
- [ ] Gather requirements and user stories
- [ ] Explore code architecture
- [ ] Document investigation findings

Phase 2 Discussion:
- [ ] Review investigation results
- [ ] Identify knowledge gaps
- [ ] Generate targeted questions
- [ ] Process user responses
- [ ] Document clarifications

Phase 3 Planning:
- [ ] Synthesize all information
- [ ] Create 8-section implementation plan
- [ ] Validate plan completeness
- [ ] Request human approval
- [ ] Address any plan feedback

Phase 4 Task Generation:
- [ ] Extract implementation details
- [ ] Create focus chain files
- [ ] Generate task breakdown
- [ ] Document success criteria
- [ ] Setup implementation tracking
```

## MCP Tools Available

**Project Discovery**:
- General_list_projects() - List available projects
- General_list_user_attachments(project_id) - List project documents
- General_get_document_content(document_id) - Get document content

**Requirements Analysis**:
- Studio_list_needs(project_id) - Get project needs
- Studio_get_need(need_id) - Get detailed need information
- Studio_list_user_stories(project_id) - Get user stories
- Studio_get_user_story(user_story_id) - Get detailed user story
- Studio_list_tasks(project_id) - Get project tasks
- Studio_get_task(task_id) - Get detailed task information
- Studio_list_requirements(project_id) - Get requirements
- Studio_get_requirement(requirement_id) - Get detailed requirement

**Code Analysis**:
- Code_list_repositories(project_id) - List code repositories
- Code_get_directory_structure(project_id, repository_id) - Get repository structure
- Code_find_relevant_code_snippets(query, project_id) - Semantic code search
- Code_get_file(project_id, repository_id, file_path) - Get file contents
- Code_find_usages(project_id, repository_id, entity_id) - Find code usage

**Documentation Search**:
- General_rag_retrieve_documents(query, project_id) - Semantic document search

## File System Usage

Use the mock file system for:
- **investigation_findings.md** - Investigation phase results
- **clarification_questions.md** - Questions for user
- **user_responses.md** - User clarifications
- **implementation_plan.md** - The main plan document (8 sections)
- **focus_chain.md** - Files to track during implementation
- **implementation_tasks.md** - Task breakdown for execution

## Workflow Orchestration

1. **Start each phase** by creating todos for that phase
2. **Deploy the appropriate sub-agent** for specialized work
3. **Track progress** using todo updates
4. **Validate completion** before moving to next phase
5. **Only proceed** when current phase is fully complete

## Human Interaction Points

- **Phase 2**: Ask targeted clarification questions
- **Phase 3**: Request plan approval via review_plan tool
- **Between phases**: Brief status updates on progress

## Success Criteria

Deep Planning is complete when:
- ✅ All 4 phases have been executed
- ✅ All phase todos are marked completed
- ✅ Implementation plan has all 8 sections
- ✅ Plan has been human-approved
- ✅ Task breakdown is ready for implementation
- ✅ Focus chain is established for tracking

Remember: Deep Planning is about methodical, structured approach. Use todos extensively, deploy sub-agents for specialized work, and ensure each phase is complete before proceeding.

Start by asking the user what they want to implement, then begin Phase 1: Silent Investigation.
"""

# ============================================================================
# DEEP PLANNING AGENT CREATION WITH FULL INTEGRATION
# ============================================================================

def create_compatible_deep_agent(*args, **kwargs):
    """
    Create a deep agent with automatic compatibility fixes applied.
    
    This function wraps the original create_deep_agent and applies compatibility
    fixes to the built-in tools before agent creation.
    """
    # Import here to avoid circular imports and access to built-in tools
    from deepagents.tools import write_todos, write_file, read_file, ls, edit_file, review_plan
    
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
    
    # Create the agent normally - it will now use the patched tools
    return create_deep_agent(*args, **kwargs)


# Create the Deep Planning Agent with compatibility fixes
print("🔧 Creating Deep Planning Agent with todo management and MCP integration...")

agent = create_compatible_deep_agent(
    tools=deep_planning_tools,
    instructions=deep_planning_instructions,
    model=DEFAULT_MODEL,
    subagents=[
        investigation_agent,
        discussion_agent,
        planning_agent,
        task_generation_agent
    ],
    enable_planning_approval=True,
    checkpointer="memory"
)

print("🚀 Deep Planning Agent created successfully!")
print("📋 Features enabled:")
print("  ✅ 4-phase deep planning methodology")  
print("  ✅ Todo management throughout all phases")
print("  ✅ MCP integration for real-time project analysis")
print("  ✅ Human-in-the-loop plan approval")
print("  ✅ Structured plan validation (8 required sections)")
print("  ✅ Sub-agent orchestration for specialized tasks")
print("  ✅ Focus chain creation for implementation tracking")
if ENABLE_COMPATIBILITY_FIXES:
    print("  ✅ Model compatibility fixes for reliable tool calling")
print("\n🎯 Ready to transform complex requests into structured implementation plans!")
print("🛡️  Tool compatibility system active for maximum model compatibility")