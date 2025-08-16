# Compact Implementation Analysis

## Overview & Goals

Compact (also known as `/compact`, `/smol`, or context summarization) is an intelligent context window management feature that automatically condenses conversation history when the context limit is reached. The feature transforms long conversations into structured summaries while preserving essential technical details, code patterns, and task continuity.

**Core Objectives:**
- Automatically detect when context window is approaching capacity
- Generate comprehensive conversation summaries that preserve technical context
- Enable seamless task continuation after context compression
- Maintain conversation flow without losing critical information
- Support both manual (`/compact`, `/smol`) and automatic context management

## Architecture Overview

### Context Window Management Flow
```
Token Threshold Reached → Context Analysis → Summary Generation → 
Context Replacement → Continuation Prompt → Task Resumption
```

### Core Components
- **ContextManager**: Token counting and context window analysis
- **SummarizeTask Tool**: Automated conversation summarization
- **Slash Commands**: Manual compact triggers (`/compact`, `/smol`)
- **Continuation System**: Post-summary task resumption

## Core Implementation

### Slash Command Integration
**Location**: `src/core/slash-commands/index.ts`

The compact functionality is triggered through multiple slash commands that map to the same underlying tool:

```typescript
const commandReplacements: Record<string, string> = {
  newtask: newTaskToolResponse(),
  smol: condenseToolResponse(),        // Legacy alias
  compact: condenseToolResponse(),     // Main command
  newrule: newRuleToolResponse(),
  reportbug: reportBugToolResponse(),
  "deep-planning": deepPlanningToolResponse(),
}
```

**Command Processing Logic:**
```typescript
if (SUPPORTED_DEFAULT_COMMANDS.includes(commandName)) {
  const textWithoutSlashCommand = text.substring(0, slashCommandStartIndex) + 
                                  text.substring(slashCommandEndIndex)
  const processedText = commandReplacements[commandName] + textWithoutSlashCommand
  
  return { processedText: processedText, needsClinerulesFileCheck: false }
}
```

### Manual Compact Tool Response
**Location**: `src/core/prompts/commands.ts`

```typescript
export const condenseToolResponse = () =>
  `<explicit_instructions type="condense">
The user has explicitly asked you to create a detailed summary of the conversation so far, which will be used to compact the current context window while retaining key information.

The condense tool is defined below:

Description:
Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions. This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing with the conversation and supporting any continuing tasks.

Parameters:
- Context: (required) The context to continue the conversation with. If applicable based on the current task, this should include:
  1. Previous Conversation: High level details about what was discussed throughout the entire conversation
  2. Current Work: Describe in detail what was being worked on prior to this request
  3. Key Technical Concepts: List all important technical concepts, technologies, coding conventions, and frameworks discussed
  4. Relevant Files and Code: Enumerate specific files and code sections examined, modified, or created
  5. Problem Solving: Document problems solved thus far and any ongoing troubleshooting efforts
  6. Pending Tasks and Next Steps: Outline all pending tasks and next steps with code snippets and direct quotes from the conversation

Usage:
<condense>
<context>Your detailed summary</context>
</condense>
</explicit_instructions>`
```

### Automatic Context Management
**Location**: `src/core/context/context-management/ContextManager.ts`

#### Context Window Detection
```typescript
shouldCompactContextWindow(clineMessages: ClineMessage[], api: ApiHandler, previousApiReqIndex: number): boolean {
  if (previousApiReqIndex >= 0) {
    const previousRequest = clineMessages[previousApiReqIndex]
    if (previousRequest && previousRequest.text) {
      const { tokensIn, tokensOut, cacheWrites, cacheReads }: ClineApiReqInfo = 
        JSON.parse(previousRequest.text)
      const totalTokens = (tokensIn || 0) + (tokensOut || 0) + (cacheWrites || 0) + (cacheReads || 0)

      const { maxAllowedSize } = getContextWindowInfo(api)
      return totalTokens >= maxAllowedSize
    }
  }
  return false
}
```

#### Context Telemetry Data Collection
```typescript
getContextTelemetryData(
  clineMessages: ClineMessage[],
  api: ApiHandler,
  triggerIndex?: number,
): {
  tokensUsed: number
  maxContextWindow: number
} | null {
  // Find second-to-last API request (the one that caused summarization)
  const apiReqIndices = clineMessages
    .map((msg, index) => (msg.say === "api_req_started" ? index : -1))
    .filter((index) => index !== -1)

  const targetIndex = apiReqIndices.length >= 2 ? apiReqIndices[apiReqIndices.length - 2] : -1
  
  if (targetIndex >= 0) {
    const targetRequest = clineMessages[targetIndex]
    if (targetRequest && targetRequest.text) {
      const { tokensIn, tokensOut, cacheWrites, cacheReads }: ClineApiReqInfo = 
        JSON.parse(targetRequest.text)
      const tokensUsed = (tokensIn || 0) + (tokensOut || 0) + (cacheWrites || 0) + (cacheReads || 0)
      const { contextWindow } = getContextWindowInfo(api)

      return { tokensUsed, maxContextWindow: contextWindow }
    }
  }
  return null
}
```

