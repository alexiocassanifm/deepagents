"""
Helper tools for virtual filesystem management and MCP content archiving.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Annotated
from langchain_core.tools import tool
from deepagents.state import DeepAgentState
from langgraph.prebuilt import InjectedState

# File naming convention patterns
FILE_NAMING_CONVENTION = {
    # MCP Archives
    "mcp_doc": "mcp_doc_YYYYMMDD_HHMMSS.json",
    "mcp_rag": "mcp_rag_YYYYMMDD_HHMMSS.json", 
    "mcp_code": "mcp_code_YYYYMMDD_HHMMSS.json",
    "mcp_source": "mcp_source_YYYYMMDD_HHMMSS.json",
    
    # Context Management
    "context_summary": "context_summary.md",
    "context_technical": "context_technical.md",
    "context_archive": "context_archive_N.json",
    "context_todos": "context_todos_snapshot.json",
    
    # Workspace
    "workspace": "workspace_*.py",
    "temp": "temp_*.json"
}


@tool
async def organize_virtual_fs(
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """
    Analyze virtual filesystem organization and suggest improvements.
    
    Returns:
        Report on filesystem organization with cleanup suggestions
    """
    files = state.get("files", {})
    
    if not files:
        return "Virtual file system is empty. No organization needed."
    
    # Categorize files by prefix
    categories = {
        "mcp_archives": [],
        "context_files": [],
        "workspace": [],
        "temp_files": [],
        "other": []
    }
    
    for filename in files.keys():
        if filename.startswith("mcp_"):
            categories["mcp_archives"].append(filename)
        elif filename.startswith("context_"):
            categories["context_files"].append(filename)
        elif filename.startswith("workspace_"):
            categories["workspace"].append(filename)
        elif filename.startswith("temp_"):
            categories["temp_files"].append(filename)
        else:
            categories["other"].append(filename)
    
    # Generate report
    report = "## Virtual File System Organization\n\n"
    total_files = len(files)
    total_size = sum(len(str(content)) for content in files.values())
    
    report += f"**Overview**: {total_files} files, {total_size:,} total characters\n\n"
    
    for category, file_list in categories.items():
        if file_list:
            report += f"### {category.replace('_', ' ').title()} ({len(file_list)} files)\n"
            
            # Show first 5 files with sizes
            for filename in file_list[:5]:
                size = len(str(files.get(filename, "")))
                report += f"- {filename} ({size:,} chars)\n"
            
            if len(file_list) > 5:
                report += f"- ... and {len(file_list) - 5} more files\n"
            
            report += "\n"
    
    # Add cleanup suggestions
    cleanup_suggestions = []
    
    # Check for too many MCP archives by type
    mcp_by_type = {}
    for filename in categories["mcp_archives"]:
        parts = filename.split("_")
        if len(parts) >= 2:
            mcp_type = parts[1]
            mcp_by_type.setdefault(mcp_type, []).append(filename)
    
    for mcp_type, type_files in mcp_by_type.items():
        if len(type_files) > 5:
            cleanup_suggestions.append(f"Consider cleaning old {mcp_type} archives (have {len(type_files)}, suggest keeping 3-5)")
    
    # Check for old temp files
    if len(categories["temp_files"]) > 0:
        cleanup_suggestions.append(f"Consider removing {len(categories['temp_files'])} temporary files")
    
    # Check for very large files
    large_files = [(name, len(str(content))) for name, content in files.items() if len(str(content)) > 10000]
    if large_files:
        cleanup_suggestions.append(f"Large files detected: {len(large_files)} files over 10k characters")
    
    if cleanup_suggestions:
        report += "### Cleanup Suggestions\n"
        for suggestion in cleanup_suggestions:
            report += f"- {suggestion}\n"
        report += "\nUse `cleanup_old_archives()` tool to perform cleanup.\n"
    else:
        report += "### Status: Well Organized ✅\nNo cleanup needed.\n"
    
    return report


@tool
async def cleanup_old_archives(
    prefix: str,
    state: Annotated[DeepAgentState, InjectedState],
    keep_last_n: int = 3
) -> str:
    """
    Remove old archive files keeping only the most recent ones.
    
    Args:
        prefix: File prefix to clean (e.g., "mcp_rag_", "temp_")
        keep_last_n: Number of recent files to keep (default: 3)
    
    Returns:
        Summary of cleanup actions performed
    """
    files = state.get("files", {})
    matching_files = [f for f in files.keys() if f.startswith(prefix)]
    
    if len(matching_files) <= keep_last_n:
        return f"No cleanup needed for {prefix}* files ({len(matching_files)} files, keeping {keep_last_n})"
    
    # Sort files by timestamp (embedded in filename)
    try:
        sorted_files = sorted(matching_files, key=lambda f: _extract_timestamp_from_filename(f))
        files_to_remove = sorted_files[:-keep_last_n]
        
        # Note: In a real implementation, this would generate Commands to remove files
        # For now, we simulate the cleanup action
        removed_count = len(files_to_remove)
        kept_files = sorted_files[-keep_last_n:]
        
        return f"""Cleanup Summary for {prefix}* files:
