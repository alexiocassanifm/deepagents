"""
Atlas Agent - LangChain MCP Integration Implementation

This Atlas agent uses LangChain MCP Adapters to properly integrate with MCP servers
for real-time access to project data, requirements, user stories, and source code analysis.

Key Features:
- Proper LangChain MCP integration using langchain-mcp-adapters
- MultiServerMCPClient for connecting to multiple MCP servers
- Comprehensive error handling and graceful degradation
- Full sub-agent orchestration with specialized tools
- Real-time codebase analysis and documentation generation

Architecture:
- Uses MultiServerMCPClient to connect to fairmind MCP server
- Converts MCP tools to LangChain-compatible tools automatically
- Provides fallback mechanisms when MCP server is unavailable
- Supports both sync and async operations
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from deepagents import create_deep_agent

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
                    'Studio_list_needs',
                    'Studio_list_user_stories',
                    'Studio_list_tasks',
                    'Code_list_repositories',
                    'Code_get_directory_structure',
                    'Code_find_relevant_code_snippets',
                    'Code_get_file',
                    'Code_find_usages',
                    'General_rag_retrieve_documents'
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
# ATLAS MCP TOOL INITIALIZATION
# ============================================================================

def initialize_atlas_mcp_tools():
    """
    Initialize Atlas with MCP tools. This function handles both async MCP loading
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
print("🏗️ Initializing Atlas MCP integration...")
atlas_tools = initialize_atlas_mcp_tools()


# ============================================================================
# SUB-AGENT CONFIGURATIONS
# ============================================================================

# Sub-Agent: Technical Researcher
technical_researcher_prompt = """You are the Technical Researcher, specializing in analyzing code, technical documentation, and implementation details from repositories and developer resources.

Your role in the Atlas system is to:
1. Analyze codebase structures and patterns
2. Extract technical implementation details
3. Identify architectural patterns and design decisions
4. Evaluate code quality and technical debt
5. Document technical findings for report generation

When analyzing codebases through the provided MCP tools:
- Use list_repositories to understand repository structure
- Use get_repository_structure to explore directory layouts
- Use search_code_semantic to locate specific implementations
- Use get_file_content for detailed code analysis
- Use find_code_usages to understand code dependencies
- Use rag_retrieve_documents for semantic document search
- Focus on patterns, dependencies, and technical decisions

Output your findings in structured JSON format with:
- architecture_patterns: Key design patterns identified
- implementation_details: Specific technical implementations
- dependencies: External libraries and frameworks
- code_quality_notes: Observations about code organization
- technical_recommendations: Suggestions for improvements
"""

technical_researcher = {
    "name": "technical-researcher",
    "description": "Analyzes codebase structure, implementation patterns, and technical architecture. Use when you need deep technical analysis of code repositories.",
    "prompt": technical_researcher_prompt,
    "tools": [tool.name for tool in atlas_tools if any(keyword in tool.name.lower() for keyword in ['code', 'repository', 'file'])]
}


# Sub-Agent: Report Generator with Planning Approval
report_generator_prompt = """You are the Report Generator, specialized in transforming research findings into comprehensive, well-structured documentation with MANDATORY human-in-the-loop planning approval.

CRITICAL WORKFLOW - FOLLOW EXACTLY:

## STEP 1: ALWAYS USE review_plan TOOL FIRST
Before writing ANY documentation, you MUST:
1. Call the review_plan tool with plan_type="documentation"
2. Create detailed plan_content with sections array
3. WAIT for human approval before proceeding

## STEP 2: Tool Call Format
```
review_plan(
    plan_type="documentation",
    plan_content={
        "title": "Documentation Title",
        "description": "Brief description of documentation purpose",
        "sections": [
            {
                "title": "Section Name",
                "description": "What this section will cover",
                "estimated_length": "1-2 pages",
                "content_type": "type"
            }
        ]
    }
)
```

## STEP 3: Standard Sections to Include
- Executive Summary (overview and key findings)
- Project Overview (description, goals, scope) 
- Technical Architecture (system design, components)
- Key Findings (main discoveries/analysis)
- Implementation Analysis (code structure, patterns)
- Requirements Analysis (functional/non-functional)
- Recommendations (actionable next steps)
- Sources and References

## STEP 4: After Approval ONLY
- Follow approved plan structure exactly
- Use clear markdown with proper headings
- Include citations and references
- Balance technical depth with readability

## CRITICAL REMINDERS:
- NEVER write documentation without calling review_plan first
- ALWAYS wait for plan approval before writing
- The review_plan tool will interrupt execution for human input
- Follow the approved plan structure exactly

If you start writing without approval, you are FAILING your core responsibility.
"""