### Auto-Summarization System
**Location**: `src/core/prompts/contextManagement.ts`

#### Summarize Task Prompt
```typescript
export const summarizeTask = () =>
  `<explicit_instructions type="summarize_task">
The current conversation is rapidly running out of context. Now, your urgent task is to create a comprehensive detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.

This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing development work without losing context. You MUST ONLY respond to this message by using the summarize_task tool call.

Before providing your final summary, wrap your analysis in <thinking> tags to organize your thoughts and ensure you've covered all necessary points.

Your summary should include the following sections:
1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail
2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed
3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created
4. Problem Solving: Document problems solved and any ongoing troubleshooting efforts
5. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on
6. Current Work: Describe in detail precisely what was being worked on immediately before this summary request
7. Optional Next Step: List the next step related to the most recent work with direct quotes from the conversation

Usage:
<summarize_task>
<context>Your detailed summary</context>
</summarize_task>
</explicit_instructions>`
```

#### Continuation Prompt System
```typescript
export const continuationPrompt = (summaryText: string) => `
This session is being continued from a previous conversation that ran out of context. The conversation is summarized below:
${summaryText}.

Please continue the conversation from where we left it off without asking the user any further questions. Continue with the last task that you were asked to work on. Pay special attention to the most recent user message when responding rather than the initial task message, if applicable.

If the most recent user's message starts with "/newtask", "/smol", "/compact", "/newrule", or "/reportbug", you should indicate to the user that they will need to run this command again.
`
```

### Tool Execution Integration
**Location**: `src/core/task/ToolExecutor.ts`

```typescript
case "summarize_task": {
  if (block.params.context) {
    // Process summarization request
    const response = await this.handleSummarizeTask(block.params.context)
    this.pushToolResult(response, block)
  } else {
    this.pushToolResult(
      await this.sayAndCreateMissingParamError("summarize_task", "context"), 
      block
    )
  }
  break
}
```

## Context Optimization Features

### File Read Deduplication
The ContextManager includes sophisticated file read optimization that removes duplicate file content from the context window:

```typescript
private findAndPotentiallySaveFileReadContextHistoryUpdates(
  apiMessages: Anthropic.Messages.MessageParam[],
  startFromIndex: number,
  timestamp: number,
): [boolean, Set<number>] {
  const [fileReadIndices, messageFilePaths] = this.getPossibleDuplicateFileReads(apiMessages, startFromIndex)
  return this.applyFileReadContextHistoryUpdates(fileReadIndices, messageFilePaths, apiMessages, timestamp)
}
```

