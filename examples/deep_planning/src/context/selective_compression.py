"""
Selective compression system for deep planning agents.
Preserves critical elements while compressing safe content.
"""

from typing import List, Dict, Set, Any, Optional, Union
import json
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Core preservation rules
PRESERVE_ALWAYS = {
    "todos": "Task tracking critical for agent continuity",
    "files": "Virtual filesystem maintains shared context", 
    "system_messages": "Agent instructions must persist",
    "recent_context": "Last 3-5 exchanges for immediate context",
    "tool_results": "Recent tool outputs for decision making",
    "plans": "Planning information for multi-phase tasks"
}

# MCP tools that produce large outputs requiring archiving
MCP_CONTENT_TOOLS = {
    "mcp__fairmind__General_get_document_content": "doc",
    "mcp__fairmind__General_rag_retrieve_documents": "rag",
    "mcp__fairmind__General_rag_retrieve_specific_documents": "rag_specific",
    "mcp__fairmind__Code_find_relevant_code_snippets": "code_snippets",
    "mcp__fairmind__Code_get_file": "source"
}

# Content size thresholds for archiving
ARCHIVING_THRESHOLDS = {
    "large_content": 3000,  # Characters requiring archiving consideration
    "huge_content": 5000,   # Characters requiring immediate archiving
}


class PreservationRules:
    """Defines what content must never be compressed."""
    
    def __init__(self):
        self.todo_indicators = [
            "write_todos", "todo list", "task tracking", "pending", 
            "in_progress", "completed", "TodoWrite"
        ]
        self.recent_context_size = 5  # Number of recent messages to preserve
    
    def should_preserve_message(self, message: Any, index: int, context: Dict) -> bool:
        """
        Determine if a message should be preserved.
        
        Args:
            message: Message to evaluate (dict or LangChain Message object)
            index: Position in message list
            context: Additional context (todos, state, etc.)
        """
        # Always preserve todos
        if self._contains_todos(message):
            logger.debug(f"Preserving message {index}: contains todo content")
            return True
            
        # Always preserve system instructions
        role = self._get_message_role(message)
        if role == "system":
            logger.debug(f"Preserving message {index}: system message")
            return True
            
        # Preserve recent messages (last N)
        all_messages = context.get("all_messages", [])
        if index >= len(all_messages) - self.recent_context_size:
            logger.debug(f"Preserving message {index}: recent context (last {self.recent_context_size})")
            return True
            
        # Preserve recent tool results
        if self._is_recent_tool_result(message, index, context):
            logger.debug(f"Preserving message {index}: recent tool result")
            return True
            
        # Preserve virtual file system references
        if self._references_virtual_fs(message):
            logger.debug(f"Preserving message {index}: references virtual FS")
            return True
            
        return False
    
    def _contains_todos(self, message: Any) -> bool:
        """Check if message contains todo-related content."""
        # Handle both dict and LangChain Message objects
        if hasattr(message, 'content'):
            content = str(getattr(message, 'content', "")).lower()
        elif hasattr(message, 'get'):
            content = str(message.get("content", "")).lower()
        else:
            content = str(message).lower()
        
        return any(indicator.lower() in content for indicator in self.todo_indicators)
    
    def _get_message_role(self, message: Any) -> str:
        """Get role from message, handling both dict and LangChain Message objects."""
        if hasattr(message, 'type'):
            # LangChain Message objects have a type attribute
            message_type = message.type
            if message_type == 'human':
                return 'user'
            elif message_type == 'ai':
                return 'assistant'
            elif message_type == 'system':
                return 'system'
            elif message_type == 'tool':
                return 'tool'
            return message_type
        elif hasattr(message, 'get'):
            return message.get("role", "unknown")
        elif hasattr(message, '__class__'):
            class_name = message.__class__.__name__.lower()
            if 'human' in class_name:
                return 'user'
            elif 'ai' in class_name:
                return 'assistant'
            elif 'system' in class_name:
                return 'system'
            elif 'tool' in class_name:
                return 'tool'
        return "unknown"
    
    def _get_message_content(self, message: Any) -> str:
        """Get content from message, handling both dict and LangChain Message objects."""
        if hasattr(message, 'content'):
            return str(getattr(message, 'content', ""))
        elif hasattr(message, 'get'):
            return str(message.get("content", ""))
        else:
            return str(message)
    
    def _is_recent_tool_result(self, message: Any, index: int, context: Dict) -> bool:
        """Check if this is a recent tool result that should be preserved."""
        # Tool messages should be preserved if recent
        if self._get_message_role(message) == "tool":
            all_messages = context.get("all_messages", [])
            return index >= len(all_messages) - (self.recent_context_size * 2)  # More generous for tool results
        return False
    
    def _references_virtual_fs(self, message: Any) -> bool:
        """Check if message references virtual file system operations."""
        content = self._get_message_content(message).lower()
        fs_indicators = ["write_file", "read_file", "edit_file", "ls()", "virtual filesystem"]
        return any(indicator in content for indicator in fs_indicators)


