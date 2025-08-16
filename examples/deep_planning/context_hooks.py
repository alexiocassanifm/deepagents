"""
Context Hooks System - Hook automatici per integrazione LLM compression nel grafo LangGraph

Questo modulo implementa un sistema di hook che si integra automaticamente con LangGraph
per eseguire compressione LLM intelligente ad ogni step senza modificare il codice esistente.

Funzionalità principali:
1. Hook pre/post step per intercettazione automatica
2. Integrazione trasparente con DeepAgentState
3. Trigger intelligenti basati su metriche del contesto
4. Middleware pattern per estensibilità
5. Preservazione completa della compatibilità esistente
"""

import asyncio
import json
import time
import yaml
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path

from langchain_core.language_models import LanguageModelLike
from langgraph.types import Command

# Import existing system components
from context_manager import ContextManager, ContextMetrics
from llm_compression import LLMCompressor, CompressionConfig, LLMCompressionResult, CompressionType
from deepagents.state import DeepAgentState


def load_context_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carica configurazione dal file YAML.
    
    Args:
        config_path: Percorso al file di configurazione. Se None, cerca context_config.yaml
                    nella directory corrente.
    
    Returns:
        Dizionario con la configurazione caricata dal YAML.
    """
    if config_path is None:
        # Cerca nella directory corrente
        config_path = Path(__file__).parent / "context_config.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        # Fallback con valori di default se il file non esiste
        return {
            'context_management': {
                'trigger_threshold': 0.80,
                'mcp_noise_threshold': 0.60,
                'force_llm_threshold': 0.90,
                'post_tool_threshold': 0.70,
                'llm_compression_threshold': 0.75
            },
            'performance': {
                'auto_check_interval': 60
            }
        }
    except yaml.YAMLError as e:
        print(f"Errore parsing YAML config: {e}")
        # Usa configurazione di default in caso di errore
        return load_context_config()


class HookType(str, Enum):
    """Tipi di hook disponibili."""
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_MESSAGE = "pre_message"
    POST_MESSAGE = "post_message"
    PRE_SUBAGENT = "pre_subagent"
    POST_SUBAGENT = "post_subagent"


class HookPriority(int, Enum):
    """Priorità di esecuzione hook."""
    HIGHEST = 1
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class HookContext:
    """Contesto passato agli hook durante l'esecuzione."""
    hook_type: HookType
    state: DeepAgentState
    metadata: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    execution_path: List[str] = field(default_factory=list)


class Hook(ABC):
    """Interfaccia base per hook."""
    
    def __init__(self, name: str, priority: HookPriority = HookPriority.NORMAL):
        self.name = name
        self.priority = priority
        self.enabled = True
        self.stats = {
            "executions": 0,
            "total_time": 0.0,
            "errors": 0
        }
    
    @abstractmethod
    async def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """Esegue la logica dell'hook."""
        pass
    
    def can_execute(self, context: HookContext) -> bool:
        """Determina se l'hook può essere eseguito in questo contesto."""
        return self.enabled


