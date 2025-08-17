#!/bin/bash

# monitor_logs.sh - Real-time log monitoring for Deep Planning Agent
# This script watches debug.log and highlights your custom logging messages

LOG_FILE="debug.log"
COLORS=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo "🔥 Deep Planning Agent Log Monitor"
echo "=================================="
echo "📁 Monitoring: $LOG_FILE"
echo "🎯 Filtering for custom logging messages"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "⚠️  Log file not found: $LOG_FILE"
    echo "💡 Try running the agent first to create the log file"
    exit 1
fi

# Function to colorize output
colorize_line() {
    local line="$1"
    
    # Your custom loggers
    if [[ "$line" =~ "deep_planning_main" ]]; then
        echo -e "${GREEN}🏗️  MAIN: ${line}${NC}"
    elif [[ "$line" =~ "deep_planning_compat" ]]; then
        echo -e "${BLUE}🔧 COMPAT: ${line}${NC}"
    elif [[ "$line" =~ "deep_planning_module" ]]; then
        echo -e "${PURPLE}📦 MODULE: ${line}${NC}"
    elif [[ "$line" =~ "langgraph_console_test" ]]; then
        echo -e "${YELLOW}🚀 TEST: ${line}${NC}"
    elif [[ "$line" =~ "mcp_context_tracker" ]]; then
        echo -e "${CYAN}🎯 MCP_TRACKER: ${line}${NC}"
    elif [[ "$line" =~ "context_manager" ]]; then
        echo -e "${WHITE}📊 CONTEXT_MGR: ${line}${NC}"
    # Your emoji patterns
    elif [[ "$line" =~ "🔵|🟢|🔴|🟠|🟡" ]]; then
        echo -e "${RED}💎 MONITORING: ${line}${NC}"
    elif [[ "$line" =~ "🏗️|🔧|🤖|✅|📝|⚡|🏁" ]]; then
        echo -e "${GREEN}⭐ FERRARI: ${line}${NC}"
    # LangGraph internal (dimmed)
    elif [[ "$line" =~ "langgraph_runtime_inmem|langgraph_api|LiteLLM|httpx" ]]; then
        if [[ "$line" =~ "ERROR" ]]; then
            echo -e "${RED}❌ LANGGRAPH_ERROR: ${line}${NC}"
        else
            echo -e "\033[2m🔧 langgraph: ${line}\033[0m"  # Dimmed
        fi
    # Errors (any)
    elif [[ "$line" =~ "ERROR|error|Error" ]]; then
        echo -e "${RED}❌ ERROR: ${line}${NC}"
    # Warnings
    elif [[ "$line" =~ "WARNING|warning|Warning" ]]; then
        echo -e "${YELLOW}⚠️  WARNING: ${line}${NC}"
    # Default
    else
        echo "$line"
    fi
}

# Main monitoring loop
echo "👀 Starting log monitor..."
echo ""

# Show last 5 lines first
echo "📋 Last 5 log entries:"
tail -5 "$LOG_FILE" | while read line; do
    colorize_line "$line"
done
echo ""
echo "🔄 Watching for new entries..."
echo ""

# Follow the log file and colorize output
tail -f "$LOG_FILE" | while read line; do
    colorize_line "$line"
done