class MessageAnalyzer:
    """Analyzes message content and extracts key information."""
    
    def _get_message_role(self, message: Any) -> str:
        """Get role from message, handling both dict and LangChain Message objects."""
        if hasattr(message, 'type'):
            # LangChain Message objects have a type attribute
            message_type = message.type
            if message_type == 'human':
                return 'user'
            elif message_type == 'ai':
                return 'assistant'
            elif message_type == 'system':
                return 'system'
            elif message_type == 'tool':
                return 'tool'
            return message_type
        elif hasattr(message, 'get'):
            return message.get("role", "unknown")
        elif hasattr(message, '__class__'):
            class_name = message.__class__.__name__.lower()
            if 'human' in class_name:
                return 'user'
            elif 'ai' in class_name:
                return 'assistant'
            elif 'system' in class_name:
                return 'system'
            elif 'tool' in class_name:
                return 'tool'
        return "unknown"
    
    def _get_message_content(self, message: Any) -> str:
        """Get content from message, handling both dict and LangChain Message objects."""
        if hasattr(message, 'content'):
            return str(getattr(message, 'content', ""))
        elif hasattr(message, 'get'):
            return str(message.get("content", ""))
        else:
            return str(message)
    
    def _get_message_name(self, message: Any) -> str:
        """Get name/tool name from message, handling both dict and LangChain Message objects."""
        if hasattr(message, 'name'):
            return str(getattr(message, 'name', ""))
        elif hasattr(message, 'get'):
            return message.get("name", "")
        else:
            return ""
    
    def extract_topics(self, messages: List[Any]) -> List[str]:
        """Extract key topics from a list of messages."""
        topics = set()
        
        for message in messages:
            content = self._get_message_content(message)
            
            # Extract common technical concepts
            tech_patterns = [
                r'\b(function|class|method|variable)\s+(\w+)',
                r'\b(import|from)\s+(\w+)',
                r'\b(API|endpoint|service|database|query)\b',
                r'\b(error|exception|bug|issue)\b',
                r'\b(test|testing|unittest|pytest)\b'
            ]
            
            for pattern in tech_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                topics.update([match[1] if isinstance(match, tuple) else match for match in matches])
        
        return list(topics)[:10]  # Return top 10 topics
    
    def extract_timeframe(self, messages: List[Any]) -> str:
        """Extract timeframe information from messages."""
        if not messages:
            return "Unknown timeframe"
        
        # Simple timeframe based on message count
        count = len(messages)
        if count <= 5:
            return "Brief conversation"
        elif count <= 15:
            return "Medium conversation"
        else:
            return "Extended conversation"
    
    def analyze_mcp_content(self, message: Any) -> Optional[Dict]:
        """Analyze if message contains large MCP content requiring archiving."""
        # Use helper to get role and check if it's a tool message
        if self._get_message_role(message) != "tool":
            return None
            
        tool_name = self._get_message_name(message)
        content = self._get_message_content(message)
        content_size = len(content)
        
        # Check if this is a known large MCP tool
        if not any(mcp_tool in tool_name for mcp_tool in MCP_CONTENT_TOOLS.keys()):
            return None
            
        # Check size thresholds
        if content_size < ARCHIVING_THRESHOLDS["large_content"]:
            return None
            
        # Determine archiving urgency
        urgency = "immediate" if content_size >= ARCHIVING_THRESHOLDS["huge_content"] else "suggested"
        
        return {
            "tool_name": tool_name,
            "content_size": content_size,
            "urgency": urgency,
            "summary": self._extract_content_summary(content),
            "suggested_filename": self._generate_filename(tool_name)
        }
    
    def _extract_content_summary(self, content: str) -> str:
        """Extract a brief summary from large content."""
        content_str = str(content)
        
        # Try to extract structured data summaries
        if content_str.strip().startswith('{'):
            try:
                data = json.loads(content_str)
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    return f"JSON data with keys: {', '.join(keys)}"
                elif isinstance(data, list):
                    return f"JSON array with {len(data)} items"
            except:
                pass
        
        # Fallback to simple text summary
        lines = content_str.split('\n')[:3]
        return ' '.join(lines)[:200] + "..." if len(content_str) > 200 else content_str
    
    def _generate_filename(self, tool_name: str) -> str:
        """Generate appropriate filename for MCP content."""
        # Map tool names to file prefixes
        for mcp_tool, prefix in MCP_CONTENT_TOOLS.items():
            if mcp_tool in tool_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"mcp_{prefix}_{timestamp}.json"
        
        # Fallback filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"mcp_content_{timestamp}.json"