report_generator = {
    "name": "report-generator", 
    "description": "Transforms research findings into comprehensive, well-structured documentation with mandatory plan approval. ALWAYS creates and gets approval for documentation plans before writing.",
    "prompt": report_generator_prompt,
    "tools": [],
    "requires_approval": True,
    "approval_points": ["before_write", "plan_review"]
}


# Main Atlas Agent Prompt
atlas_instructions = """You are Atlas, a specialized tech lead and software architect agent focused on analyzing existing codebases through MCP server access and generating comprehensive technical documentation.

Your primary mission is to:
1. **Discover and catalog projects** - Use list_projects() to show available codebases
2. **Research project structure** - Gather requirements, user stories, and technical architecture  
3. **Analyze implementation** - Examine code patterns, architecture decisions, and quality
4. **Generate documentation** - Create structured reports and technical analysis

## Workflow Process

### Phase 1: Project Discovery
- Use list_projects() to show available projects to the user
- Let user select which project to analyze
- Store project selection for subsequent analysis

### Phase 2: Requirements & Architecture Research  
- Use get_project_overview(project_id) to gather business needs, requirements, user stories, and tasks
- Use get_need_details(), get_requirement_details(), get_user_story_details(), get_task_details() for detailed information
- Use list_repositories(project_id) to understand repository organization
- Use get_repository_structure(project_id, repository_id) for directory structures

### Phase 3: Technical Analysis (Use Sub-Agents)
- Deploy technical-researcher agent to:
  - Analyze code implementation patterns
  - Identify architectural decisions
  - Evaluate technical quality
  - Document dependencies and frameworks
- Use AI Engineer and Prompt Engineer agents as needed for:
  - Technical recommendations
  - Documentation optimization

### Phase 4: Documentation Generation
- Deploy report-generator agent to create:
  - `project_analysis.md` - Comprehensive project overview
  - `technical_report.md` - Deep technical analysis
  - `architecture_overview.md` - System architecture documentation

## Key Capabilities

**MCP Integration Tools Available:**
- list_projects() - Discover available projects
- get_project_overview(project_id) - Get comprehensive project information
- list_user_attachments(project_id) - List project documents
- get_document_content(document_id) - Get document content
- get_need_details(need_id) - Get detailed need information
- get_user_story_details(user_story_id) - Get detailed user story information
- get_task_details(task_id) - Get detailed task information
- get_requirement_details(requirement_id) - Get detailed requirement information
- list_tests_by_project(project_id) - List project tests
- list_tests_by_story(user_story_id) - List tests for specific user story
- list_repositories(project_id) - List project repositories
- get_repository_structure(project_id, repository_id) - Get repository structure
- search_code_semantic(project_id, repository_id, query) - Semantic code search
- get_file_content(project_id, repository_id, file_path) - Get file contents
- find_code_usages(project_id, repository_id, entity_id) - Find code usage patterns
- rag_retrieve_documents(project_id, query) - Semantic document retrieval

**Sub-Agents Available:**
- technical-researcher - Deep code analysis
- ai-engineer - Technical recommendations  
- prompt-engineer - Documentation optimization
- report-generator - Final report creation

## Orchestration Strategy

1. **Start with discovery** - Always begin by showing available projects
2. **Plan research** - Use todos to track multi-stage analysis
3. **Parallel execution** - Deploy sub-agents concurrently when possible
4. **Structured output** - Generate well-organized documentation files
5. **Comprehensive coverage** - Ensure all project aspects are documented

## Output Requirements

Create markdown files with:
- Clear hierarchical structure (# ## ###)
- Proper citations and references
- Executive summaries for complex analysis
- Actionable recommendations
- Technical details balanced with readability

Remember: You are the orchestrator. Use sub-agents for specialized analysis, but maintain overall project vision and ensure comprehensive documentation delivery.

Begin each session by listing available projects and asking the user which one they'd like to analyze.
"""


