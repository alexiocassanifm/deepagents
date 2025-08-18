"""
Minimal test script for token tracking functionality.
This avoids the complex factory system and focuses on testing the core token tracking.
"""

import sys
import os
import logging

# Add the src directory to path
sys.path.append('src')

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable our custom loggers
logging.getLogger('enhanced_token_tracker').setLevel(logging.INFO)
logging.getLogger('openrouter_http').setLevel(logging.INFO)
logging.getLogger('token_tracker').setLevel(logging.INFO)

# Import and enable HTTP interceptor
logger.info("🔍 Enabling OpenRouter HTTP logging...")
try:
    from src.context.http_interceptor import enable_openrouter_logging
    enable_openrouter_logging()
    logger.info("✅ OpenRouter HTTP logging enabled")
except Exception as e:
    logger.warning(f"⚠️ Could not enable HTTP logging: {e}")

# Import token tracking hooks
from src.context.token_tracking_hooks import (
    create_enhanced_token_tracking_hook,
    create_passthrough_token_tracking_hook
)

# Import basic deepagents
from deepagents import create_deep_agent

def test_minimal_tracking():
    """Test token tracking with a minimal agent configuration."""
    
    logger.info("\n🧪 MINIMAL TOKEN TRACKING TEST")
    logger.info("=" * 50)
    
    # Create a simple enhanced tracking hook (without compression)
    logger.info("🔬 Creating passthrough token tracking hook...")
    tracking_hook = create_passthrough_token_tracking_hook()
    
    # Create a minimal agent
    logger.info("🤖 Creating minimal agent...")
    agent = create_deep_agent(
        tools=[],  # No additional tools
        instructions="You are a helpful assistant. Always respond concisely.",
        model="openrouter/z-ai/glm-4.5",
        pre_model_hook=tracking_hook
    )
    
    logger.info("✅ Minimal agent created!")
    
    # Test with a simple message
    test_input = {
        "messages": [
            {
                "role": "user",
                "content": "Hello! Can you count the tokens in this message and explain what you see?"
            }
        ]
    }
    
    logger.info("📤 Sending test message...")
    logger.info(f"📝 Message content: {test_input['messages'][0]['content']}")
    
    try:
        logger.info("\n" + "="*60)
        logger.info("🚀 INVOKING AGENT - WATCH FOR TOKEN TRACKING LOGS")
        logger.info("="*60)
        
        result = agent.invoke(test_input)
        
        logger.info("="*60)
        logger.info("✅ AGENT RESPONSE RECEIVED")
        logger.info("="*60)
        
        # Show result
        if "messages" in result:
            messages = result["messages"]
            logger.info(f"📊 Total messages in result: {len(messages)}")
            
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    content = str(last_msg.content)
                    logger.info(f"📝 Assistant response ({len(content)} chars):")
                    logger.info(f"   '{content[:200]}{'...' if len(content) > 200 else ''}'")
        
        logger.info("\n✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minimal_tracking()