class SelectiveCompressor:
    """Performs intelligent compression preserving critical elements."""
    
    def __init__(self):
        self.preservation_rules = PreservationRules()
        self.message_analyzer = MessageAnalyzer()
        self.compression_stats = {
            "messages_processed": 0,
            "messages_preserved": 0,
            "messages_compressed": 0,
            "archiving_markers_created": 0
        }
    
    def compress_messages(self, messages: List[Any], state_context: Dict) -> List[Any]:
        """
        Compress messages while preserving critical elements.
        
        Args:
            messages: List of messages to process
            state_context: DeepAgentState context for preservation rules
            
        Returns:
            Compressed message list with critical elements intact
        """
        if not messages:
            return messages
            
        logger.info(f"Starting selective compression of {len(messages)} messages")
        
        preserved_indices = set()
        compressed_messages = []
        conversation_buffer = []
        archiving_markers = []
        
        # Phase 1: Identify what to preserve and what to archive
        for i, message in enumerate(messages):
            # Check for preservation
            if self.preservation_rules.should_preserve_message(message, i, state_context):
                preserved_indices.add(i)
                self.compression_stats["messages_preserved"] += 1
            
            # Check for MCP content archiving
            mcp_analysis = self.message_analyzer.analyze_mcp_content(message)
            if mcp_analysis:
                archiving_marker = self._create_archiving_marker(message, mcp_analysis)
                archiving_markers.append((i, archiving_marker))
                self.compression_stats["archiving_markers_created"] += 1
        
        # Phase 2: Process messages
        for i, message in enumerate(messages):
            # Check if this message should be replaced with archiving marker
            archiving_marker = next((marker for idx, marker in archiving_markers if idx == i), None)
            if archiving_marker:
                compressed_messages.append(archiving_marker)
                continue
                
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
                    self.compression_stats["messages_compressed"] += len(conversation_buffer)
        
        # Handle remaining buffer
        if conversation_buffer:
            summary = self._compress_conversation_buffer(conversation_buffer)
            compressed_messages.append(summary)
            self.compression_stats["messages_compressed"] += len(conversation_buffer)
        
        self.compression_stats["messages_processed"] = len(messages)
        
        logger.info(f"Compression complete: {len(messages)} → {len(compressed_messages)} messages")
        logger.info(f"Stats: {self.compression_stats}")
        
        return compressed_messages
    
    def _compress_conversation_buffer(self, buffer: List[Any]) -> Dict:
        """Compress a buffer of old conversations into a summary."""
        if not buffer:
            return {"role": "system", "content": "[Empty conversation buffer]"}
            
        # Extract key information using helper methods
        user_requests = [msg for msg in buffer if self.message_analyzer._get_message_role(msg) == "user"]
        assistant_actions = [msg for msg in buffer if self.message_analyzer._get_message_role(msg) == "assistant"]
        tool_calls = [msg for msg in buffer if self.message_analyzer._get_message_role(msg) == "tool"]
        
        topics = self.message_analyzer.extract_topics(buffer)
        timeframe = self.message_analyzer.extract_timeframe(buffer)
        
        summary_content = f"""[Conversation Summary - {len(buffer)} messages compressed]

User Requests: {len(user_requests)} requests
Assistant Actions: {len(assistant_actions)} responses  
Tool Calls: {len(tool_calls)} tool invocations
Key Topics: {', '.join(topics) if topics else 'General conversation'}
Timeframe: {timeframe}

Note: This summary replaces {len(buffer)} historical messages to manage context size.
Full conversation history available in virtual FS if archived.
Compression performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return {
            "role": "system",
            "content": summary_content,
            "metadata": {
                "type": "compression_summary",
                "original_count": len(buffer),
                "compressed_at": datetime.now().isoformat(),
                "compression_ratio": len(summary_content) / sum(len(self.message_analyzer._get_message_content(msg)) for msg in buffer)
            }
        }
    
    def _create_archiving_marker(self, message: Any, mcp_analysis: Dict) -> Dict:
        """Create a marker that the agent can recognize and act on."""
        tool_name = mcp_analysis["tool_name"]
        suggested_filename = mcp_analysis["suggested_filename"]
        content_summary = mcp_analysis["summary"]
        content_size = mcp_analysis["content_size"]
        urgency = mcp_analysis["urgency"]
        
        urgency_indicator = "⚠️ IMMEDIATE" if urgency == "immediate" else "💡 SUGGESTED"
        
        # Get content using helper method
        original_content = self.message_analyzer._get_message_content(message)
        
        marker_content = f"""[CONTENT TO ARCHIVE] {urgency_indicator}

