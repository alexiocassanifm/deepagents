"""
LLM-based Context Compression System - Intelligent Semantic Compression

Questo modulo implementa compressione semantica intelligente del contesto usando LLM,
integrandosi perfettamente con il sistema di context management esistente.

Funzionalità principali:
1. Compressione semantica vera tramite LLM calls
2. Prompts ottimizzati per diversi tipi di contenuto
3. Preservazione intelligente di informazioni critiche
4. Fallback graceful al sistema di pulizia esistente
5. Gestione rate limiting e performance
6. Integrazione con DeepAgentState e context_manager
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage

# Import existing context management
from .context_manager import ContextManager, ContextMetrics, CleaningResult
from .compact_integration import CompactSummary, CompactTrigger

# Import configurazione centralizzata
try:
    from ..config.config_loader import get_trigger_config, get_full_config
    CONFIG_LOADER_AVAILABLE = True
except ImportError:
    CONFIG_LOADER_AVAILABLE = False


class CompressionType(str, Enum):
    """Tipi di compressione disponibili."""
    GENERAL = "general"
    MCP_HEAVY = "mcp_heavy" 
    CODE_FOCUSED = "code_focused"
    PLANNING_FOCUSED = "planning_focused"
    TECHNICAL_DEEP = "technical_deep"


class CompressionStrategy(str, Enum):
    """Strategie di compressione."""
    AGGRESSIVE = "aggressive"  # 70-80% reduction
    BALANCED = "balanced"      # 50-60% reduction  
    CONSERVATIVE = "conservative"  # 30-40% reduction
    ADAPTIVE = "adaptive"      # Based on content analysis


def _load_compression_config() -> Dict[str, Any]:
    """Carica configurazione compressione da YAML."""
    if CONFIG_LOADER_AVAILABLE:
        try:
            trigger_config = get_trigger_config()
            full_config = get_full_config()
            
            return {
                "target_reduction_percentage": 60.0,  # From context_config or default
                "max_output_tokens": 2500,  # From context_config or default
                "preserve_last_n_messages": trigger_config.preserve_last_n_messages,
                "compression_timeout": trigger_config.compression_timeout,
                "enable_fallback": trigger_config.enable_fallback,
                "preserve_patterns": [
                    r'project_id:\s*[\w-]+',
                    r'entity_id:\s*[\w-]+', 
                    r'file_path:\s*[\w/.]+',
                    r'TODO:\s*.+',
                    r'ERROR:\s*.+'
                ]
            }
        except Exception as e:
            print(f"⚠️ Failed to load compression config: {e}")
    
    # Fallback configuration
    return {
        "target_reduction_percentage": 60.0,
        "max_output_tokens": 2000,
        "preserve_last_n_messages": 3,
        "compression_timeout": 30.0,
        "enable_fallback": True,
        "preserve_patterns": [
            r'project_id:\s*[\w-]+',
            r'entity_id:\s*[\w-]+', 
            r'file_path:\s*[\w/.]+',
            r'TODO:\s*.+',
            r'ERROR:\s*.+'
        ]
    }


@dataclass
class CompressionConfig:
    """Configurazione per compressione LLM."""
    strategy: CompressionStrategy = CompressionStrategy.BALANCED
    target_reduction_percentage: float = 60.0
    max_output_tokens: int = 2000
    preserve_last_n_messages: int = 3
    preserve_patterns: List[str] = field(default_factory=lambda: [
        r'project_id:\s*[\w-]+',
        r'entity_id:\s*[\w-]+', 
        r'file_path:\s*[\w/.]+',
        r'TODO:\s*.+',
        r'ERROR:\s*.+'
    ])
    compression_timeout: float = 30.0
    enable_fallback: bool = True
    
    @classmethod
    def from_yaml(cls) -> 'CompressionConfig':
        """Crea configurazione caricando da YAML."""
        config_data = _load_compression_config()
        return cls(
            target_reduction_percentage=config_data["target_reduction_percentage"],
            max_output_tokens=config_data["max_output_tokens"],
            preserve_last_n_messages=config_data["preserve_last_n_messages"],
            preserve_patterns=config_data["preserve_patterns"],
            compression_timeout=config_data["compression_timeout"],
            enable_fallback=config_data["enable_fallback"]
        )


@dataclass 
class LLMCompressionResult:
    """Risultato di compressione LLM."""
    original_messages: List[Dict[str, Any]]
    compressed_content: str
    compression_type: CompressionType
    actual_reduction_percentage: float
    tokens_before: int
    tokens_after: int
    processing_time: float
    success: bool
    fallback_used: bool
    preserved_elements: List[str]
    compression_metadata: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LLMCompressor:
    """
    Compressore semantico basato su LLM per riduzione intelligente del contesto.
    
    Questo sistema:
    1. Analizza il tipo di contenuto per scegliere strategia ottimale
    2. Usa prompts specializzati per ogni tipo di compressione
    3. Preserva informazioni critiche durante la compressione
    4. Gestisce fallback al sistema di pulizia esistente
    5. Monitora performance e rate limiting
    """
    
    def __init__(self, 
                 model: LanguageModelLike,
                 config: CompressionConfig = None,
                 context_manager: ContextManager = None):
        self.model = model
        self.config = config or CompressionConfig()
        self.context_manager = context_manager
        self.compression_history: List[LLMCompressionResult] = []
        self.stats = {
            "total_compressions": 0,
            "successful_compressions": 0,
            "fallback_compressions": 0,
            "average_reduction": 0.0,
            "total_processing_time": 0.0
        }
        
        # Load compression prompts
        self.prompts = self._load_compression_prompts()
    
    def _load_compression_prompts(self) -> Dict[CompressionType, str]:
        """Carica i prompts di compressione ottimizzati."""
        return {
            CompressionType.GENERAL: """
