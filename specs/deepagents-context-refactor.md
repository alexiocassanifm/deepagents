# DeepAgents Context Management Refactor

## Executive Summary

This document outlines a comprehensive refactor of the deepagents context management system, transitioning from aggressive generic compression to **intelligent selective preservation** with **agent-driven archiving**.

### Current Problem
- Pre-hook compresses **everything indiscriminatingly** (including todos, file system, agent instructions)
- Ignores deepagents architecture (virtual file system, state management)
- Causes loss of critical context needed for agent continuity

### Solution Overview
- **Selective compression** preserving critical elements
- **Virtual file system** utilization for content archiving  
- **Agent-driven** archiving for transparency and control
- **Progressive cleanup** to maintain codebase quality

---

## Current State Analysis

### Problem 1: Indiscriminate Compression

**File**: `examples/deep_planning/src/context/compression_hooks.py:186-191`

```python
return {
    "messages": [
        RemoveMessage(id="__remove_all__"),  # ❌ Removes EVERYTHING
        *compacted_messages  # Only compressed messages remain
    ]
}
```

**Impact**: 
- Todos get lost → agent loses task tracking
- Virtual file system state not preserved → context sharing broken
- Agent instructions compressed → behavioral changes

### Problem 2: Architectural Mismatch

The current pre-hook is a **generic LangGraph pattern** that doesn't understand deepagents:

- `DeepAgentState` has rich structure (todos, files, plans, context_history)
- Virtual file system designed for context sharing
- Built-in tools (`ls`, `read_file`, `write_file`) for FS interaction
- But compression hook only looks at `messages`

### Problem 3: MCP Content Bloat

MCP tools from Fairmind produce large outputs:
- `get_document_content`: 5-15k tokens
- `rag_retrieve_documents`: 3-10k tokens  
- `find_relevant_code_snippets`: 8-20k tokens
- These stay in context causing rapid token exhaustion

---

## Proposed Architecture

### Core Principle: Selective Preservation

Instead of compressing everything, **preserve critical elements** and compress only safe content.

```python
PRESERVE_ALWAYS = {
    "todos": "Task tracking critical for agent continuity",
    "files": "Virtual filesystem maintains shared context", 
    "system_messages": "Agent instructions must persist",
    "recent_context": "Last 3-5 exchanges for immediate context",
    "tool_results": "Recent tool outputs for decision making",
    "plans": "Planning information for multi-phase tasks"
}

COMPRESSIBLE_ELEMENTS = {
    "historical_conversation": "Old user-assistant exchanges",
    "verbose_tool_outputs": "Long tool results from past actions",
    "duplicate_information": "Repeated explanations or examples"
}
```

### Architecture Components

#### 1. Selective Compression Engine
```
src/deepagents/context/selective_compression.py
├── SelectiveCompressor
├── PreservationRules  
├── MessageAnalyzer
└── CompressionStrategy
```

#### 2. MCP Content Manager
```
src/deepagents/context/mcp_content_manager.py
├── MCPContentDetector
├── ArchivingManager
├── ContentSummarizer
└── PointerGenerator
```

#### 3. Agent Extensions
```
src/deepagents/extensions/
├── smart_archiving_prompts.py
├── virtual_fs_tools.py
└── context_management_helpers.py
```

---

## Design Details

### 1. Selective Compression System

#### PreservationRules Engine

```python
class PreservationRules:
    """Defines what content must never be compressed."""
    
    def should_preserve_message(self, message: Dict, index: int, context: Dict) -> bool:
        """
        Determine if a message should be preserved.
        
        Args:
            message: Message to evaluate
            index: Position in message list
            context: Additional context (todos, state, etc.)
        """
        # Always preserve todos
        if self._contains_todos(message):
            return True
            
        # Always preserve system instructions
        if message.get("role") == "system":
            return True
            
        # Preserve recent messages (last 5)
        if index >= len(context.get("all_messages", [])) - 5:
            return True
            
        # Preserve recent tool results
        if self._is_recent_tool_result(message, context):
            return True
            
        return False
    
    def _contains_todos(self, message: Dict) -> bool:
        """Check if message contains todo-related content."""
        content = str(message.get("content", "")).lower()
        todo_indicators = ["write_todos", "todo list", "task tracking", "pending", "in_progress", "completed"]
        return any(indicator in content for indicator in todo_indicators)
```

#### SelectiveCompressor Implementation