Tool: {tool_name}
Size: {content_size:,} characters
Suggested filename: {suggested_filename}
Summary: {content_summary}

Instructions: Use write_file('{suggested_filename}', content) to archive this content.
Content will remain accessible via read_file() while reducing context size.

Full content:
{original_content}

[END CONTENT TO ARCHIVE]"""
        
        # Handle both dict and LangChain Message objects
        if hasattr(message, 'get'):
            # Dict format
            return {
                **message,
                "content": marker_content,
                "metadata": {
                    "type": "archiving_marker",
                    "original_size": content_size,
                    "suggested_filename": suggested_filename,
                    "urgency": urgency,
                    "created_at": datetime.now().isoformat()
                }
            }
        else:
            # LangChain Message object - convert to dict format
            return {
                "role": self.message_analyzer._get_message_role(message),
                "content": marker_content,
                "name": self.message_analyzer._get_message_name(message),
                "metadata": {
                    "type": "archiving_marker",
                    "original_size": content_size,
                    "suggested_filename": suggested_filename,
                    "urgency": urgency,
                    "created_at": datetime.now().isoformat()
                }
            }
    
    def get_compression_stats(self) -> Dict:
        """Get current compression statistics."""
        return self.compression_stats.copy()
    
    def reset_stats(self):
        """Reset compression statistics."""
        self.compression_stats = {
            "messages_processed": 0,
            "messages_preserved": 0, 
            "messages_compressed": 0,
            "archiving_markers_created": 0
        }


def is_mcp_content_tool(tool_name: str) -> bool:
    """Check if a tool name is a known MCP content tool."""
    return any(mcp_tool in tool_name for mcp_tool in MCP_CONTENT_TOOLS.keys())


def generate_mcp_filename(tool_name: str) -> str:
    """Generate appropriate filename for MCP content."""
    analyzer = MessageAnalyzer()
    return analyzer._generate_filename(tool_name)


def create_smart_compression_hook():
    """Create a smart compression hook for deep planning agents."""
    
    def smart_compression_hook(state) -> Dict:
        """Smart compression hook that preserves critical deepagents elements."""
        messages = state.get("messages", [])
        
        if not messages:
            return {}
            
        # Create context for preservation rules
        context = {
            "todos": state.get("todos", []),
            "files": state.get("files", {}),
            "plans": state.get("plans", []),
            "context_history": state.get("context_history", []),
            "all_messages": messages
        }
        
        # Perform selective compression
        compressor = SelectiveCompressor()
        compressed_messages = compressor.compress_messages(messages, context)
        
        # Only return updates if compression actually occurred
        if len(compressed_messages) < len(messages):
            logger.info(f"Smart compression reduced messages: {len(messages)} → {len(compressed_messages)}")
            return {"messages": compressed_messages}
        
        return {}
    
    return smart_compression_hook