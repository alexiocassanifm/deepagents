"""
MCP Integration Module for Deep Planning Agent

This module handles all Model Context Protocol (MCP) related functionality,
including loading tools from MCP servers, fallback mechanisms, and tool wrapping
for automatic context cleaning.

Key Features:
- Async MCP tool loading from fairmind server
- Fallback demo tools when MCP is unavailable
- Automatic tool wrapping for context cleaning
- Integration with compact context management
"""

import asyncio
import os
import logging
from typing import List, Any, Dict, Tuple, Optional

# Setup logger for MCP operations
logger = logging.getLogger(__name__)

# Check MCP availability
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_AVAILABLE = True
    logger.info("✅ MCP adapters available")
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("⚠️ langchain-mcp-adapters not available. Install with: pip install langchain-mcp-adapters")

# Import unified wrapper and compact integration if available
try:
    from ...compatibility.unified_wrapper import wrap_tools_unified
    from ...context.compact_integration import CompactIntegration
    from ...context.context_manager import ContextManager
    WRAPPER_AVAILABLE = True
except ImportError:
    WRAPPER_AVAILABLE = False
    logger.warning("⚠️ Unified wrapper or compact integration not available")


async def load_fairmind_mcp_tools() -> Tuple[List[Any], Optional[Any], Optional[Any]]:
    """
    Load MCP tools from the fairmind MCP server using LangChain MCP adapters.
    
    Returns:
        Tuple of (tools, mcp_wrapper, compact_integration)
        Falls back to demo tools if MCP server is not available.
    """
    if not MCP_AVAILABLE:
        logger.warning("⚠️ MCP adapters not available, using fallback tools")
        # Create compact integration even for fallback tools
        if WRAPPER_AVAILABLE:
            from ...context.context_manager import ContextManager
            from ...context.compact_integration import CompactIntegration
            context_manager = ContextManager()
            compact_integration = CompactIntegration(context_manager, model_name=os.getenv("DEEPAGENTS_MODEL", "claude-sonnet-4-20250514"))
            logger.info("✅ Created compact integration for fallback tools")
            return get_fallback_tools(), None, compact_integration
        else:
            return get_fallback_tools(), None, None
    
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
        
        logger.info("🔌 Connecting to fairmind MCP server...")
        client = MultiServerMCPClient(fairmind_server_config)
        
        # Load all available tools from the MCP server
        tools = await client.get_tools()
        
        logger.info(f"✅ Loaded {len(tools)} MCP tools from fairmind server")
        
        # Filter for relevant fairmind tools
        fairmind_tools = filter_relevant_fairmind_tools(tools)
        
        logger.info(f"🎯 Found {len(fairmind_tools)} relevant fairmind tools")
        
        # Skip wrapping MCP tools as it corrupts signatures, but CREATE context integration
        logger.warning("⚠️ Skipping MCP tool wrapping due to signature corruption issues")
        logger.info(f"✅ Using {len(fairmind_tools)} MCP tools without wrapping")
        
        # Create compact integration even without wrapping
        if WRAPPER_AVAILABLE:
            from ...context.context_manager import ContextManager
            from ...context.compact_integration import CompactIntegration
            context_manager = ContextManager()
            compact_integration = CompactIntegration(context_manager, model_name=os.getenv("DEEPAGENTS_MODEL", "claude-sonnet-4-20250514"))
            logger.info("✅ Created compact integration for context management")
            return fairmind_tools, None, compact_integration
        else:
            logger.warning("⚠️ Context manager not available")
            return fairmind_tools, None, None
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MCP server: {e}")
        logger.info("🔄 Falling back to demo tools")
        
        # EVEN FOR DEMO TOOLS: Create context integration to test compression functionality
        demo_tools = get_fallback_tools()
        
        # Skip wrapping for demo tools but create compact integration for testing
        if WRAPPER_AVAILABLE:
            from ...context.context_manager import ContextManager
            from ...context.compact_integration import CompactIntegration
            context_manager = ContextManager()
            compact_integration = CompactIntegration(context_manager, model_name=os.getenv("DEEPAGENTS_MODEL", "claude-sonnet-4-20250514"))
            logger.info("✅ Created compact integration for demo tools (for testing compression)")
            logger.info("⚠️ Using demo tools (no real MCP connection) without wrapping")
            return demo_tools, None, compact_integration
        else:
            logger.warning("⚠️ Context manager not available for demo tools")
            return demo_tools, None, None