```python
class SelectiveCompressor:
    """Performs intelligent compression preserving critical elements."""
    
    def __init__(self):
        self.preservation_rules = PreservationRules()
        self.message_analyzer = MessageAnalyzer()
    
    def compress_messages(self, messages: List[Dict], state_context: Dict) -> List[Dict]:
        """
        Compress messages while preserving critical elements.
        
        Returns:
            Compressed message list with critical elements intact
        """
        preserved_indices = set()
        compressed_messages = []
        conversation_buffer = []
        
        # Phase 1: Identify what to preserve
        for i, message in enumerate(messages):
            if self.preservation_rules.should_preserve_message(message, i, state_context):
                preserved_indices.add(i)
        
        # Phase 2: Process messages
        for i, message in enumerate(messages):
            if i in preserved_indices:
                # Preserve as-is
                compressed_messages.append(message)
            else:
                # Accumulate for compression
                conversation_buffer.append(message)
                
                # Compress buffer when it gets large
                if len(conversation_buffer) >= 10:
                    summary = self._compress_conversation_buffer(conversation_buffer)
                    compressed_messages.append(summary)
                    conversation_buffer = []
        
        # Handle remaining buffer
        if conversation_buffer:
            summary = self._compress_conversation_buffer(conversation_buffer)
            compressed_messages.append(summary)
        
        return compressed_messages
    
    def _compress_conversation_buffer(self, buffer: List[Dict]) -> Dict:
        """Compress a buffer of old conversations into a summary."""
        # Extract key information
        user_requests = [msg for msg in buffer if msg.get("role") == "user"]
        assistant_actions = [msg for msg in buffer if msg.get("role") == "assistant"]
        
        summary_content = f"""
[Conversation Summary - {len(buffer)} messages compressed]

User Requests: {len(user_requests)} requests
Assistant Actions: {len(assistant_actions)} responses
Key Topics: {self._extract_topics(buffer)}
Timeframe: {self._extract_timeframe(buffer)}

Note: This summary replaces {len(buffer)} historical messages to manage context size.
Full conversation history available in context_archive.json if needed.
"""
        
        return {
            "role": "system",
            "content": summary_content,
            "metadata": {
                "type": "compression_summary",
                "original_count": len(buffer),
                "compressed_at": datetime.now().isoformat()
            }
        }
```

### 2. MCP Content Archiving

#### Agent-Driven Approach

Instead of automatically archiving, the system **marks content for archiving** and lets the agent decide:

```python
def mark_mcp_for_archiving(self, messages: List[Dict]) -> List[Dict]:
    """
    Mark large MCP outputs for archiving to virtual FS.
    Agent will see markers and can choose to archive.
    """
    marked_messages = []
    
    for message in messages:
        if self._is_large_mcp_output(message):
            # Create archiving marker
            marker = self._create_archiving_marker(message)
            marked_messages.append(marker)
        else:
            marked_messages.append(message)
    
    return marked_messages

def _create_archiving_marker(self, message: Dict) -> Dict:
    """Create a marker that the agent can recognize and act on."""
    tool_name = self._extract_tool_name(message)
    suggested_filename = self._generate_filename(tool_name)
    content_summary = self._extract_summary(message.content)
    
    marker_content = f"""
[CONTENT TO ARCHIVE]
Tool: {tool_name}
Size: {len(str(message.content))} characters
Suggested filename: {suggested_filename}
Summary: {content_summary}

Instructions: Use write_file('{suggested_filename}', content) to archive this content.
Content will remain accessible via read_file() while reducing context size.

Full content:
{message.content}
[END CONTENT TO ARCHIVE]
"""
    
    return {
        **message,
        "content": marker_content,
        "metadata": {
            "type": "archiving_marker",
            "original_size": len(str(message.content)),
            "suggested_filename": suggested_filename
        }
    }
```

#### Virtual File System Organization

Since the FS is flat, use naming conventions for organization:

```python
FILE_NAMING_CONVENTION = {
    # MCP Archives
    "mcp_doc_YYYYMMDD_HHMMSS.json": "Document content from get_document_content",
    "mcp_rag_YYYYMMDD_HHMMSS.json": "RAG search results",
    "mcp_code_YYYYMMDD_HHMMSS.json": "Code snippets from find_relevant_code",
    "mcp_source_YYYYMMDD_HHMMSS.json": "Full source files from get_file",
    
    # Context Management
    "context_summary.md": "Current session summary",
    "context_technical.md": "Technical decisions and context",
    "context_archive_N.json": "Archived conversation segments",
    "context_todos_snapshot.json": "Historical todo states",
    
    # Workspace
    "workspace_*.py": "User-created or agent-generated code",
    "workspace_*.md": "Working documents and notes",
    "temp_*.json": "Temporary data (auto-cleanup)"
}
```

