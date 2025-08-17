#!/usr/bin/env python3
"""
test_logging.py - Quick test to verify your logging setup is working

This script tests the logging configuration without running the full agent.
"""

import logging
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_logging_setup():
    """Test the logging configuration from deep_planning_agent.py"""
    
    print("🧪 TESTING: Logging configuration")
    print("=" * 50)
    
    # Import the logging setup function
    try:
        from deep_planning_agent import setup_debug_logging
        print("✅ IMPORTED: setup_debug_logging function")
    except ImportError as e:
        print(f"❌ FAILED: Could not import setup_debug_logging: {e}")
        return False
    
    # Call the setup function
    print("🔧 SETUP: Calling setup_debug_logging()...")
    setup_debug_logging()
    print("✅ SETUP: Logging configuration complete")
    
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

if __name__ == "__main__":
    print("🔥 Deep Planning Agent Logging Test")
    print("=" * 50)
    
    success = test_logging_setup()
    
    if success:
        print("\n✅ LOGGING TEST COMPLETE")
        print("🎯 If you see the fire emoji messages above, console logging works!")
        print("📋 Now check debug.log for all messages")
        
        show_recent_logs()
        
        print(f"\n💡 USAGE:")
        print(f"  🔍 Monitor logs: ./watch_my_logs.sh")
        print(f"  📊 Full monitor: ./monitor_logs.sh")
        print(f"  📁 View file: tail -f debug.log")
    else:
        print("\n❌ LOGGING TEST FAILED")
        print("💡 Check the import errors above")