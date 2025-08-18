"""
DISABLED MODULE - MCP Cleaning Strategies No Longer Needed

This module has been disabled as part of the context management simplification.
MCP cleaning strategies are no longer necessary because:

1. LiteLLM provides accurate token counting without pattern matching
2. No false positives from MCP content detection
3. Simple threshold-based compression without noise detection
4. Focus on essential functionality: token counting + compression triggering

The functionality in this module was causing import errors and complexity
without providing real value in the simplified architecture.
"""

# Dummy implementations to prevent import errors
class CleaningStrategy:
    """Disabled stub for backward compatibility."""
    pass

def create_default_cleaning_strategies(config=None):
    """Disabled - returns empty list."""
    return []

# All other functionality has been removed for simplification