#### File Mention Handling
```typescript
private handlePotentialFileMentionCalls(
  i: number,
  secondBlockText: string,
  fileReadIndices: Map<string, [number, number, string, string][]>,
  thisExistingFileReads: string[],
): [boolean, string[]] {
  const pattern = new RegExp(`<file_content path="([^"]*)">([\\s\\S]*?)</file_content>`, "g")

  let foundMatch = false
  const filePaths: string[] = []

  let match
  while ((match = pattern.exec(secondBlockText)) !== null) {
    const filePath = match[1]
    const entireMatch = match[0]
    
    // Create replacement text with duplicate notice
    const replacementText = `<file_content path="${filePath}">${formatResponse.duplicateFileReadNotice()}</file_content>`
    
    const indices = fileReadIndices.get(filePath) || []
    indices.push([i, EditType.FILE_MENTION, entireMatch, replacementText])
    fileReadIndices.set(filePath, indices)
  }

  return [foundMatch, filePaths]
}
```

### Context Message Management
```typescript
private getAndAlterTruncatedMessages(
  messages: Anthropic.Messages.MessageParam[],
  deletedRange: [number, number] | undefined,
): Anthropic.Messages.MessageParam[] {
  if (messages.length <= 1) {
    return messages
  }

  const updatedMessages = this.applyContextHistoryUpdates(
    messages, 
    deletedRange ? deletedRange[1] + 1 : 2
  )

  return updatedMessages
}
```

#### Context History Updates Application
```typescript
private applyContextHistoryUpdates(
  messages: Anthropic.Messages.MessageParam[],
  startFromIndex: number,
): Anthropic.Messages.MessageParam[] {
  const firstChunk = messages.slice(0, 2) // First user-assistant pair
  const secondChunk = messages.slice(startFromIndex) // Remaining messages
  const messagesToUpdate = [...firstChunk, ...secondChunk]

  for (let arrayIndex = 0; arrayIndex < messagesToUpdate.length; arrayIndex++) {
    const messageIndex = originalIndices[arrayIndex]
    const innerTuple = this.contextHistoryUpdates.get(messageIndex)
    
    if (innerTuple) {
      messagesToUpdate[arrayIndex] = cloneDeep(messagesToUpdate[arrayIndex])
      
      // Apply latest changes to message content
      const innerMap = innerTuple[1]
      for (const [blockIndex, changes] of innerMap) {
        const latestChange = changes[changes.length - 1]
        
        if (latestChange[1] === "text") {
          const message = messagesToUpdate[arrayIndex]
          if (Array.isArray(message.content)) {
            const block = message.content[blockIndex]
            if (block && block.type === "text") {
              block.text = latestChange[2][0]
            }
          }
        }
      }
    }
  }

  return messagesToUpdate
}
```

## UI Integration

### Chat Message Handling
**Location**: `webview-ui/src/components/chat/chat-view/hooks/useMessageHandlers.ts`

```typescript
case "condense":
  await SlashServiceClient.condense(
    StringRequest.create({ value: lastMessage?.text })
  ).catch((err) => console.error("Failed to condense:", err))
  break
```

### Response Processing
**Location**: `src/core/prompts/responses.ts`

```typescript
condense: () =>
  `The user has accepted the condensed conversation summary you generated. This summary covers important details of the historical conversation with the user which has been truncated.
<explicit_instructions type="condense_response">
It's crucial that you respond by ONLY asking the user what you should work on next. You should NOT take any initiative or make any assumptions about continuing with work. For example you should NOT suggest file changes or attempt to read any files.
When asking the user what you should work on next, you can reference information in the summary which was just generated. However, you should NOT reference information outside of what's contained in the summary for this response. Keep this response CONCISE.
</explicit_instructions>`
```

## Telemetry Integration

### Auto-Compact Tracking
**Location**: `src/services/posthog/telemetry/TelemetryService.ts`

```typescript
// Tracks when the context window is auto-condensed with the summarize_task tool call
AUTO_COMPACT: "task.summarize_task",
```

## Message Type System

### Protocol Buffer Integration
**Location**: `src/shared/proto-conversions/cline-message.ts`

```typescript
const clineAskToProto = {
  condense: ClineAsk.CONDENSE,
  summarize_task: ClineAsk.SUMMARIZE_TASK,
}

const protoToClineAsk = {
  [ClineAsk.CONDENSE]: "condense",
  [ClineAsk.SUMMARIZE_TASK]: "summarize_task",
}
```

### Extension Message Types
**Location**: `src/shared/ExtensionMessage.ts`

```typescript
export type ClineAsk = 
  | "condense"
  | "summarize_task"
  | "summarizeTask"  // Legacy support
