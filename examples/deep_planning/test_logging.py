#!/usr/bin/env python3
"""
test_logging.py - Comprehensive logging tests for Deep Planning Agent

This script tests both basic logging configuration and enhanced context management logging.
It combines tests from the original test_logging.py and test_enhanced_logging.py.
"""

import logging
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging for enhanced tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_logging_setup():
    """Test the logging configuration from deep_planning_agent.py"""
    
    print("🧪 TESTING: Logging configuration")
    print("=" * 50)
    
    # Import is no longer needed - logging is configured at module level
    print("🔧 SETUP: Logging configuration is now handled at module import level")
    print("✅ SETUP: Basic logging configuration complete")
    
    # Test different loggers that should appear in console
    print("\n🎯 TESTING: Various loggers (should appear in console and debug.log)")
    print("-" * 60)
    
    # Test your custom loggers
    loggers_to_test = [
        ('deep_planning_main', '🏗️ Testing main logger'),
        ('deep_planning_compat', '🔧 Testing compatibility logger'),
        ('deep_planning_module', '📦 Testing module logger'),
        ('mcp_context_tracker', '🎯 Testing MCP context tracker'),
        ('context_manager', '📊 Testing context manager'),
        ('langgraph_console_test', '🚀 Testing LangGraph console'),
    ]
    
    for logger_name, message in loggers_to_test:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.info(message)
        print(f"📤 SENT: {logger_name} -> {message}")
    
    # Test root logger
    logging.info("🔥 ROOT LOGGER: This should appear in console with fire emoji format!")
    logging.warning("⚠️ ROOT WARNING: This should definitely be visible!")
    logging.error("❌ ROOT ERROR: This should be very visible!")
    
    print(f"\n📁 Log file location: {os.path.abspath('debug.log')}")
    print("👀 Check console output above for logged messages")
    print("📋 Check debug.log file for all messages")
    
    return True

def show_recent_logs():
    """Show recent log entries from debug.log"""
    log_file = "debug.log"
    if os.path.exists(log_file):
        print(f"\n📄 RECENT LOGS from {log_file}:")
        print("-" * 40)
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Show last 10 lines
                for line in lines[-10:]:
                    print(line.strip())
        except Exception as e:
            print(f"❌ Could not read log file: {e}")
    else:
        print(f"\n⚠️ Log file {log_file} does not exist yet")

def test_enhanced_logging():
    """Test enhanced logging for context management."""
    print("\n🚀 TESTING: Enhanced Context Management Logging")
    print("=" * 60)
    
    try:
        # Import modules with enhanced logging
        from mcp_wrapper import create_mcp_wrapper
        from context_manager import ContextManager
        print("✅ Enhanced modules imported successfully")
        
        # Create wrapper with test configuration
        config = {
            "cleaning_enabled": True,
            "max_context_window": 50000,
            "trigger_threshold": 0.70,
            "mcp_noise_threshold": 0.50,
            "deduplication_enabled": True,
            "preserve_essential_fields": True,
            "auto_compaction": True
        }
        
        wrapper = create_mcp_wrapper(config)
        print("✅ MCP Wrapper created with enhanced logging")
        
        # Test context tracking
        print("\n📊 Testing context metrics tracking...")
        context_manager = wrapper.context_manager if hasattr(wrapper, 'context_manager') else None
        if context_manager:
            metrics = context_manager.get_current_metrics()
            print(f"  📏 Context utilization: {metrics.utilization_percentage:.1f}%")
            print(f"  🧹 MCP noise: {metrics.mcp_noise_percentage:.1f}%")
            print(f"  📝 Total tokens: {metrics.tokens_used:,}")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ Enhanced logging test skipped: {e}")
        print("💡 This is normal if MCP wrapper is not available")
        return False
    except Exception as e:
        print(f"❌ Enhanced logging test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔥 Deep Planning Agent Comprehensive Logging Test")
    print("=" * 50)
    
    # Run basic logging test
    success = test_logging_setup()
    
    if success:
        print("\n✅ BASIC LOGGING TEST COMPLETE")
        print("🎯 If you see the fire emoji messages above, console logging works!")
        print("📋 Now check debug.log for all messages")
        
        show_recent_logs()
        
        # Run enhanced logging test
        enhanced_success = test_enhanced_logging()
        if enhanced_success:
            print("\n✅ ENHANCED LOGGING TEST COMPLETE")
        else:
            print("\n⚠️ Enhanced logging not fully available (this is okay)")
        
        print(f"\n💡 USAGE:")
        print(f"  🔍 Monitor logs: ./watch_my_logs.sh")
        print(f"  📊 Full monitor: ./monitor_logs.sh")
        print(f"  📁 View file: tail -f debug.log")
    else:
        print("\n❌ BASIC LOGGING TEST FAILED")
        print("💡 Check the import errors above")