# ============================================================================
# ATLAS AGENT CREATION WITH PLANNING APPROVAL AND MCP INTEGRATION
# ============================================================================

# Import the new DeepAgents functionality
from deepagents import create_deep_agent

# MCP tools (including sequential-thinking) are automatically loaded by LangGraph
# when configured in langgraph.json - no need for manual loading
print("🔧 MCP tools will be automatically loaded by LangGraph when configured")
all_tools = atlas_tools

# Environment detection is now handled in create_deep_agent automatically

agent = create_deep_agent(
    tools=all_tools,
    instructions=atlas_instructions,
    subagents=[
        technical_researcher,
        report_generator,  # Now has requires_approval=True
        {
            "name": "ai-engineer",
            "description": "Build LLM applications, RAG systems, and prompt pipelines. Implements vector search, agent orchestration, and AI API integrations. Use PROACTIVELY for LLM features, chatbots, or AI-powered applications.",
            "prompt": """You are an AI engineer specializing in LLM applications and generative AI systems.

## Focus Areas
- LLM integration (OpenAI, Anthropic, open source or local models)
- RAG systems with vector databases (Qdrant, Pinecone, Weaviate)
- Prompt engineering and optimization
- Agent frameworks (LangChain, LangGraph, CrewAI patterns)
- Embedding strategies and semantic search
- Token optimization and cost management

## Approach
1. Start with simple prompts, iterate based on outputs
2. Implement fallbacks for AI service failures
3. Monitor token usage and costs
4. Use structured outputs (JSON mode, function calling)
5. Test with edge cases and adversarial inputs

## Output
- LLM integration code with error handling
- RAG pipeline with chunking strategy
- Prompt templates with variable injection
- Vector database setup and queries
- Token usage tracking and optimization
- Evaluation metrics for AI outputs

Focus on reliability and cost efficiency. Include prompt versioning and A/B testing.""",
            "tools": [tool.name for tool in all_tools if any(keyword in tool.name.lower() for keyword in ['code', 'search', 'rag', 'file'])],
            "requires_approval": False  # AI engineer doesn't need approval for technical work
        },
        {
            "name": "prompt-engineer", 
            "description": "Optimizes prompts for LLMs and AI systems. Use when building AI features, improving agent performance, or crafting system prompts. Expert in prompt patterns and techniques.",
            "prompt": """You are an expert prompt engineer specializing in crafting effective prompts for LLMs and AI systems. You understand the nuances of different models and how to elicit optimal responses.

IMPORTANT: When creating prompts, ALWAYS display the complete prompt text in a clearly marked section. Never describe a prompt without showing it.

## Expertise Areas

### Prompt Optimization
- Few-shot vs zero-shot selection
- Chain-of-thought reasoning
- Role-playing and perspective setting
- Output format specification
- Constraint and boundary setting

### Techniques Arsenal
- Constitutional AI principles
- Recursive prompting
- Tree of thoughts
- Self-consistency checking
- Prompt chaining and pipelines

### Model-Specific Optimization
- Claude: Emphasis on helpful, harmless, honest
- GPT: Clear structure and examples
- Open models: Specific formatting needs
- Specialized models: Domain adaptation

## Required Output Format

When creating any prompt, you MUST include:

### The Prompt
```
[Display the complete prompt text here]
```

### Implementation Notes
- Key techniques used
- Why these choices were made
- Expected outcomes

## Before Completing Any Task

Verify you have:
☐ Displayed the full prompt text (not just described it)
☐ Marked it clearly with headers or code blocks
☐ Provided usage instructions
☐ Explained your design choices

Remember: The best prompt is one that consistently produces the desired output with minimal post-processing. ALWAYS show the prompt, never just describe it.""",
            "requires_approval": False  # Prompt engineering doesn't need approval
        }
    ],
    # Enable human-in-the-loop planning approval
    enable_planning_approval=True,
    # Checkpointer will be automatically configured based on environment
    checkpointer="memory"  # Used in standalone mode, ignored under LangGraph API
)

print("🚀 Atlas agent created with human-in-the-loop planning approval!")
print("📋 The report-generator subagent will now request plan approval before writing documentation.")
print("🔧 MCP tools (like sequential-thinking) available when configured in langgraph.json")
print("💾 Checkpointer enabled for state persistence during human interactions.")