### 3. Agent Prompt Extensions

#### Smart Archiving Instructions

```python
SMART_ARCHIVING_PROMPT = """
## Intelligent Content Archiving

When you encounter [CONTENT TO ARCHIVE] markers in messages:

1. **Recognize the marker**: Look for [CONTENT TO ARCHIVE] sections
2. **Extract information**:
   - Tool name that generated the content
   - Suggested filename 
   - Content summary
   - Full content to archive

3. **Take action**:
   - Use write_file() with the suggested filename
   - Save the full content to the virtual filesystem
   - Confirm archiving in your response
   - Reference the archived file instead of repeating content

4. **Example workflow**:
   ```
   User: "Find authentication code"
   You: Searching for authentication code...
   [CONTENT TO ARCHIVE appears with large code snippets]
   You: write_file("mcp_code_snippets_20240118_143022.json", <content>)
   You: "I found 15 authentication code snippets and archived them to 
        mcp_code_snippets_20240118_143022.json. The key findings are..."
   ```

This keeps your working context clean while preserving all information.
You can always use read_file() to access archived content when needed.
"""

VIRTUAL_FS_MANAGEMENT_PROMPT = """
## Virtual File System Management

Maintain a clean and organized virtual filesystem:

1. **Regular maintenance**:
   - Use ls() to check current files periodically
   - Remove old MCP archives (keep last 3-5 per type)
   - Maintain consistent naming with prefixes

2. **File organization**:
   - Use organize_virtual_fs() for filesystem overview
   - Group related files with consistent prefixes
   - Clean up temporary files regularly

3. **Access patterns**:
   - Reference archived files by name in responses
   - Use read_file() when you need to examine archived content
   - Provide file summaries rather than full content in responses

Example maintenance:
```
You: Let me check my filesystem organization...
You: organize_virtual_fs()
[Shows 15 files, suggests cleanup of old archives]
You: I'll clean up old MCP archives keeping the 3 most recent...
You: [Performs cleanup using appropriate tool calls]
```
"""
```

### 4. Helper Tools

#### Virtual FS Management Tools

```python
@tool
async def organize_virtual_fs(
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """
    Analyze virtual filesystem organization and suggest improvements.
    
    Returns:
        Report on filesystem organization with cleanup suggestions
    """
    files = await ls(state)
    
    # Categorize files by prefix
    categories = {
        "mcp_archives": [],
        "context_files": [],
        "workspace": [],
        "temp_files": [],
        "other": []
    }
    
    for filename in files:
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
    report = "Virtual File System Organization:\n\n"
    
    for category, file_list in categories.items():
        if file_list:
            report += f"**{category.replace('_', ' ').title()}** ({len(file_list)} files):\n"
            
            # Show first 5 files
            for filename in file_list[:5]:
                size = len(state.files.get(filename, ""))
                report += f"  - {filename} ({size:,} chars)\n"
            
            if len(file_list) > 5:
                report += f"  ... and {len(file_list) - 5} more\n"
            
            report += "\n"
    
    # Add cleanup suggestions
    cleanup_suggestions = []
    
    # Check for too many MCP archives
    mcp_by_type = {}
    for filename in categories["mcp_archives"]:
        mcp_type = filename.split("_")[1] if "_" in filename else "unknown"
        mcp_by_type.setdefault(mcp_type, []).append(filename)
    
    for mcp_type, files in mcp_by_type.items():
        if len(files) > 5:
            cleanup_suggestions.append(f"Consider cleaning old {mcp_type} archives (have {len(files)}, suggest keeping 3-5)")
    
    # Check for old temp files
    if categories["temp_files"]:
        cleanup_suggestions.append(f"Consider removing {len(categories['temp_files'])} temporary files")
    
    if cleanup_suggestions:
        report += "**Cleanup Suggestions:**\n"
        for suggestion in cleanup_suggestions:
            report += f"- {suggestion}\n"
    
    return report

@tool
async def cleanup_old_archives(
    prefix: str,
    keep_last_n: int = 3,
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """
    Remove old archive files keeping only the most recent ones.
    
    Args:
        prefix: File prefix to clean (e.g., "mcp_rag_", "temp_")
        keep_last_n: Number of recent files to keep (default: 3)
    
    Returns:
        Summary of cleanup actions performed
    """
    files = await ls(state)
    matching_files = [f for f in files if f.startswith(prefix)]
    
    if len(matching_files) <= keep_last_n:
        return f"No cleanup needed for {prefix}* files ({len(matching_files)} files, keeping {keep_last_n})"
    
    # Sort files by timestamp (embedded in filename)
    # Files with format: prefix_YYYYMMDD_HHMMSS.ext
    try:
        sorted_files = sorted(matching_files, key=lambda f: extract_timestamp_from_filename(f))
        files_to_remove = sorted_files[:-keep_last_n]
        
        removed_count = 0
        for filename in files_to_remove:
            # Note: In real implementation, this would generate appropriate Commands
            # For now, document the action
            removed_count += 1
        
        return f"Cleaned {len(files_to_remove)} old {prefix}* files, kept {keep_last_n} most recent"
        
    except Exception as e:
        return f"Error cleaning {prefix}* files: {str(e)}"

def extract_timestamp_from_filename(filename: str) -> str:
    """Extract timestamp from filename for sorting."""
    import re
    match = re.search(r'(\d{8}_\d{6})', filename)
    return match.group(1) if match else "00000000_000000"
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (4-6 hours)

#### Step 1.1: Create Selective Compression Module
**File**: `src/deepagents/context/selective_compression.py`

```python
"""
Selective compression system for deepagents.
Preserves critical elements while compressing safe content.
"""