- Found {len(matching_files)} matching files
- Would remove {removed_count} old files
- Would keep {len(kept_files)} most recent files: {', '.join(kept_files)}

Note: To actually perform cleanup, implement file removal commands in agent workflow."""
        
    except Exception as e:
        return f"Error cleaning {prefix}* files: {str(e)}"


@tool
async def archive_content_helper(
    content: str,
    filename: str,
    summary: str,
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """
    Helper tool for archiving large content to virtual FS.
    
    Args:
        content: Content to archive
        filename: Suggested filename
        summary: Brief summary of content
    
    Returns:
        Confirmation of archiving action with file reference
    """
    if not content:
        return "Error: No content provided for archiving"
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"archived_content_{timestamp}.json"
    
    # Validate and clean filename
    clean_filename = _clean_filename(filename)
    content_size = len(content)
    
    # Create archival metadata
    archive_metadata = {
        "archived_at": datetime.now().isoformat(),
        "original_size": content_size,
        "summary": summary[:200],  # Limit summary length
        "archive_tool": "archive_content_helper"
    }
    
    # Structure the archived content
    archived_data = {
        "metadata": archive_metadata,
        "summary": summary,
        "content": content
    }
    
    # Note: In real implementation, this would use write_file command
    # For now, return the archiving instructions
    return f"""Archive Helper Result:
✅ Content ready for archiving

**Filename**: {clean_filename}
**Size**: {content_size:,} characters
**Summary**: {summary[:100]}{'...' if len(summary) > 100 else ''}

**Next Steps**:
Use write_file('{clean_filename}', content) to complete archiving.

The content has been prepared with metadata for efficient retrieval."""


@tool
async def get_archiving_suggestions(
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """
    Analyze current context and suggest content for archiving.
    
    Returns:
        Suggestions for content that could be archived
    """
    messages = state.get("messages", [])
    files = state.get("files", {})
    
    suggestions = []
    
    # Analyze messages for large tool outputs
    for i, message in enumerate(messages):
        if message.get("role") == "tool":
            content = str(message.get("content", ""))
            if len(content) > 3000:  # Large content threshold
                tool_name = message.get("name", "unknown_tool")
                suggestions.append({
                    "type": "large_tool_output",
                    "message_index": i,
                    "tool_name": tool_name,
                    "size": len(content),
                    "suggested_filename": _generate_filename_for_tool(tool_name)
                })
    
    # Analyze files for cleanup opportunities
    large_files = [(name, len(str(content))) for name, content in files.items() if len(str(content)) > 8000]
    for filename, size in large_files:
        if filename.startswith("mcp_") and not filename.endswith("_summary.json"):
            suggestions.append({
                "type": "large_file_summarization",
                "filename": filename,
                "size": size,
                "suggested_action": "create_summary"
            })
    
    if not suggestions:
        return "No archiving suggestions at this time. Context appears well-managed."
    
    report = "## Archiving Suggestions\n\n"
    
    tool_suggestions = [s for s in suggestions if s["type"] == "large_tool_output"]
    if tool_suggestions:
        report += "### Large Tool Outputs (consider archiving)\n"
        for suggestion in tool_suggestions:
            report += f"- {suggestion['tool_name']}: {suggestion['size']:,} chars → {suggestion['suggested_filename']}\n"
        report += "\n"
    
    file_suggestions = [s for s in suggestions if s["type"] == "large_file_summarization"]
    if file_suggestions:
        report += "### Large Files (consider summarizing)\n"
        for suggestion in file_suggestions:
            report += f"- {suggestion['filename']}: {suggestion['size']:,} chars\n"
        report += "\n"
    
    report += "Use archive_content_helper() to archive specific content."
    
    return report


def _extract_timestamp_from_filename(filename: str) -> str:
    """Extract timestamp from filename for sorting."""
    match = re.search(r'(\d{8}_\d{6})', filename)
    return match.group(1) if match else "00000000_000000"


def _clean_filename(filename: str) -> str:
    """Clean and validate filename for virtual FS."""
    # Remove invalid characters
    clean = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure it has an extension
    if '.' not in clean:
        clean += '.json'
    
    # Limit length
    if len(clean) > 100:
        name, ext = clean.rsplit('.', 1)
        clean = name[:95] + '.' + ext
    
    return clean


def _generate_filename_for_tool(tool_name: str) -> str:
    """Generate appropriate filename for a tool output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Map common tool patterns to prefixes
    if "document_content" in tool_name:
        return f"mcp_doc_{timestamp}.json"
    elif "rag_retrieve" in tool_name:
        return f"mcp_rag_{timestamp}.json"
    elif "code_snippets" in tool_name:
        return f"mcp_code_{timestamp}.json"
    elif "get_file" in tool_name:
        return f"mcp_source_{timestamp}.json"
    else:
        return f"mcp_tool_{timestamp}.json"


def get_archiving_tools():
    """Get list of archiving tools for agent integration."""
    return [
        organize_virtual_fs,
        cleanup_old_archives,
        archive_content_helper,
        get_archiving_suggestions
    ]