```

## LangGraph Implementation Specifications

### State Schema
```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class CompactTrigger(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    THRESHOLD = "threshold"

class ContextMetrics(BaseModel):
    tokens_used: int
    max_context_window: int
    utilization_percentage: float
    trigger_threshold: float = 0.85

class ConversationSegment(BaseModel):
    start_index: int
    end_index: int
    content_type: str  # "user_message", "assistant_response", "tool_call"
    importance_score: float
    technical_content: bool
    file_references: List[str] = []

class CompactState(BaseModel):
    trigger_type: CompactTrigger
    context_metrics: ContextMetrics
    conversation_segments: List[ConversationSegment] = []
    summary_generated: bool = False
    summary_content: Optional[str] = None
    files_referenced: List[str] = []
    technical_concepts: List[str] = []
    pending_tasks: List[str] = []
    current_work: Optional[str] = None
    next_steps: List[str] = []
    continuation_ready: bool = False
```

### Context Analysis Engine
```python
class ContextAnalyzer:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        
    def analyze_context_window(self, messages: List[Dict], api_config: Dict) -> ContextMetrics:
        """Analyze current context window utilization"""
        total_tokens = self.count_tokens(messages)
        max_tokens = api_config.get("max_context_window", 200000)
        utilization = total_tokens / max_tokens
        
        return ContextMetrics(
            tokens_used=total_tokens,
            max_context_window=max_tokens,
            utilization_percentage=utilization,
            trigger_threshold=self.threshold
        )
    
    def should_trigger_compact(self, metrics: ContextMetrics) -> bool:
        """Determine if context should be compacted"""
        return metrics.utilization_percentage >= metrics.trigger_threshold
    
    def segment_conversation(self, messages: List[Dict]) -> List[ConversationSegment]:
        """Break conversation into analyzable segments"""
        segments = []
        
        for i, message in enumerate(messages):
            segment = ConversationSegment(
                start_index=i,
                end_index=i,
                content_type=message.get("role", "unknown"),
                importance_score=self.calculate_importance(message),
                technical_content=self.has_technical_content(message),
                file_references=self.extract_file_references(message)
            )
            segments.append(segment)
            
        return segments
    
    def calculate_importance(self, message: Dict) -> float:
        """Score message importance for summarization"""
        content = message.get("content", "")
        
        # Higher scores for technical content
        score = 0.5
        
        if self.has_code_blocks(content):
            score += 0.3
        if self.has_file_operations(content):
            score += 0.2
        if self.has_error_messages(content):
            score += 0.3
        if self.is_task_definition(content):
            score += 0.4
            
        return min(score, 1.0)
```

### Summary Generation Framework
```python
class SummaryGenerator:
    def __init__(self, template_path: str):
        self.template = self.load_template(template_path)
        self.section_generators = {
            "primary_request": self.generate_primary_request,
            "technical_concepts": self.generate_technical_concepts,
            "files_and_code": self.generate_files_and_code,
            "problem_solving": self.generate_problem_solving,
            "pending_tasks": self.generate_pending_tasks,
            "current_work": self.generate_current_work,
            "next_steps": self.generate_next_steps
        }
    
    def generate_summary(self, 
                        conversation_segments: List[ConversationSegment],
                        context: Dict[str, Any]) -> str:
        """Generate comprehensive conversation summary"""
        
        sections = {}
        for section_name, generator in self.section_generators.items():
            sections[section_name] = generator(conversation_segments, context)
        
        return self.template.render(sections=sections, **context)
    
    def generate_primary_request(self, segments: List[ConversationSegment], context: Dict) -> str:
        """Extract and summarize user's primary requests"""
        user_messages = [s for s in segments if s.content_type == "user"]
        
        primary_requests = []
        for segment in user_messages:
            if segment.importance_score > 0.7:
                content = self.extract_content(segment)
                if self.is_primary_request(content):
                    primary_requests.append(content)
        
        return self.format_requests(primary_requests)
    
    def generate_technical_concepts(self, segments: List[ConversationSegment], context: Dict) -> List[str]:
        """Extract technical concepts, frameworks, and technologies"""
        concepts = set()
        
        for segment in segments:
            if segment.technical_content:
                content = self.extract_content(segment)
                concepts.update(self.extract_technologies(content))
                concepts.update(self.extract_frameworks(content))
                concepts.update(self.extract_patterns(content))
        
        return sorted(list(concepts))
    
    def generate_files_and_code(self, segments: List[ConversationSegment], context: Dict) -> Dict[str, Any]:
        """Document files examined, modified, or created"""
        files_info = {}
        
        for segment in segments:
            for file_path in segment.file_references:
                if file_path not in files_info:
                    files_info[file_path] = {
                        "path": file_path,
                        "operations": [],
                        "importance": "File operations tracked",
                        "code_snippets": []
                    }
                
                operation = self.determine_file_operation(segment)
                if operation:
                    files_info[file_path]["operations"].append(operation)
                
                code_snippets = self.extract_code_snippets(segment)
                files_info[file_path]["code_snippets"].extend(code_snippets)
        
        return files_info
```

### Node Implementations
```python
def compact_trigger_node(state: AgentState) -> AgentState:
    """Detect if context compaction should be triggered"""
    analyzer = ContextAnalyzer()
    
    # Analyze current context
    metrics = analyzer.analyze_context_window(
        state.messages, 
        state.api_config
    )
    
    # Determine trigger type
    if state.user_requested_compact:
        trigger_type = CompactTrigger.MANUAL
    elif analyzer.should_trigger_compact(metrics):
        trigger_type = CompactTrigger.AUTOMATIC
    else:
        return state  # No compaction needed
    
    # Initialize compact state
    state.compact_state = CompactState(
        trigger_type=trigger_type,
        context_metrics=metrics,
        conversation_segments=analyzer.segment_conversation(state.messages)
    )
    
    return state

def summary_generation_node(state: AgentState) -> AgentState:
    """Generate conversation summary"""
    if not state.compact_state:
        return state
    
    generator = SummaryGenerator("templates/summary_template.md")
    
    # Generate comprehensive summary
    summary = generator.generate_summary(
        state.compact_state.conversation_segments,
        {
            "user_id": state.user_id,
            "session_id": state.session_id,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Update state
    state.compact_state.summary_generated = True
    state.compact_state.summary_content = summary
    state.compact_state.files_referenced = generator.extract_all_files(
        state.compact_state.conversation_segments
    )
    state.compact_state.technical_concepts = generator.generate_technical_concepts(
        state.compact_state.conversation_segments, {}
    )
    
    return state

def context_replacement_node(state: AgentState) -> AgentState:
    """Replace conversation history with summary"""
    if not state.compact_state or not state.compact_state.summary_generated:
        return state
    
    # Create continuation prompt
    continuation_prompt = f"""
    This session is being continued from a previous conversation that ran out of context. 
    The conversation is summarized below:
    
    {state.compact_state.summary_content}
    
    Please continue the conversation from where we left it off without asking the user 
    any further questions. Continue with the last task that you were asked to work on.
    """
    
    # Replace message history
    state.messages = [
        {"role": "system", "content": continuation_prompt},
        state.messages[-1]  # Keep the latest user message
    ]
    
    # Update context metrics
    analyzer = ContextAnalyzer()
    state.compact_state.context_metrics = analyzer.analyze_context_window(
        state.messages, 
        state.api_config
    )
    
    state.compact_state.continuation_ready = True
    
    return state
```

### Context Window Router
```python
def context_window_router(state: AgentState) -> str:
    """Route based on context window status"""
    if not state.compact_state:
        return "normal_processing"
    
    if not state.compact_state.summary_generated:
        return "generate_summary"
    elif not state.compact_state.continuation_ready:
        return "replace_context"
    else:
        return "continue_conversation"

def compact_complete_router(state: AgentState) -> str:
    """Determine if compaction process is complete"""
    if state.compact_state and state.compact_state.continuation_ready:
        return "task_continuation"
    else:
        return "compact_processing"
```

### File Deduplication System
```python
class FileDeduplicationEngine:
    def __init__(self):
        self.file_read_tracker = {}
        self.deduplication_patterns = [
            r'<file_content path="([^"]*)">([\s\S]*?)</file_content>',
            r'\[read_file for \'([^\']+)\'\] Result:',
            r'\[write_to_file for \'([^\']+)\'\] Result:',
            r'\[replace_in_file for \'([^\']+)\'\] Result:'
        ]
    
    def identify_duplicate_reads(self, messages: List[Dict]) -> Dict[str, List[int]]:
        """Identify duplicate file read operations"""
        file_occurrences = {}
        
        for i, message in enumerate(messages):
            content = message.get("content", "")
            
            for pattern in self.deduplication_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    file_path = match.group(1)
                    
                    if file_path not in file_occurrences:
                        file_occurrences[file_path] = []
                    file_occurrences[file_path].append(i)
        
        # Return only files with multiple occurrences
        return {path: indices for path, indices in file_occurrences.items() 
                if len(indices) > 1}
    
    def apply_deduplication(self, messages: List[Dict]) -> List[Dict]:
        """Replace duplicate file reads with notices"""
        duplicates = self.identify_duplicate_reads(messages)
        processed_messages = messages.copy()
        
        for file_path, indices in duplicates.items():
            # Keep the last occurrence, replace earlier ones
            for i in indices[:-1]:
                content = processed_messages[i].get("content", "")
                
                # Replace file content with deduplication notice
                for pattern in self.deduplication_patterns:
                    if re.search(pattern, content):
                        replacement = f'<file_content path="{file_path}">**[Content previously shown - See latest occurrence]**</file_content>'
                        processed_messages[i]["content"] = re.sub(
                            pattern, replacement, content, count=1
                        )
                        break
        
        return processed_messages
```

## Implementation Recommendations

### 1. Modular Architecture
- Separate context analysis, summary generation, and content replacement
- Use dependency injection for different summarization strategies
- Implement clean interfaces for different context window providers

### 2. Intelligent Context Preservation
- Preserve first user-assistant message pair as anchor
- Maintain technical context and code patterns
- Keep task-relevant information with higher priority

### 3. Performance Optimization
- Cache context analysis results
- Use streaming for large context processing
- Implement efficient token counting

### 4. Error Recovery
- Graceful degradation when summarization fails
- Fallback to rule-based truncation
- User notification for context issues

### 5. User Experience
- Clear indication when context is being compacted
- Progress feedback during summarization
- Easy access to full conversation history

The Compact feature represents a sophisticated approach to context window management that enables continuous long-form conversations while preserving essential technical context and task continuity.