from typing import List, Dict, Set, Any, Optional
import json
import re
from datetime import datetime

# Core preservation rules
PRESERVE_ALWAYS = {
    "todos": "Task tracking critical for agent continuity",
    "files": "Virtual filesystem maintains shared context", 
    "system_messages": "Agent instructions must persist",
    "recent_context": "Last 3-5 exchanges for immediate context",
    "tool_results": "Recent tool outputs for decision making",
    "plans": "Planning information for multi-phase tasks"
}

# MCP tools that produce large outputs
MCP_CONTENT_TOOLS = {
    "mcp__fairmind__General_get_document_content": "doc",
    "mcp__fairmind__General_rag_retrieve_documents": "rag",
    "mcp__fairmind__General_rag_retrieve_specific_documents": "rag_specific",
    "mcp__fairmind__Code_find_relevant_code_snippets": "code_snippets",
    "mcp__fairmind__Code_get_file": "source"
}

class PreservationRules:
    # Implementation details here
    pass

class MessageAnalyzer:
    # Implementation details here
    pass

class SelectiveCompressor:
    # Implementation details here
    pass
```

#### Step 1.2: Refactor Compression Hook
**File**: `examples/deep_planning/src/context/compression_hooks.py`

**Actions**:
1. Replace current aggressive compression logic
2. Integrate SelectiveCompressor
3. Add MCP content marking
4. Remove LLM compression complexity

**Before** (current):
```python
def compression_hook(state: DeepAgentState) -> DeepAgentState:
    # Aggressive compression removing everything
    return {
        "messages": [
            RemoveMessage(id="__remove_all__"),
            *compacted_messages
        ]
    }
```

**After** (new):
```python
def compression_hook(state: DeepAgentState) -> DeepAgentState:
    messages = state.get("messages", [])
    
    # Create context for preservation rules
    context = {
        "todos": state.get("todos", []),
        "files": state.get("files", {}),
        "plans": state.get("plans", []),
        "all_messages": messages
    }
    
    # Selective compression preserving critical elements
    compressor = SelectiveCompressor()
    compressed_messages = compressor.compress_messages(messages, context)
    
    return {"messages": compressed_messages}
```

#### Step 1.3: Update compact_integration.py
**File**: `examples/deep_planning/src/context/compact_integration.py`

**Actions**:
1. Remove LLM compression initialization (lines 98-112)
2. Remove `_initialize_llm_compressor` method
3. Remove `_analyze_with_llm` method  
4. Simplify to use only SelectiveCompressor

### Phase 2: Agent Extensions (3-4 hours)

#### Step 2.1: Create Agent Prompt Extensions
**File**: `src/deepagents/extensions/smart_archiving_prompts.py`

```python
"""
Prompt extensions for intelligent content archiving.
"""

SMART_ARCHIVING_PROMPT = """
## Intelligent Content Archiving
[Detailed prompts as designed above]
"""

