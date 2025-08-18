"""
Prompt extensions for intelligent content archiving in deep planning agents.
"""

SMART_ARCHIVING_PROMPT = """
## Intelligent Content Archiving

When you encounter [CONTENT TO ARCHIVE] markers in messages:

### 🔍 Recognition
Look for messages containing:
- `[CONTENT TO ARCHIVE]` section headers
- Tool name and content size information  
- Suggested filename for archiving
- Full content to be archived

### 📋 Information Extraction
From each marker, extract:
- **Tool name**: The MCP tool that generated the content
- **Content size**: Size in characters
- **Suggested filename**: Recommended file name with timestamp
- **Summary**: Brief description of the content
- **Urgency**: IMMEDIATE (>5k chars) or SUGGESTED (3-5k chars)

### ⚡ Action Protocol
When you find archiving markers:

1. **Immediate Response**:
   ```
   I found large content from [tool_name] that needs archiving.
   Size: [X,XXX] characters
   Action: Archiving to [suggested_filename]
   ```

2. **Execute Archiving**:
   ```python
   write_file("suggested_filename", content_from_marker)
   ```

3. **Confirm and Reference**:
   ```
   ✅ Archived [tool_name] output to [filename]
   📊 Content summary: [brief_summary]
   📁 Access via: read_file("[filename]")
   ```

### 📝 Example Workflow

**User**: "Find authentication code in the project"

**You**: "I'll search for authentication code..."
[MCP tool returns large code snippets]

**[CONTENT TO ARCHIVE]** marker appears with 8,000 character code snippets

**You**: 
```
I found 15 authentication code snippets (8,000 characters). Archiving for efficient access...

write_file("mcp_code_snippets_20240118_143022.json", [full_content])

✅ Archived code snippets to mcp_code_snippets_20240118_143022.json
📊 Found authentication in: auth.py, login.py, middleware.py
📁 Access archived code: read_file("mcp_code_snippets_20240118_143022.json")
```

### 🎯 Key Benefits
- **Clean context**: Keep working memory focused on current task
- **Preserved access**: All content remains available via read_file()
- **Organized storage**: Timestamp-based naming for easy tracking
- **Efficient workflow**: Reference archived files instead of repeating large content
"""

VIRTUAL_FS_MANAGEMENT_PROMPT = """
## Virtual File System Management

Maintain a clean and organized virtual filesystem for optimal performance:

### 🔧 Regular Maintenance

#### **Periodic Organization Check**
Use `organize_virtual_fs()` every 10-15 interactions:
```python
organize_virtual_fs()
```
This provides:
- File categorization (MCP archives, workspace, temp files)
- Size analysis and storage overview
- Cleanup suggestions and recommendations

#### **Proactive Cleanup**
When file count exceeds reasonable limits:
```python
cleanup_old_archives("mcp_rag_", 3)  # Keep 3 most recent RAG archives
cleanup_old_archives("mcp_code_", 3)  # Keep 3 most recent code archives
cleanup_old_archives("temp_", 0)     # Remove all temp files
```

### 📁 File Organization Patterns

#### **Naming Conventions**
- **MCP Archives**: `mcp_[type]_YYYYMMDD_HHMMSS.json`
  - `mcp_doc_*`: Document content from get_document_content
  - `mcp_rag_*`: RAG search results
  - `mcp_code_*`: Code snippets and source files
  - `mcp_source_*`: Full source file content

- **Context Files**: `context_[purpose].md`
  - `context_summary.md`: Current session summary
  - `context_technical.md`: Technical decisions and context

- **Workspace**: `workspace_[name].[ext]`
  - User-created files and working documents
  - Generated code and analysis results

- **Temporary**: `temp_[purpose].json`
  - Intermediate processing results
  - Should be cleaned up regularly

#### **Size Management**
- **Individual files**: Aim for <10k characters per file
- **Total filesystem**: Monitor overall size via organize_virtual_fs()
- **Archive threshold**: Archive content >3k characters from MCP tools

### 🎯 Access Patterns

#### **Reference Archived Content**
Instead of repeating large content in responses:
```
The authentication implementation includes 3 main patterns:
1. JWT validation (see mcp_code_20240118_143022.json, lines 45-120)
2. Session management (see mcp_source_20240118_144501.json)  
3. OAuth integration (archived in mcp_doc_20240118_142010.json)

Use read_file() to examine specific implementations.
```

#### **Provide Context Summaries**
When referencing archived files:
```
📁 mcp_rag_20240118_143500.json contains:
- 15 search results about user authentication
- Relevance scores: 0.85-0.95
- Key findings: JWT, session management, OAuth flows
- Access via: read_file("mcp_rag_20240118_143500.json")
```

### 🔄 Maintenance Workflow Example

```python
# Check current organization
organize_virtual_fs()

# Example output analysis:
# "MCP Archives (12 files): 3 doc, 5 rag, 4 code archives"
# "Cleanup suggested: Consider cleaning old rag archives (have 5, suggest keeping 3)"

# Perform cleanup based on suggestions
cleanup_old_archives("mcp_rag_", 3)

# Verify organization
organize_virtual_fs()

# Result: "MCP Archives (10 files): Well organized ✅"
```

### ⚠️ Important Guidelines

1. **Never delete workspace files**: User-created content should be preserved
2. **Preserve recent archives**: Keep 3-5 most recent files per archive type
3. **Monitor total size**: Use organize_virtual_fs() to track overall filesystem health
4. **Clean temp files**: Regularly remove temporary processing files
5. **Archive large content**: Use archiving for any MCP output >3k characters

This systematic approach ensures your virtual filesystem remains organized, searchable, and performant throughout long conversations.
"""

def enhance_agent_instructions(base_instructions: str) -> str:
    """Add smart archiving capabilities to agent instructions."""
    enhanced_instructions = f"""{base_instructions}

{SMART_ARCHIVING_PROMPT}

{VIRTUAL_FS_MANAGEMENT_PROMPT}

## Integration Notes

These archiving capabilities are automatically integrated when smart compression is enabled. 
The archiving system works seamlessly with your existing tools:

- **write_file()**: Used for archiving large MCP content
- **read_file()**: Access archived content when needed  
- **ls()**: Browse your virtual filesystem
- **organize_virtual_fs()**: Analyze and manage file organization
- **cleanup_old_archives()**: Remove old archives while preserving recent ones

The system maintains context cleanliness while preserving all information for future access.
"""
    
    return enhanced_instructions