"""
Test script to validate the compression hook fix without requiring OpenRouter API.
This tests the hook logic independently of actual LLM calls.
"""

import sys
import os
import logging
from unittest.mock import Mock, MagicMock

# Add the src directory to path
sys.path.append('src')

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable our custom loggers
logging.getLogger('mcp_context_tracker').setLevel(logging.INFO)

def test_compression_hook_fix():
    """Test that the compression hook properly returns state updates for LangGraph v2."""
    
    logger.info("\n🧪 TESTING COMPRESSION HOOK FIX")
    logger.info("=" * 50)
    
    # Import the compression hook
    from src.context.compression_hooks import create_compression_hook
    
    # Create mock compact integration
    mock_compact_integration = Mock()
    mock_compact_integration.should_trigger_compaction = Mock()
    mock_compact_integration.perform_automatic_compaction = Mock()
    
    # Create mock MCP wrapper
    mock_mcp_wrapper = Mock()
    
    # Test case 1: No compression needed
    logger.info("🔬 Test 1: No compression needed")
    
    # Setup mock to return no compression needed
    mock_metrics = Mock()
    mock_metrics.utilization_percentage = 50.0
    mock_compact_integration.should_trigger_compaction.return_value = (False, Mock(), mock_metrics)
    
    # Create hook
    hook = create_compression_hook(
        compact_integration=mock_compact_integration,
        mcp_wrapper=mock_mcp_wrapper,
        model_name="test-model"
    )
    
    # Test state (LangGraph format)
    test_state = {
        "messages": [
            {"role": "user", "content": "Hello, this is a test message"},
            {"role": "assistant", "content": "I understand, let me help you."}
        ]
    }
    
    result = hook(test_state)
    
    logger.info(f"✅ Result type: {type(result)}")
    logger.info(f"✅ Result content: {result}")
    
    # Should return empty dict for no compression
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result == {}, f"Expected empty dict, got {result}"
    
    logger.info("✅ Test 1 PASSED: No compression returns empty dict")
    
    # Test case 2: Compression needed
    logger.info("\n🔬 Test 2: Compression needed")
    
    # Setup mock to return compression needed
    mock_trigger_type = Mock()
    mock_trigger_type.value = "TOKEN_LIMIT"
    mock_metrics.utilization_percentage = 85.0
    mock_compact_integration.should_trigger_compaction.return_value = (True, mock_trigger_type, mock_metrics)
    
    # Setup mock compression result
    compressed_messages = [
        {"role": "system", "content": "Compressed conversation summary"},
        {"role": "user", "content": "Hello, this is a test message"}
    ]
    
    mock_summary = Mock()
    mock_summary.total_reduction_percentage = 60.0
    mock_summary.summary_content = "Compressed conversation"
    
    mock_compact_integration.perform_automatic_compaction.return_value = (compressed_messages, mock_summary)
    
    result = hook(test_state)
    
    logger.info(f"✅ Result type: {type(result)}")
    logger.info(f"✅ Result content: {result}")
    
    # Should return messages update for compression
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "messages" in result, f"Expected 'messages' key in result: {result}"
    assert len(result["messages"]) == 2, f"Expected 2 compressed messages, got {len(result['messages'])}"
    
    logger.info("✅ Test 2 PASSED: Compression returns correct state update")
    
    # Test case 3: Error handling
    logger.info("\n🔬 Test 3: Error handling")
    
    # Setup mock to throw error
    mock_compact_integration.should_trigger_compaction.side_effect = Exception("Test error")
    
    result = hook(test_state)
    
    logger.info(f"✅ Result type: {type(result)}")
    logger.info(f"✅ Result content: {result}")
    
    # Should return empty dict on error
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result == {}, f"Expected empty dict on error, got {result}"
    
    logger.info("✅ Test 3 PASSED: Error handling returns empty dict")
    
    # Test case 4: No compact integration
    logger.info("\n🔬 Test 4: No compact integration")
    
    hook_no_compact = create_compression_hook(
        compact_integration=None,
        mcp_wrapper=mock_mcp_wrapper,
        model_name="test-model"
    )
    
    result = hook_no_compact(test_state)
    
    logger.info(f"✅ Result type: {type(result)}")
    logger.info(f"✅ Result content: {result}")
    
    # Should return empty dict when no compact integration
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result == {}, f"Expected empty dict with no compact integration, got {result}"
    
    logger.info("✅ Test 4 PASSED: No compact integration returns empty dict")
    
    logger.info("\n🎉 ALL TESTS PASSED!")
    logger.info("✅ Compression hook correctly returns LangGraph v2 state updates")
    logger.info("✅ Hook handles all edge cases properly")
    logger.info("✅ Error handling works correctly")


def test_return_format_validation():
    """Validate that the hook return format matches LangGraph v2 expectations."""
    
    logger.info("\n🔍 VALIDATING LANGGRAPH v2 RETURN FORMAT")
    logger.info("=" * 50)
    
    from src.context.compression_hooks import create_compression_hook
    
    # Create minimal hook for format testing
    hook = create_compression_hook()
    
    test_state = {"messages": [{"role": "user", "content": "test"}]}
    result = hook(test_state)
    
    # LangGraph v2 pre_model_hook requirements:
    # 1. Must return a dict (state update)
    # 2. Empty dict means no changes
    # 3. {"messages": [...]} means update messages
    # 4. Must NOT return the full state object
    
    assert isinstance(result, dict), "Hook must return dict for LangGraph v2"
    
    # Check that we're not returning the original state
    assert result is not test_state, "Hook must not return original state object"
    
    # Check that result is either empty dict or has messages key
    if result:  # If not empty
        assert "messages" in result, "Non-empty result must contain 'messages' key"
        assert isinstance(result["messages"], list), "'messages' value must be a list"
    
    logger.info("✅ LangGraph v2 format validation PASSED")
    logger.info(f"   Result type: {type(result)}")
    logger.info(f"   Result keys: {list(result.keys()) if result else 'empty dict'}")


if __name__ == "__main__":
    test_compression_hook_fix()
    test_return_format_validation()
    logger.info("\n🏁 All compression hook tests completed successfully!")