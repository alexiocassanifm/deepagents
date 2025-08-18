"""
Debug Agent Core - Enhanced Token Tracking Version

This is a debug version of the agent core that includes comprehensive
token tracking to identify discrepancies with OpenRouter's reported usage.
"""

import os
import logging
import sys

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Enable comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import HTTP interceptor to capture OpenRouter requests
print("🔍 Enabling OpenRouter HTTP request logging...")
try:
    from ..context.http_interceptor import enable_openrouter_logging
    enable_openrouter_logging()
    print("✅ OpenRouter HTTP logging enabled")
except Exception as e:
    print(f"⚠️ Could not enable HTTP logging: {e}")

# Import enhanced token tracking
from ..context.token_tracking_hooks import (
    create_enhanced_token_tracking_hook,
    create_passthrough_token_tracking_hook
)

# Import existing agent creation components
from .agent_core import (
    DEFAULT_MODEL,
    initialize_deep_planning_mcp_tools,
    create_simplified_factory,
    print_compatibility_report
)

from deepagents import create_deep_agent

def create_debug_agent_with_enhanced_tracking(enable_compression=True):
    """
    Create a debug version of the deep planning agent with comprehensive token tracking.
    
    Args:
        enable_compression: Whether to enable compression or just track tokens
        
    Returns:
        Agent with enhanced token tracking capabilities
    """
    
    logger.info("🚀 Creating DEBUG AGENT with Enhanced Token Tracking")
    logger.info("=" * 60)
    
    # Initialize MCP tools
    logger.info("🔗 Initializing MCP tools...")
    mcp_tools, mcp_wrapper, compact_integration_from_mcp = initialize_deep_planning_mcp_tools()
    logger.info(f"✅ MCP tools initialized: {len(mcp_tools)} tools available")
    
    # Create agent factory with MCP tools
    logger.info("🏭 Creating agent factory...")
    factory = create_simplified_factory(mcp_tools)
    
    # Get agent configuration
    tools, instructions, model, subagents = factory.get_agent_config()
    logger.info(f"✅ Agent config loaded: {len(tools)} additional tools, model: {model}")
    
    # Use compact integration from MCP or create new one
    compact_integration = compact_integration_from_mcp
    if enable_compression and not compact_integration:
        try:
            from ..context.compact_integration import CompactIntegration
            compact_integration = CompactIntegration()
            logger.info("✅ Compact integration created for compression")
        except Exception as e:
            logger.warning(f"⚠️ Could not load compact integration: {e}")
            compact_integration = None
    elif compact_integration:
        logger.info("✅ Using compact integration from MCP initialization")
    
    # Create enhanced token tracking hook
    logger.info("🔬 Creating enhanced token tracking hook...")
    
    if enable_compression and compact_integration:
        logger.info("🧠 Using ENHANCED TRACKING with COMPRESSION")
        tracking_hook = create_enhanced_token_tracking_hook(
            compact_integration=compact_integration,
            mcp_wrapper=mcp_wrapper,
            model_name=DEFAULT_MODEL
        )
    else:
        logger.info("🧠 Using PASSTHROUGH TRACKING (no compression)")
        tracking_hook = create_passthrough_token_tracking_hook()
    
    # Create the agent with enhanced tracking
    logger.info("🏗️ Creating deep agent with enhanced tracking...")
    
    agent = create_deep_agent(
        tools=tools + mcp_tools,
        instructions=instructions,
        model=DEFAULT_MODEL,
        subagents=subagents,
        pre_model_hook=tracking_hook,
        enable_planning_approval=True,
        checkpointer="memory"
    )
    
    logger.info("✅ Debug agent created successfully!")
    logger.info("=" * 60)
    logger.info("🔍 Token tracking features enabled:")
    logger.info("  ✅ Pre-model hook token counting")
    logger.info("  ✅ Multiple tokenization methods")
    logger.info("  ✅ HTTP request/response logging")
    logger.info("  ✅ Payload structure analysis")
    logger.info(f"  {'✅' if enable_compression else '❌'} Context compression")
    logger.info("=" * 60)
    
    return agent


def test_token_tracking():
    """Test the token tracking capabilities with a simple conversation."""
    
    print("\n🧪 Testing Enhanced Token Tracking")
    print("=" * 50)
    
    # Create debug agent
    agent = create_debug_agent_with_enhanced_tracking(enable_compression=True)
    
    # Test with a simple message
    test_message = {
        "messages": [
            {
                "role": "user", 
                "content": "Hello! Please analyze this codebase and tell me about the token tracking discrepancy we're investigating. Create a todo list for the investigation."
            }
        ]
    }
    
    print("📤 Sending test message...")
    print(f"Test content: '{test_message['messages'][0]['content'][:100]}...'")
    
    try:
        # This should trigger our enhanced logging
        result = agent.invoke(test_message)
        
        print("✅ Test message processed successfully!")
        print(f"📊 Response received: {len(result.get('messages', []))} total messages in result")
        
        # Show the assistant's response
        messages = result.get('messages', [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                content = str(last_message.content)[:300] + "..." if len(str(last_message.content)) > 300 else str(last_message.content)
                print(f"📝 Assistant response preview: '{content}'")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("🧪 Test completed - check logs for detailed token tracking information")


if __name__ == "__main__":
    """Run debug agent for testing."""
    
    print("🔬 DEEP PLANNING DEBUG AGENT")
    print("Enhanced Token Tracking for OpenRouter Discrepancy Investigation")
    print("=" * 70)
    
    # Print compatibility report
    print_compatibility_report()
    
    # Enable debug logging for key modules
    logging.getLogger('enhanced_token_tracker').setLevel(logging.INFO)
    logging.getLogger('openrouter_http').setLevel(logging.INFO)
    logging.getLogger('token_tracker').setLevel(logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test
        test_token_tracking()
    else:
        # Create agent and make it available for import
        print("Creating debug agent for interactive use...")
        debug_agent = create_debug_agent_with_enhanced_tracking(enable_compression=True)
        print("✅ Debug agent ready for use!")
        print("💡 Import this agent with: from src.core.debug_agent_core import debug_agent")