class CompressionHook(Hook):
    """Hook specializzato per compressione LLM del contesto."""
    
    def __init__(self, 
                 compressor: LLMCompressor,
                 trigger_config: Dict[str, Any] = None,
                 priority: HookPriority = HookPriority.HIGH,
                 config_path: Optional[str] = None):
        super().__init__("compression_hook", priority)
        self.compressor = compressor
        
        # Carica configurazione dal YAML
        self.config = load_context_config(config_path)
        context_mgmt = self.config.get('context_management', {})
        performance = self.config.get('performance', {})
        
        # Usa configurazione YAML con fallback ai valori di default
        self.trigger_config = trigger_config or {
            "utilization_threshold": context_mgmt.get('trigger_threshold', 0.80),
            "mcp_noise_threshold": context_mgmt.get('mcp_noise_threshold', 0.60),
            "min_messages": 5,  # Non presente nel YAML, mantieni default
            "force_compression_threshold": context_mgmt.get('force_llm_threshold', 0.90),
            "post_tool_threshold": context_mgmt.get('post_tool_threshold', 0.70),
            "llm_compression_threshold": context_mgmt.get('llm_compression_threshold', 0.75)
        }
        self.last_compression_time = 0
        self.compression_cooldown = performance.get('auto_check_interval', 60)  # seconds from YAML
    
    async def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """Esegue compressione se necessaria."""
        start_time = time.time()
        
        try:
            self.stats["executions"] += 1
            
            # 1. Analizza se serve compressione
            should_compress, compression_type, metrics = await self._should_trigger_compression(context.state)
            
            if not should_compress:
                return {"compression_triggered": False, "reason": "no_trigger"}
            
            # 2. Controlla cooldown
            if time.time() - self.last_compression_time < self.compression_cooldown:
                return {"compression_triggered": False, "reason": "cooldown"}
            
            # 3. Estrae messaggi dal state
            messages = self._extract_messages_from_state(context.state)
            if len(messages) < self.trigger_config["min_messages"]:
                return {"compression_triggered": False, "reason": "insufficient_messages"}
            
            # 4. Esegue compressione LLM
            compression_result = await self.compressor.compress_conversation(
                messages, compression_type, {"hook_context": context.metadata}
            )
            
            if compression_result.success:
                # 5. Aggiorna state con contesto compresso
                updated_state = self._apply_compression_to_state(context.state, compression_result)
                self.last_compression_time = time.time()
                
                return {
                    "compression_triggered": True,
                    "compression_result": compression_result,
                    "state_update": updated_state,
                    "metrics": {
                        "reduction_percentage": compression_result.actual_reduction_percentage,
                        "tokens_saved": compression_result.tokens_before - compression_result.tokens_after,
                        "compression_type": compression_result.compression_type.value
                    }
                }
            else:
                return {"compression_triggered": False, "reason": "compression_failed"}
                
        except Exception as e:
            self.stats["errors"] += 1
            return {"compression_triggered": False, "reason": "error", "error": str(e)}
        
        finally:
            self.stats["total_time"] += time.time() - start_time
    
    async def _should_trigger_compression(self, state: DeepAgentState) -> tuple[bool, CompressionType, ContextMetrics]:
        """Determina se deve essere attivata la compressione."""
        
        # Usa metrics esistenti se disponibili
        if hasattr(state, 'context_metrics') and state.get('context_metrics'):
            metrics = state['context_metrics']
        else:
            # Calcola metrics dai messaggi
            messages = self._extract_messages_from_state(state)
            if self.compressor.context_manager:
                metrics = self.compressor.context_manager.analyze_context(messages)
            else:
                # Fallback metrics
                total_tokens = sum(len(json.dumps(m, default=str)) // 4 for m in messages)
                metrics = {
                    "tokens_used": total_tokens,
                    "utilization_percentage": min(total_tokens / 200000 * 100, 100),
                    "mcp_noise_percentage": 0
                }
        
        # Controlli trigger
        utilization = metrics.get("utilization_percentage", 0)
        mcp_noise = metrics.get("mcp_noise_percentage", 0)
        
        # Force compression se utilizzo molto alto
        if utilization >= self.trigger_config["force_compression_threshold"]:
            return True, CompressionType.GENERAL, metrics
        
        # Trigger standard
        if utilization >= self.trigger_config["utilization_threshold"]:
            return True, CompressionType.GENERAL, metrics
        
        # Trigger per rumore MCP
        if mcp_noise >= self.trigger_config["mcp_noise_threshold"]:
            return True, CompressionType.MCP_HEAVY, metrics
        
        return False, CompressionType.GENERAL, metrics
    
    def _extract_messages_from_state(self, state: DeepAgentState) -> List[Dict[str, Any]]:
        """Estrae messaggi dal DeepAgentState."""
        if 'messages' in state:
            return [msg.dict() if hasattr(msg, 'dict') else dict(msg) for msg in state['messages']]
        return []
    
    def _apply_compression_to_state(self, state: DeepAgentState, result: LLMCompressionResult) -> Dict[str, Any]:
        """Applica il risultato della compressione al state."""
        
        # Crea messaggio di sistema con summary compresso
        compressed_message = {
            "role": "system",
            "content": result.compressed_content,
            "compression_metadata": {
                "original_message_count": len(result.original_messages),
                "compression_type": result.compression_type.value,
                "reduction_percentage": result.actual_reduction_percentage,
                "timestamp": result.timestamp
            }
        }
        
        # Preserva ultimi messaggi se configurato
        recent_messages = []
        if self.compressor.config.preserve_last_n_messages > 0:
            recent_messages = result.original_messages[-self.compressor.config.preserve_last_n_messages:]
        
        # Aggiorna state
        state_update = {
            "messages": [compressed_message] + recent_messages,
            "context_metrics": {
                "tokens_used": result.tokens_after,
                "last_compression": result.timestamp,
                "compression_count": getattr(state, 'compression_count', 0) + 1
            },
            "compression_history": getattr(state, 'compression_history', []) + [{
                "timestamp": result.timestamp,
                "reduction_percentage": result.actual_reduction_percentage,
                "compression_type": result.compression_type.value
            }]
        }
        
        return state_update


class ContextHookManager:
    """
    Manager centrale per gestione hook del contesto nel grafo LangGraph.
    
    Questo sistema:
    1. Registra e gestisce hook multipli per diversi punti del grafo
    2. Esegue hook in ordine di priorità
    3. Gestisce errori e fallback graceful
    4. Fornisce metriche e monitoring
    5. Si integra trasparentemente con LangGraph execution
    """
    
    def __init__(self, compressor: LLMCompressor, config: Dict[str, Any] = None, config_path: Optional[str] = None):
        self.compressor = compressor
        self.config = config or {}
        self.config_path = config_path
        self.hooks: Dict[HookType, List[Hook]] = {hook_type: [] for hook_type in HookType}
        self.enabled = True
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_processing_time": 0.0
        }
        
        # Registra hook di compressione di default con configurazione YAML
        compression_hook = CompressionHook(compressor, config_path=config_path)
        self.register_hook(HookType.POST_STEP, compression_hook)
        self.register_hook(HookType.POST_TOOL, compression_hook)
    
    def register_hook(self, hook_type: HookType, hook: Hook) -> None:
        """Registra un hook per un tipo specifico."""
        self.hooks[hook_type].append(hook)
        # Ordina per priorità (numeri più bassi = priorità più alta)
        self.hooks[hook_type].sort(key=lambda h: h.priority.value)
    
    def unregister_hook(self, hook_type: HookType, hook_name: str) -> bool:
        """Rimuove un hook."""
        original_length = len(self.hooks[hook_type])
        self.hooks[hook_type] = [h for h in self.hooks[hook_type] if h.name != hook_name]
        return len(self.hooks[hook_type]) < original_length
    
    async def execute_hooks(self, hook_type: HookType, state: DeepAgentState, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Esegue tutti gli hook per il tipo specificato."""
        if not self.enabled or not self.hooks[hook_type]:
            return None
        
        start_time = time.time()
        self.stats["total_executions"] += 1
        
        try:
            context = HookContext(
                hook_type=hook_type,
                state=state,
                metadata=metadata or {}
            )
            
            results = []
            state_updates = {}
            
            # Esegue hook in ordine di priorità
            for hook in self.hooks[hook_type]:
                if hook.can_execute(context):
                    try:
                        result = await hook.execute(context)
                        if result:
                            results.append({"hook": hook.name, "result": result})
                            
                            # Applica aggiornamenti state se presenti
                            if "state_update" in result:
                                state_updates.update(result["state_update"])
                    
                    except Exception as e:
                        results.append({
                            "hook": hook.name, 
                            "error": str(e),
                            "success": False
                        })
            
            self.stats["successful_executions"] += 1
            
            # Restituisce risultati e aggiornamenti state
            return {
                "hook_type": hook_type.value,
                "executed_hooks": len([r for r in results if "error" not in r]),
                "results": results,
                "state_updates": state_updates,
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            self.stats["failed_executions"] += 1
            return {
                "hook_type": hook_type.value,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        finally:
            self.stats["total_processing_time"] += time.time() - start_time
    
    def get_hook_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche degli hook."""
        hook_counts = {hook_type.value: len(hooks) for hook_type, hooks in self.hooks.items()}
        
        return {
            **self.stats,
            "enabled": self.enabled,
            "registered_hooks": hook_counts,
            "total_registered": sum(hook_counts.values()),
            "average_execution_time": (
                self.stats["total_processing_time"] / self.stats["total_executions"]
                if self.stats["total_executions"] > 0 else 0
            )
        }


# ============================================================================
# INTEGRATION DECORATORS AND UTILITIES
# ============================================================================

def with_context_hooks(hook_manager: ContextHookManager):
    """
    Decorator per integrare hook automatici in funzioni agent.
    
    Uso:
    @with_context_hooks(hook_manager)
    async def my_agent_function(state: DeepAgentState):
        # La funzione verrà automaticamente wrappata con hook
        pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Estrae state dagli argomenti
            state = None
            for arg in args:
                if isinstance(arg, (dict, DeepAgentState)):
                    state = arg
                    break
            
            if state is None:
                # Se non trova state, esegue funzione normale
                return await func(*args, **kwargs)
            
            # Pre-hook
            pre_result = await hook_manager.execute_hooks(
                HookType.PRE_STEP, 
                state, 
                {"function": func.__name__}
            )
            
            # Applica aggiornamenti pre-step se presenti
            if pre_result and "state_updates" in pre_result:
                if isinstance(state, dict):
                    state.update(pre_result["state_updates"])
                else:
                    for key, value in pre_result["state_updates"].items():
                        setattr(state, key, value)
            
            # Esegue funzione originale
            result = await func(*args, **kwargs)
            
            # Post-hook
            post_result = await hook_manager.execute_hooks(
                HookType.POST_STEP, 
                state,
                {"function": func.__name__, "pre_result": pre_result}
            )
            
            # Applica aggiornamenti post-step al risultato se è un Command
            if post_result and "state_updates" in post_result:
                if hasattr(result, 'update') and hasattr(result.update, 'update'):
                    # È un Command di LangGraph
                    result.update.update(post_result["state_updates"])
                elif isinstance(result, dict):
                    # È un dict di state
                    result.update(post_result["state_updates"])
            
            return result
        
        return wrapper
    return decorator


async def create_hooked_deep_agent(tools, instructions, model=None, hook_manager=None, config_path=None, **kwargs):
    """
    Crea un deep agent con hook automatici integrati.
    
    Questa funzione wrappa create_deep_agent e aggiunge hook automatici
    senza modificare l'interfaccia esistente.
    
    Args:
        tools: Lista di tool per l'agente
        instructions: Istruzioni per l'agente
        model: Modello LLM da utilizzare
        hook_manager: Manager per gli hook. Se None, verrà creato automaticamente
        config_path: Percorso al file di configurazione YAML
        **kwargs: Altri argomenti per create_deep_agent
    """
    from deepagents.graph import create_deep_agent
    
    # Crea agent normale
    agent = create_deep_agent(tools, instructions, model, **kwargs)
    
    if hook_manager:
        # Applica hook al grafo dell'agent
        original_nodes = agent.get_graph().nodes
        
        # Wrappa ogni nodo con hook
        for node_name, node_func in original_nodes.items():
            if callable(node_func):
                wrapped_func = with_context_hooks(hook_manager)(node_func)
                agent.get_graph().nodes[node_name] = wrapped_func
    
    return agent


# ============================================================================
# MONITORING AND DIAGNOSTICS
# ============================================================================

class HookMonitor:
    """Monitor per analisi performance e debugging hook."""
    
    def __init__(self, hook_manager: ContextHookManager):
        self.hook_manager = hook_manager
        self.execution_log: List[Dict[str, Any]] = []
        self.max_log_size = 1000
    
    def log_execution(self, hook_type: HookType, result: Dict[str, Any]) -> None:
        """Registra esecuzione hook per analisi."""
        self.execution_log.append({
            "timestamp": time.time(),
            "hook_type": hook_type.value,
            "result": result
        })
        
        # Mantiene solo ultimi N record
        if len(self.execution_log) > self.max_log_size:
            self.execution_log = self.execution_log[-self.max_log_size:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Genera report delle performance hook."""
        if not self.execution_log:
            return {"status": "no_data"}
        
        # Analizza execution log
        by_type = {}
        total_time = 0
        total_executions = len(self.execution_log)
        
        for entry in self.execution_log:
            hook_type = entry["hook_type"]
            exec_time = entry["result"].get("execution_time", 0)
            
            if hook_type not in by_type:
                by_type[hook_type] = {"count": 0, "total_time": 0, "errors": 0}
            
            by_type[hook_type]["count"] += 1
            by_type[hook_type]["total_time"] += exec_time
            total_time += exec_time
            
            if "error" in entry["result"]:
                by_type[hook_type]["errors"] += 1
        
        # Calcola medie
        for hook_type in by_type:
            stats = by_type[hook_type]
            stats["avg_time"] = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            stats["error_rate"] = stats["errors"] / stats["count"] * 100 if stats["count"] > 0 else 0
        
        return {
            "total_executions": total_executions,
            "total_time": round(total_time, 3),
            "average_time": round(total_time / total_executions, 3) if total_executions > 0 else 0,
            "by_hook_type": by_type,
            "hook_manager_stats": self.hook_manager.get_hook_stats()
        }
