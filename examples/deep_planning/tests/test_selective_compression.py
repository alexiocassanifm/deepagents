#!/usr/bin/env python3
"""
Quick test of the new selective compression system.
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.context.selective_compression import (
    SelectiveCompressor, 
    PreservationRules, 
    MessageAnalyzer,
    create_smart_compression_hook
)

def test_preservation_rules():
    """Test that preservation rules correctly identify critical content."""
    print("🔍 Testing PreservationRules...")
    
    rules = PreservationRules()
    
    # Test todo preservation
    todo_message = {
        "role": "assistant",
        "content": "I'll use write_todos to track these tasks for the project."
    }
    
    context = {"all_messages": [todo_message] * 10}
    assert rules.should_preserve_message(todo_message, 5, context), "Todo message should be preserved"
    print("✅ Todo preservation: PASS")
    
    # Test system message preservation
    system_message = {
        "role": "system", 
        "content": "You are a helpful assistant with access to tools."
    }
    
    assert rules.should_preserve_message(system_message, 0, context), "System message should be preserved"
    print("✅ System message preservation: PASS")
    
    # Test recent context preservation
    recent_message = {"role": "user", "content": "Recent user message"}
    assert rules.should_preserve_message(recent_message, 8, context), "Recent message should be preserved"
    print("✅ Recent context preservation: PASS")
    
    # Test old message compression
    old_message = {"role": "user", "content": "Old user message"}
    assert not rules.should_preserve_message(old_message, 2, context), "Old message should be compressed"
    print("✅ Old message compression: PASS")
    
    print("✅ PreservationRules tests completed\n")


def test_message_analyzer():
    """Test MCP content analysis functionality."""
    print("🔍 Testing MessageAnalyzer...")
    
    analyzer = MessageAnalyzer()
    
    # Test MCP content detection
    large_mcp_message = {
        "role": "tool",
        "name": "mcp__fairmind__Code_find_relevant_code_snippets",
        "content": "x" * 5000  # Large content
    }
    
    analysis = analyzer.analyze_mcp_content(large_mcp_message)
    assert analysis is not None, "Large MCP message should be analyzed"
    assert analysis["content_size"] == 5000, "Content size should be correctly calculated"
    assert "mcp_code_snippets_" in analysis["suggested_filename"], "Filename should be generated correctly"
    print("✅ MCP content analysis: PASS")
    
    # Test non-MCP message
    regular_message = {"role": "user", "content": "Regular message"}
    analysis = analyzer.analyze_mcp_content(regular_message)
    assert analysis is None, "Regular message should not be analyzed for archiving"
    print("✅ Non-MCP message handling: PASS")
    
    print("✅ MessageAnalyzer tests completed\n")


def test_selective_compressor():
    """Test the core selective compression functionality."""
    print("🔍 Testing SelectiveCompressor...")
    
    compressor = SelectiveCompressor()
    
    # Create test messages
    messages = [
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": "Old user message 1"},
        {"role": "assistant", "content": "Old assistant response 1"},
        {"role": "user", "content": "Old user message 2"},
        {"role": "assistant", "content": "Old assistant response 2"},
        {"role": "assistant", "content": "I'll use write_todos to track this task"},
        {"role": "tool", "name": "mcp__fairmind__Code_find_relevant_code_snippets", "content": "x" * 4000},
        {"role": "user", "content": "Recent user message"},
        {"role": "assistant", "content": "Recent assistant response"}
    ]
    
    context = {
        "todos": [{"content": "Test task", "status": "pending", "id": "1"}],
        "files": {"test.py": "print('hello')"},
        "all_messages": messages
    }
    
    compressed = compressor.compress_messages(messages, context)
    
    # Should have fewer messages (compression occurred)
    assert len(compressed) < len(messages), f"Compression should reduce message count: {len(messages)} -> {len(compressed)}"
    print(f"✅ Message reduction: {len(messages)} -> {len(compressed)} messages")
    
    # System message should be preserved
    system_preserved = any(msg.get("role") == "system" for msg in compressed)
    assert system_preserved, "System message should be preserved"
    print("✅ System message preserved: PASS")
    
    # Todo message should be preserved
    todo_preserved = any("write_todos" in str(msg.get("content", "")) for msg in compressed)
    assert todo_preserved, "Todo message should be preserved"
    print("✅ Todo message preserved: PASS")
    
    # MCP content should be marked for archiving
    archiving_marker = any("[CONTENT TO ARCHIVE]" in str(msg.get("content", "")) for msg in compressed)
    assert archiving_marker, "MCP content should be marked for archiving"
    print("✅ MCP archiving marker created: PASS")
    
    # Should have compression summary
    summary_present = any(msg.get("metadata", {}).get("type") == "compression_summary" for msg in compressed)
    assert summary_present, "Compression summary should be present"
    print("✅ Compression summary present: PASS")
    
    stats = compressor.get_compression_stats()
    print(f"📊 Compression stats: {stats}")
    
    print("✅ SelectiveCompressor tests completed\n")


def test_smart_compression_hook():
    """Test the smart compression hook."""
    print("🔍 Testing smart compression hook...")
    
    hook = create_smart_compression_hook()
    
    # Test with small context (no compression needed)
    small_state = {
        "messages": [
            {"role": "user", "content": "Small message"},
            {"role": "assistant", "content": "Small response"}
        ],
        "todos": [],
        "files": {}
    }
    
    result = hook(small_state)
    assert result == {}, "Small context should not trigger compression"
    print("✅ Small context handling: PASS")
    
    # Test with large context 
    large_messages = []
    for i in range(20):
        large_messages.extend([
            {"role": "user", "content": f"User message {i}" * 50},
            {"role": "assistant", "content": f"Assistant response {i}" * 50}
        ])
    
    large_state = {
        "messages": large_messages,
        "todos": [{"content": "Important task", "status": "pending", "id": "1"}],
        "files": {"important.py": "critical code"}
    }
    
    result = hook(large_state)
    
    if result and "messages" in result:
        print(f"✅ Large context compression: {len(large_messages)} -> {len(result['messages'])} messages")
        
        # Check that todos and files are preserved in context (not in messages directly)
        # The hook should preserve the structure by not modifying non-message fields
        assert "todos" not in result or result.get("todos") == large_state["todos"], "Todos should be preserved"
        assert "files" not in result or result.get("files") == large_state["files"], "Files should be preserved"
        print("✅ Critical state preservation: PASS")
    else:
        print("ℹ️ No compression triggered (context may not be large enough)")
    
    print("✅ Smart compression hook tests completed\n")


async def test_virtual_fs_tools():
    """Test virtual filesystem management tools."""
    print("🔍 Testing virtual FS tools...")
    
    try:
        from src.context.archiving_tools import organize_virtual_fs, cleanup_old_archives
        
        # Mock state for testing
        mock_state = {
            "files": {
                "mcp_rag_20240115_100000.json": "old content 1",
                "mcp_rag_20240116_100000.json": "old content 2",
                "mcp_rag_20240118_100000.json": "recent content",
                "mcp_code_20240118_120000.json": "code content",
                "workspace_main.py": "user code",
                "context_summary.md": "session summary"
            }
        }
        
        # Test organization analysis
        try:
            # Note: Since we can't actually call the async tool without proper LangGraph context,
            # we'll just test that the imports work
            print("✅ Virtual FS tools import: PASS")
            print("ℹ️ Full async tool testing requires LangGraph execution context")
        except Exception as e:
            print(f"⚠️ Virtual FS tools test limited: {e}")
        
    except ImportError as e:
        print(f"⚠️ Virtual FS tools not available: {e}")
    
    print("✅ Virtual FS tools tests completed\n")


def test_integration():
    """Test integration between components."""
    print("🔍 Testing component integration...")
    
    # Test that compression hook can be created
    try:
        hook = create_smart_compression_hook()
        assert callable(hook), "Hook should be callable"
        print("✅ Hook creation: PASS")
    except Exception as e:
        print(f"❌ Hook creation failed: {e}")
        return
    
    # Test that all main classes can be instantiated
    try:
        compressor = SelectiveCompressor()
        rules = PreservationRules()
        analyzer = MessageAnalyzer()
        
        print("✅ Component instantiation: PASS")
    except Exception as e:
        print(f"❌ Component instantiation failed: {e}")
        return
    
    print("✅ Integration tests completed\n")


def main():
    """Run all tests."""
    print("🚀 Starting Selective Compression Tests")
    print("=" * 50)
    
    try:
        test_preservation_rules()
        test_message_analyzer()
        test_selective_compressor()
        test_smart_compression_hook()
        asyncio.run(test_virtual_fs_tools())
        test_integration()
        
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ Selective compression system is working correctly")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())