VIRTUAL_FS_MANAGEMENT_PROMPT = """
## Virtual File System Management  
[Detailed prompts as designed above]
"""

def enhance_agent_instructions(base_instructions: str) -> str:
    """Add smart archiving capabilities to agent instructions."""
    return base_instructions + "\n\n" + SMART_ARCHIVING_PROMPT + "\n\n" + VIRTUAL_FS_MANAGEMENT_PROMPT
```

#### Step 2.2: Create Virtual FS Helper Tools
**File**: `src/deepagents/extensions/virtual_fs_tools.py`

```python
"""
Helper tools for virtual filesystem management.
"""

from langchain_core.tools import tool
from typing import Annotated

@tool
async def organize_virtual_fs(state: Annotated[DeepAgentState, InjectedState]) -> str:
    # Implementation as designed above
    pass

@tool  
async def cleanup_old_archives(prefix: str, keep_last_n: int = 3, state = None) -> str:
    # Implementation as designed above
    pass

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
        Confirmation of archiving action
    """
    # Use write_file to save content
    # Return confirmation with file reference
    pass
```

#### Step 2.3: Update graph.py Integration
**File**: `src/deepagents/graph.py`

```python
def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
    enable_planning_approval: bool = False,
    checkpointer: Optional[Union[str, Any]] = None,
    pre_model_hook: Optional[Callable] = None,
    enable_smart_compression: bool = False,  # NEW
):
    """Create a deep agent with optional smart compression."""
    
    # Enhance instructions if smart compression enabled
    if enable_smart_compression:
        from deepagents.extensions.smart_archiving_prompts import enhance_agent_instructions
        from deepagents.extensions.virtual_fs_tools import organize_virtual_fs, cleanup_old_archives
        
        instructions = enhance_agent_instructions(instructions)
        tools = list(tools) + [organize_virtual_fs, cleanup_old_archives]
    
    # Create smart compression hook if needed
    if enable_smart_compression and pre_model_hook is None:
        from deepagents.context.selective_compression import create_smart_compression_hook
        pre_model_hook = create_smart_compression_hook()
    
    # Rest of existing logic unchanged
    # ...
```

### Phase 3: Testing & Validation (3-4 hours)

#### Step 3.1: Unit Tests
**File**: `tests/test_selective_compression.py`

```python
"""
Tests for selective compression system.
"""

import pytest
from deepagents.context.selective_compression import (
    SelectiveCompressor, 
    PreservationRules,
    MCP_CONTENT_TOOLS
)

class TestPreservationRules:
    def test_todos_always_preserved(self):
        """Todo messages must never be compressed."""
        rules = PreservationRules()
        
        todo_message = {
            "role": "assistant", 
            "content": "I'll use write_todos to track these tasks..."
        }
        
        assert rules.should_preserve_message(todo_message, 5, {})
    
    def test_system_messages_preserved(self):
        """System instructions must always be preserved."""
        rules = PreservationRules()
        
        system_message = {"role": "system", "content": "You are a helpful assistant..."}
        
        assert rules.should_preserve_message(system_message, 0, {})
    
    def test_recent_messages_preserved(self):
        """Recent messages (last 5) should be preserved."""
        rules = PreservationRules()
        
        context = {"all_messages": ["msg"] * 10}  # 10 total messages
        
        # Message at index 7 (within last 5) should be preserved
        assert rules.should_preserve_message({}, 7, context)
        
        # Message at index 3 (not in last 5) should not be preserved
        assert not rules.should_preserve_message({}, 3, context)

class TestSelectiveCompressor:
    def test_compression_preserves_critical_elements(self):
        """Critical elements should survive compression."""
        compressor = SelectiveCompressor()
        
        messages = [
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "Old user message"},
            {"role": "assistant", "content": "Old assistant response"},
            {"role": "assistant", "content": "Using write_todos to track..."},
            {"role": "user", "content": "Recent user message"}
        ]
        
        context = {"all_messages": messages}
        compressed = compressor.compress_messages(messages, context)
        
        # Should preserve system, todos, and recent messages
        # Should compress old conversation
        assert len(compressed) < len(messages)
        
        # Check that todos message is preserved
        todo_preserved = any("write_todos" in str(msg.get("content", "")) for msg in compressed)
        assert todo_preserved
    
    def test_mcp_content_marking(self):
        """Large MCP outputs should be marked for archiving."""
        compressor = SelectiveCompressor()
        
        large_mcp_message = {
            "role": "tool",
            "name": "mcp__fairmind__Code_find_relevant_code_snippets", 
            "content": "x" * 5000  # Large content
        }
        
        marked = compressor.mark_mcp_for_archiving([large_mcp_message])
        
        assert len(marked) == 1
        assert "[CONTENT TO ARCHIVE]" in marked[0]["content"]
        assert "write_file" in marked[0]["content"]

class TestMCPContentManagement:
    def test_mcp_tool_detection(self):
        """Should correctly identify MCP tools that produce large outputs."""
        from deepagents.context.selective_compression import is_mcp_content_tool
        
        assert is_mcp_content_tool("mcp__fairmind__Code_find_relevant_code_snippets")
        assert is_mcp_content_tool("mcp__fairmind__General_rag_retrieve_documents")
        assert not is_mcp_content_tool("regular_tool_name")
    
    def test_filename_generation(self):
        """Should generate appropriate filenames for MCP content."""
        from deepagents.context.selective_compression import generate_mcp_filename
        
        filename = generate_mcp_filename("mcp__fairmind__Code_find_relevant_code_snippets")
        
        assert filename.startswith("mcp_code_snippets_")
        assert filename.endswith(".json")
        assert len(filename.split("_")) >= 4  # prefix_type_date_time.ext
```

#### Step 3.2: Integration Tests
**File**: `tests/test_agent_archiving.py`

```python
"""
Integration tests for agent-driven archiving.
"""

import pytest
from deepagents import create_deep_agent

@pytest.mark.asyncio
async def test_agent_archives_mcp_content():
    """Agent should recognize and archive MCP content markers."""
    
    # Create agent with smart compression
    agent = create_deep_agent(
        tools=[],
        instructions="Test agent for archiving",
        enable_smart_compression=True
    )
    
    # Simulate message with archiving marker
    initial_state = {
        "messages": [
            {"role": "user", "content": "Test archiving"},
            {
                "role": "assistant", 
                "content": """