def filter_relevant_fairmind_tools(tools: List[Any]) -> List[Any]:
    """
    Filter MCP tools to include only relevant fairmind tools.
    
    Args:
        tools: List of all available MCP tools
        
    Returns:
        List of filtered fairmind tools
    """
    relevant_prefixes = [
        'General_list_projects',
        'General_list_user_attachments',
        'General_get_document_content',
        'General_rag_retrieve_documents',
        'Studio_list_needs',
        'Studio_get_need',
        'Studio_list_user_stories',
        'Studio_get_user_story',
        'Code_list_repositories',
        'Code_get_directory_structure',
        'Code_find_relevant_code_snippets',
        'Code_get_file',
        'Code_find_usages'
    ]
    
    fairmind_tools = [
        tool for tool in tools 
        if hasattr(tool, 'name') and any(
            prefix in tool.name for prefix in relevant_prefixes
        )
    ]
    
    return fairmind_tools


def get_fallback_tools() -> List[Any]:
    """
    Fallback tools when MCP server is not available.
    These provide demo functionality with mock data.
    
    Returns:
        List of demo tools for testing
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


def initialize_deep_planning_mcp_tools() -> Tuple[List[Any], Optional[Any], Optional[Any]]:
    """
    Initialize Deep Planning Agent with MCP tools. This function handles both async MCP loading
    and fallback to demo tools when MCP is not available.
    
    Returns:
        Tuple of (tools, mcp_wrapper, compact_integration)
    """
    try:
        # Try to load MCP tools asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mcp_tools, mcp_wrapper, compact_integration = loop.run_until_complete(load_fairmind_mcp_tools())
        loop.close()
        return mcp_tools, mcp_wrapper, compact_integration
    except Exception as e:
        logger.error(f"⚠️ Failed to initialize MCP tools: {e}")
        logger.info("🔄 Using fallback demo tools")
        # Create compact integration even for fallback case
        if WRAPPER_AVAILABLE:
            try:
                from ..context.context_manager import ContextManager
                from ..context.compact_integration import CompactIntegration
                context_manager = ContextManager()
                compact_integration = CompactIntegration(context_manager, model_name=os.getenv("DEEPAGENTS_MODEL", "claude-sonnet-4-20250514"))
                logger.info("✅ Created compact integration for fallback initialization")
                return get_fallback_tools(), None, compact_integration
            except Exception as context_error:
                logger.error(f"⚠️ Failed to create compact integration: {context_error}")
                return get_fallback_tools(), None, None
        else:
            return get_fallback_tools(), None, None


def get_mcp_status() -> Dict[str, Any]:
    """
    Get current MCP integration status.
    
    Returns:
        Dictionary containing MCP status information
    """
    return {
        "mcp_available": MCP_AVAILABLE,
        "wrapper_available": WRAPPER_AVAILABLE,
        "mcp_url": os.getenv("FAIRMIND_MCP_URL", "Not configured"),
        "mcp_token_configured": bool(os.getenv("FAIRMIND_MCP_TOKEN")),
        "fallback_tools_count": len(get_fallback_tools())
    }


def print_mcp_status():
    """
    Print MCP integration status for debugging.
    """
    status = get_mcp_status()
    
    print("\n" + "="*60)
    print("MCP INTEGRATION STATUS")
    print("="*60)
    print(f"MCP Adapters Available: {'✅' if status['mcp_available'] else '❌'}")
    print(f"MCP Wrapper Available: {'✅' if status['wrapper_available'] else '❌'}")
    print(f"MCP URL: {status['mcp_url']}")
    print(f"MCP Token Configured: {'✅' if status['mcp_token_configured'] else '❌'}")
    print(f"Fallback Tools Available: {status['fallback_tools_count']}")
    print("="*60 + "\n")