You are a context compression specialist. Compress this conversation while preserving essential information for seamless continuation.

CRITICAL TO PRESERVE:
- Main user goals and requests  
- Technical decisions and architecture choices
- Current progress and completed tasks
- File/code references and important data
- Pending actions and next steps
- Project IDs, entity IDs, and important identifiers

SAFE TO COMPRESS/REMOVE:
- Verbose tool outputs and MCP noise
- Repeated information and redundant details  
- Debug information and intermediate steps
- Verbose explanations already understood
- Tool exploration that didn't lead to decisions

COMPRESSION TARGET: {target_percentage}% reduction
MAX OUTPUT: {max_tokens} tokens

INPUT CONVERSATION:
{conversation}

Provide a comprehensive but concise summary that maintains all context needed for continuation:

## 🎯 Primary Objectives
[Main user goals and requests]

## 🔧 Technical Context  
[Architecture, technologies, key decisions made]

## 📁 Important References
[Files, code, data, IDs that matter for continuation]

## ✅ Progress Summary
[What's been completed, current status, todos]

## 📋 Next Actions
[Pending tasks, immediate next steps]

## 🧠 Essential Context
[Any other critical context for seamless continuation]
""",

            CompressionType.MCP_HEAVY: """
This conversation contains heavy MCP tool usage with lots of noise. Compress intelligently:

COMPRESSION STRATEGY:
1. **Summarize tool results** instead of including full verbose output
2. **Extract key findings** from each significant tool call
3. **Preserve essential IDs** (project_id, entity_id, repository_id, etc.)
4. **Keep final decisions** and actions taken based on tool results
5. **Remove exploration noise** that didn't lead to useful outcomes

TARGET: {target_percentage}% reduction through MCP noise elimination

PRESERVE EXACTLY:
- Project and entity identifiers
- Final decisions made from tool results
- File paths and code references discovered
- User requests and goals
- Action items and next steps

INPUT WITH MCP NOISE:
{conversation}

Provide compressed summary focusing on **outcomes** rather than **process**:
""",

            CompressionType.CODE_FOCUSED: """
Compress this code-heavy conversation while preserving technical accuracy:

PRESERVE EXACTLY:
- File paths and names mentioned
- Code snippets that were analyzed or modified  
- Architecture decisions and technical approaches
- Implementation strategies chosen
- Error messages and their solutions
- Function/class names and technical entities

COMPRESS HEAVILY:
- Code search and exploration steps
- Verbose tool outputs from code analysis
- Repetitive technical explanations
- Debug traces that were resolved

TARGET: {target_percentage}% reduction
MAX OUTPUT: {max_tokens} tokens

{conversation}

Focus on **technical decisions made** and **code elements identified**:
""",

            CompressionType.PLANNING_FOCUSED: """
Compress this planning-heavy conversation preserving project structure:

PRESERVE COMPLETELY:
- Project requirements and specifications
- Planning decisions and methodology chosen
- Task breakdowns and todos created
- File structure and organization decisions
- Implementation strategies approved
- Human approval points and feedback

COMPRESS:
- Exploration and discovery phases
- Verbose requirement gathering process
- Repetitive planning discussions

TARGET: {target_percentage}% reduction

{conversation}

Maintain planning context and decisions:
""",

            CompressionType.TECHNICAL_DEEP: """
This is a deep technical conversation. Compress while maintaining technical depth:

PRESERVE CRITICAL:
- Technical architecture decisions
- Code patterns and implementation details
- Dependencies and integration points
- Performance considerations
- Error handling approaches
- Testing strategies

SAFE TO COMPRESS:
- Verbose technical exploration
- Repetitive technical explanations
- Debug sessions that were resolved

{conversation}

Maintain technical accuracy and implementation context:
"""
        }
    
    async def compress_conversation(self, 
                                  messages: List[Dict[str, Any]], 
                                  compression_type: CompressionType = None,
                                  context: Dict[str, Any] = None) -> LLMCompressionResult:
        """
        Comprime una conversazione usando LLM semantico.
        
        Args:
            messages: Messaggi da comprimere
            compression_type: Tipo di compressione (auto-detect se None)
            context: Contesto aggiuntivo per la compressione
        
        Returns:
            Risultato della compressione LLM
        """
        start_time = time.time()
        self.stats["total_compressions"] += 1
        
        try:
            # 1. Auto-detect compression type if not specified
            if compression_type is None:
                compression_type = self._detect_compression_type(messages)
            
            # 2. Analyze content and tokens before compression
            tokens_before = self._count_tokens(messages)
            
            # 3. Prepare compression prompt
            conversation_text = self._format_conversation(messages)
            prompt = self._build_compression_prompt(compression_type, conversation_text)
            
            # 4. Execute LLM compression with timeout
            compressed_content = await asyncio.wait_for(
                self._execute_llm_compression(prompt),
                timeout=self.config.compression_timeout
            )
            
            # 5. Analyze compression results
            tokens_after = self._count_tokens([{"content": compressed_content}])
            actual_reduction = ((tokens_before - tokens_after) / tokens_before * 100) if tokens_before > 0 else 0
            
            # 6. Extract preserved elements
            preserved_elements = self._extract_preserved_elements(compressed_content)
            
            # 7. Create success result
            result = LLMCompressionResult(
                original_messages=messages,
                compressed_content=compressed_content,
                compression_type=compression_type,
                actual_reduction_percentage=round(actual_reduction, 2),
                tokens_before=tokens_before,
                tokens_after=tokens_after,
                processing_time=time.time() - start_time,
                success=True,
                fallback_used=False,
                preserved_elements=preserved_elements,
                compression_metadata={
                    "target_reduction": self.config.target_reduction_percentage,
                    "strategy": self.config.strategy.value,
                    "message_count": len(messages)
                }
            )
            
            # 8. Update stats and history
            self.stats["successful_compressions"] += 1
            self.stats["average_reduction"] = (
                (self.stats["average_reduction"] * (self.stats["successful_compressions"] - 1) + actual_reduction) / 
                self.stats["successful_compressions"]
            )
            self.compression_history.append(result)
            
            return result
            
        except Exception as e:
            # Fallback to existing system if LLM compression fails
            if self.config.enable_fallback:
                return await self._fallback_compression(messages, compression_type, start_time, e)
            else:
                # Return failed result
                return LLMCompressionResult(
                    original_messages=messages,
                    compressed_content="",
                    compression_type=compression_type or CompressionType.GENERAL,
                    actual_reduction_percentage=0.0,
                    tokens_before=self._count_tokens(messages),
                    tokens_after=0,
                    processing_time=time.time() - start_time,
                    success=False,
                    fallback_used=False,
                    preserved_elements=[],
                    compression_metadata={"error": str(e)}
                )
    
    def _detect_compression_type(self, messages: List[Dict[str, Any]]) -> CompressionType:
        """Auto-rileva il tipo di compressione ottimale."""
        conversation_text = json.dumps(messages, default=str).lower()
        
        # Analizza contenuto per determinare tipo
        mcp_indicators = ["general_list_", "code_find_", "studio_", "project_id", "entity_id"]
        code_indicators = ["function", "class", "import", "def ", "async def", "file_path"]
        planning_indicators = ["todo", "task", "plan", "requirement", "user story", "implementation"]
        
        mcp_score = sum(1 for indicator in mcp_indicators if indicator in conversation_text)
        code_score = sum(1 for indicator in code_indicators if indicator in conversation_text)
        planning_score = sum(1 for indicator in planning_indicators if indicator in conversation_text)
        
        # Determina tipo basandosi su punteggi
        if mcp_score >= 5:
            return CompressionType.MCP_HEAVY
        elif code_score >= 3:
            return CompressionType.CODE_FOCUSED
        elif planning_score >= 3:
            return CompressionType.PLANNING_FOCUSED
        else:
            return CompressionType.GENERAL
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Formatta la conversazione per il prompt di compressione."""
        formatted_messages = []
        
        for i, message in enumerate(messages):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            
            # Truncate very long tool outputs for compression
            if len(str(content)) > 2000 and self._is_tool_message(message):
                content = str(content)[:1500] + "\n... [truncated for compression] ..."
            
            formatted_messages.append(f"[{role.upper()}]: {content}")
        
        return "\n\n".join(formatted_messages)
    
    def _is_tool_message(self, message: Dict[str, Any]) -> bool:
        """Determina se un messaggio è output di un tool."""
        content = str(message.get("content", "")).lower()
        return any(indicator in content for indicator in [
            "project_id", "entity_id", "repository_id", "tool_call", "function_call"
        ])
    
    def _build_compression_prompt(self, compression_type: CompressionType, conversation: str) -> str:
        """Costruisce il prompt di compressione per il tipo specificato."""
        template = self.prompts[compression_type]
        
        return template.format(
            conversation=conversation,
            target_percentage=self.config.target_reduction_percentage,
            max_tokens=self.config.max_output_tokens
        )
    
    async def _execute_llm_compression(self, prompt: str) -> str:
        """Esegue la compressione tramite LLM."""
        messages = [
            SystemMessage(content="You are an expert at compressing conversations while preserving essential context."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.model.ainvoke(messages)
        return response.content
    
    def _count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Conta i token nei messaggi."""
        if self.context_manager:
            # Usa il tokenizer del context manager se disponibile
            text = json.dumps(messages, default=str)
            return self.context_manager.count_tokens(text)
        else:
            # Fallback: stima approssimativa
            text = json.dumps(messages, default=str)
            return len(text) // 4
    
    def _extract_preserved_elements(self, compressed_content: str) -> List[str]:
        """Estrae elementi preservati dal contenuto compresso."""
        import re
        
        preserved = []
        
        # Estrae pattern preservati
        for pattern in self.config.preserve_patterns:
            matches = re.findall(pattern, compressed_content)
            preserved.extend(matches)
        
        return preserved
    
    async def _fallback_compression(self, 
                                  messages: List[Dict[str, Any]], 
                                  compression_type: CompressionType,
                                  start_time: float,
                                  error: Exception) -> LLMCompressionResult:
        """Fallback al sistema di pulizia esistente se LLM compression fallisce."""
        self.stats["fallback_compressions"] += 1
        
        try:
            if self.context_manager:
                # Usa il sistema di pulizia esistente
                cleaned_messages, cleaning_info = self.context_manager.process_context_cleaning(messages)
                
                # Crea summary template-based come fallback
                fallback_content = self._create_fallback_summary(cleaned_messages)
                
                tokens_before = self._count_tokens(messages)
                tokens_after = self._count_tokens([{"content": fallback_content}])
                actual_reduction = ((tokens_before - tokens_after) / tokens_before * 100) if tokens_before > 0 else 0
                
                return LLMCompressionResult(
                    original_messages=messages,
                    compressed_content=fallback_content,
                    compression_type=compression_type,
                    actual_reduction_percentage=round(actual_reduction, 2),
                    tokens_before=tokens_before,
                    tokens_after=tokens_after,
                    processing_time=time.time() - start_time,
                    success=True,
                    fallback_used=True,
                    preserved_elements=[],
                    compression_metadata={
                        "fallback_reason": str(error),
                        "used_context_manager": True
                    }
                )
            else:
                # Fallback minimale senza context manager
                fallback_content = self._create_minimal_fallback(messages)
                
                return LLMCompressionResult(
                    original_messages=messages,
                    compressed_content=fallback_content,
                    compression_type=compression_type,
                    actual_reduction_percentage=30.0,  # Stima
                    tokens_before=self._count_tokens(messages),
                    tokens_after=self._count_tokens([{"content": fallback_content}]),
                    processing_time=time.time() - start_time,
                    success=True,
                    fallback_used=True,
                    preserved_elements=[],
                    compression_metadata={
                        "fallback_reason": str(error),
                        "used_minimal_fallback": True
                    }
                )
                
        except Exception as fallback_error:
            # Se anche il fallback fallisce, restituisce messaggio originale
            return LLMCompressionResult(
                original_messages=messages,
                compressed_content=json.dumps(messages[-3:], default=str),  # Ultimi 3 messaggi
                compression_type=compression_type,
                actual_reduction_percentage=0.0,
                tokens_before=self._count_tokens(messages),
                tokens_after=self._count_tokens(messages[-3:]),
                processing_time=time.time() - start_time,
                success=False,
                fallback_used=True,
                preserved_elements=[],
                compression_metadata={
                    "original_error": str(error),
                    "fallback_error": str(fallback_error)
                }
            )
    
    def _create_fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Crea un summary fallback basato su template."""
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        return f"""## Conversation Summary (Fallback)

### User Requests:
{'; '.join([str(m.get('content', ''))[:100] for m in user_messages[-3:]])}

### Key Actions Taken:
{'; '.join([str(m.get('content', ''))[:100] for m in assistant_messages[-3:]])}

### Context: 
This session was compressed using fallback method due to LLM compression failure.
Last {len(messages)} messages processed with {self.config.target_reduction_percentage}% target reduction.
"""
    
    def _create_minimal_fallback(self, messages: List[Dict[str, Any]]) -> str:
        """Crea fallback minimale preservando solo ultimi messaggi."""
        recent_messages = messages[-self.config.preserve_last_n_messages:]
        
        return f"""## Minimal Compression Fallback

Last {len(recent_messages)} messages preserved:

{json.dumps(recent_messages, indent=2, default=str)}

Compression applied due to context limits. Continue from this point.
"""
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche delle compressioni."""
        return {
            **self.stats,
            "total_processing_time": round(self.stats["total_processing_time"], 2),
            "average_processing_time": (
                round(self.stats["total_processing_time"] / self.stats["total_compressions"], 2) 
                if self.stats["total_compressions"] > 0 else 0
            ),
            "success_rate": (
                round(self.stats["successful_compressions"] / self.stats["total_compressions"] * 100, 2)
                if self.stats["total_compressions"] > 0 else 0
            ),
            "fallback_rate": (
                round(self.stats["fallback_compressions"] / self.stats["total_compressions"] * 100, 2)
                if self.stats["total_compressions"] > 0 else 0
            ),
            "compression_history_count": len(self.compression_history)
        }
    
    def get_recent_compressions(self, limit: int = 5) -> List[LLMCompressionResult]:
        """Restituisce le compressioni recenti."""
        return self.compression_history[-limit:]
