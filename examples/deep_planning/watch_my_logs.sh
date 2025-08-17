#!/bin/bash

# watch_my_logs.sh - Simple monitor for YOUR custom logging messages only
# Filters out LangGraph noise and shows only your strategic logging

LOG_FILE="debug.log"

echo "🔥 YOUR Custom Logs Monitor"
echo "=========================="
echo "📁 File: $LOG_FILE"
echo "🎯 Showing only YOUR custom logging messages"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "⚠️  Log file not found: $LOG_FILE"
    echo "💡 Run: python deep_planning_agent.py"
    exit 1
fi

# Show recent custom logs first
echo "📋 Recent custom logs:"
grep -E "(deep_planning_main|deep_planning_compat|deep_planning_module|mcp_context_tracker|context_manager|langgraph_console_test|🔵|🟢|🔴|🟠|🟡|🏗️|🔧|🤖|✅|📝|⚡|🏁)" "$LOG_FILE" | tail -10
echo ""
echo "🔄 Watching for new custom logs..."
echo ""

# Watch for new custom logs only - NOW INCLUDING CALLBACK LOGS!
tail -f "$LOG_FILE" | grep --line-buffered -E "(deep_planning_main|deep_planning_compat|deep_planning_module|mcp_context_tracker|context_manager|langgraph_console_test|langgraph_execution_callback|langgraph_global_callbacks|🔵|🟢|🔴|🟠|🟡|🏗️|🔧|🤖|✅|📝|⚡|🏁|🚀|🛠️|🎯|🔗|EXEC:|TOOL_START|TOOL_END|LLM_START|LLM_END|AGENT_ACTION|CHAIN_START)" --color=always