[CONTENT TO ARCHIVE]
Tool: mcp__fairmind__Code_find_relevant_code_snippets
Size: 5000 characters
Suggested filename: mcp_code_snippets_20240118_143022.json
Summary: Found 15 code snippets

Full content:
{"snippets": [{"file": "auth.py", "content": "def authenticate()..."}, ...]}
[END CONTENT TO ARCHIVE]
"""
            }
        ]
    }
    
    # Agent should process and archive
    result = await agent.ainvoke(initial_state)
    
    # Verify archiving occurred
    assert "mcp_code_snippets_" in result.get("files", {})
    
    # Verify agent response references archived file
    final_message = result["messages"][-1]["content"]
    assert "archived" in final_message.lower()
    assert "mcp_code_snippets_" in final_message

@pytest.mark.asyncio  
async def test_agent_cleans_old_archives():
    """Agent should clean up old archive files when requested."""
    
    agent = create_deep_agent(
        tools=[],
        instructions="Test agent",
        enable_smart_compression=True
    )
    
    # Start with multiple old archive files
    initial_state = {
        "messages": [{"role": "user", "content": "Please clean up old archives"}],
        "files": {
            "mcp_rag_20240115_100000.json": "old content 1",
            "mcp_rag_20240116_100000.json": "old content 2", 
            "mcp_rag_20240117_100000.json": "recent content 1",
            "mcp_rag_20240118_100000.json": "recent content 2",
            "workspace_code.py": "user code"
        }
    }
    
    result = await agent.ainvoke(initial_state)
    
    # Should keep recent files and user workspace
    remaining_files = result.get("files", {})
    assert "workspace_code.py" in remaining_files  # User files preserved
    
    # Should clean old archives but keep recent ones
    rag_files = [f for f in remaining_files if f.startswith("mcp_rag_")]
    assert len(rag_files) <= 3  # Kept recent archives only
```

#### Step 3.3: Performance Tests
**File**: `tests/test_compression_performance.py`

```python
"""
Performance tests for compression system.
"""

import time
import pytest
from deepagents.context.selective_compression import SelectiveCompressor

class TestCompressionPerformance:
    def test_compression_speed(self):
        """Compression should complete in under 100ms for typical inputs."""
        compressor = SelectiveCompressor()
        
        # Create typical message set (50 messages)
        messages = []
        for i in range(50):
            messages.extend([
                {"role": "user", "content": f"User request {i}"},
                {"role": "assistant", "content": f"Assistant response {i}" * 100}  # Long responses
            ])
        
        context = {"all_messages": messages}
        
        start_time = time.time()
        compressed = compressor.compress_messages(messages, context)
        end_time = time.time()
        
        compression_time = (end_time - start_time) * 1000  # ms
        
        assert compression_time < 100  # Should complete in under 100ms
        assert len(compressed) < len(messages)  # Should actually compress
    
    def test_memory_efficiency(self):
        """Compression should reduce memory usage significantly."""
        compressor = SelectiveCompressor()
        
        # Create large message set
        large_content = "x" * 10000  # 10K chars each
        messages = [
            {"role": "user", "content": large_content},
            {"role": "assistant", "content": large_content}
        ] * 20  # 40 messages total
        
        original_size = sum(len(str(msg)) for msg in messages)
        
        compressed = compressor.compress_messages(messages, {"all_messages": messages})
        compressed_size = sum(len(str(msg)) for msg in compressed)
        
        reduction_ratio = compressed_size / original_size
        
        assert reduction_ratio < 0.3  # Should achieve 70%+ reduction
```

### Phase 4: Documentation & Cleanup (2-3 hours)

#### Step 4.1: Update CLAUDE.md
**File**: `CLAUDE.md`

Add section:
```markdown
## Context Management System

DeepAgents uses an intelligent context management system that:

### Selective Compression
- **Preserves critical elements**: todos, file system state, agent instructions
- **Compresses safely**: historical conversations, verbose outputs  
- **Maintains continuity**: recent context and tool results always available

### Agent-Driven Archiving
- **MCP content archiving**: Large outputs from Fairmind MCP tools automatically marked for archiving
- **Transparent process**: Agent sees markers and chooses to archive content
- **Virtual filesystem utilization**: Content stored using built-in file tools (write_file, read_file)

### Usage
```python
# Enable smart compression
agent = create_deep_agent(
    tools=[your_tools],
    instructions="Your agent prompt", 
    enable_smart_compression=True  # NEW: Enables selective compression
)

# Agent will automatically:
# 1. Preserve todos and critical context
# 2. Archive large MCP outputs to virtual FS
# 3. Maintain clean, navigable context
```

### File System Organization
The virtual filesystem uses naming conventions for organization:
- `mcp_rag_*.json`: RAG search results
- `mcp_code_*.json`: Code snippets and files
- `mcp_doc_*.json`: Document content
- `context_*.md`: Context summaries and technical notes
- `workspace_*`: User-created files

### Monitoring
Use built-in tools to monitor filesystem:
```python
# Check filesystem organization
agent.invoke({"messages": [{"role": "user", "content": "organize_virtual_fs()"}]})

# Clean old archives
agent.invoke({"messages": [{"role": "user", "content": "cleanup_old_archives('mcp_rag_', 3)"}]})
```
```

#### Step 4.2: Create Migration Guide
**File**: `docs/CONTEXT_MIGRATION_GUIDE.md`

```markdown
# Context Management Migration Guide

## Overview
This guide covers migrating from the old aggressive compression system to the new selective compression with agent-driven archiving.

## Breaking Changes
1. **Compression behavior**: No longer compresses todos, file system, or recent context
2. **MCP handling**: Large MCP outputs marked for archiving instead of staying in context
3. **Agent prompts**: New archiving instructions added automatically

## Migration Steps

### For Existing Agents
```python
# Old way
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    pre_model_hook=create_compression_hook()  # Old aggressive compression
)

# New way  
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,
    enable_smart_compression=True  # New selective compression
)
```

### Feature Flag Rollout
For gradual migration, use environment variable:
```bash
export DEEPAGENTS_SMART_COMPRESSION=true
```

### Validating Migration
1. **Todo preservation**: Verify todos persist across context limits
2. **MCP archiving**: Check that large MCP outputs get archived to virtual FS
3. **Performance**: Monitor compression overhead (target: <100ms)
4. **Context quality**: Verify agent maintains coherence with compressed context

## Troubleshooting

### Common Issues
1. **Agent not archiving MCP content**
   - Check that `enable_smart_compression=True`
   - Verify MCP tools are in `MCP_CONTENT_TOOLS` list
   - Look for [CONTENT TO ARCHIVE] markers in messages

2. **Todos getting lost**
   - Verify preservation rules are working
   - Check that todo-related messages have proper indicators
   - Enable debug logging for compression decisions

3. **Virtual FS getting full**
   - Use `organize_virtual_fs()` tool regularly
   - Implement periodic cleanup with `cleanup_old_archives()`
   - Monitor file count and sizes

### Debug Logging
```python
import logging
logging.getLogger('deepagents.context').setLevel(logging.DEBUG)
```
```

#### Step 4.3: File Cleanup Plan
**Actions**:

1. **Remove obsolete files**:
   ```
   # After testing confirms new system works
   rm examples/deep_planning/src/context/llm_compression.py  # If not used elsewhere
   rm tests/test_old_compression.py  # If exists
   ```

2. **Clean up compact_integration.py**:
   - Remove LLM compression methods (lines 173-214)
   - Remove `_analyze_with_llm` method (lines 397-421)
   - Remove LLM initialization code (lines 98-112)
   - Keep only: context analysis, token counting, threshold checking

3. **Update imports and dependencies**:
   - Remove unused LLM compression imports
   - Clean up configuration files
   - Remove unnecessary YAML settings

4. **Archive backups**:
   ```bash
   # Create dated backup directory outside project
   mkdir -p ~/deepagents_backups/context_refactor_$(date +%Y%m%d)
   
   # Move backups out of project
   mv backups/context_refactor_* ~/deepagents_backups/
   ```

---

## Success Metrics

### Functional Requirements
- [ ] **100% todo preservation**: Todos never lost during compression
- [ ] **Virtual FS utilization**: MCP content successfully archived and retrievable
- [ ] **Context continuity**: Agent maintains coherent behavior across compression
- [ ] **Transparent archiving**: Agent successfully recognizes and acts on archiving markers

### Performance Requirements  
- [ ] **Compression speed**: <100ms overhead for typical workloads
- [ ] **Memory efficiency**: 40-60% reduction in context size for large conversations
- [ ] **Token savings**: 30-50% reduction in tokens for MCP-heavy workflows
- [ ] **FS management**: Virtual filesystem stays <10MB per session

### Quality Requirements
- [ ] **Code reduction**: 30% reduction in complexity (fewer lines of compression code)
- [ ] **Test coverage**: 90%+ coverage for new compression logic  
- [ ] **Documentation**: Complete docs for new system
- [ ] **Migration support**: Smooth transition from old system

---

## Risk Analysis

### Technical Risks

#### Risk: Agent doesn't archive content
**Probability**: Medium  
**Impact**: High  
**Mitigation**:
- Add fallback: if marker ignored for 3+ turns, auto-compress with warning
- Enhance prompt engineering with examples
- Add debugging tools to identify why archiving failed

#### Risk: Performance degradation
**Probability**: Low
**Impact**: Medium
**Mitigation**: 
- Benchmark against current system
- Optimize preservation rule checking
- Add performance monitoring

#### Risk: Context loss during migration
**Probability**: Low
**Impact**: High
**Mitigation**:
- Feature flag for gradual rollout
- Comprehensive testing before deployment
- Easy rollback to old system if needed

### Business Risks

#### Risk: User confusion about new behavior
**Probability**: Medium
**Impact**: Low
**Mitigation**:
- Clear documentation of changes
- Migration guide with examples
- Transparent archiving process

#### Risk: Breaking existing workflows
**Probability**: Low
**Impact**: High
**Mitigation**:
- Backward compatibility where possible
- Comprehensive testing of existing examples
- Staged rollout with monitoring

---

## Implementation Timeline

### Week 1: Core Development
- **Days 1-2**: Selective compression system implementation
- **Days 3-4**: MCP content archiving and agent extensions  
- **Day 5**: Initial testing and debugging

### Week 2: Integration & Testing
- **Days 1-2**: Full integration with deepagents
- **Days 3-4**: Comprehensive testing suite
- **Day 5**: Performance optimization and cleanup

### Week 3: Documentation & Deployment  
- **Days 1-2**: Complete documentation and migration guides
- **Days 3-4**: User testing and feedback incorporation
- **Day 5**: Production deployment and monitoring

---

## Conclusion

This refactor transforms deepagents context management from a blunt compression tool to an intelligent system that:

1. **Understands the architecture**: Works with todos, virtual FS, and agent state
2. **Preserves what matters**: Critical elements never lost to compression
3. **Scales efficiently**: Large MCP outputs archived, not accumulated
4. **Maintains transparency**: Agent controls archiving process
5. **Stays maintainable**: Simpler codebase with clear responsibilities

The agent-driven approach ensures transparency while the selective compression maintains the power of the original system without its drawbacks.